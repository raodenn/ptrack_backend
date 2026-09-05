from rest_framework import generics, permissions, viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import CursorPagination
from rest_framework.throttling import SimpleRateThrottle
from django.http import JsonResponse
from django.views import View
from django.db.models import Q 
from .models import UserLocation, Session, Venue, Attendance
from accounts.models import Consent
from .serializers import (
    UserLocationSerializer,
    SessionSerialzer,
    SessionUpdateSerializer,
    VenueSerializer,
)
from utils.redis_utils import add_active_user, add_active_venue, get_venue
from utils.venue import reverse_geocode_centroid
from gatherings.services.date_utils import get_period_boundaries
from django.contrib.auth import get_user_model
from gatherings.services.session_utils import get_ranked_friends_by_shared_time
User = get_user_model()


class UserLocationView(generics.CreateAPIView):
    """
    POST /api/v1/locations/
    Ingests and encrypts user coordinates.
    """
    serializer_class = UserLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        try:
            consent = user.user_consent 
        except Consent.DoesNotExist:
            raise PermissionDenied('No consent found. Location tracking is disabled')
        if not user.user_consent.is_tracking_enabled:
            raise PermissionDenied("Location tracking is disabled in your consent settings.")
        serializer.save(user = self.request.user)
        add_active_user(str(self.request.user.id))

class SessionCursorPagination(CursorPagination):
    ordering = '-created_at'
    page_size = 20

class SessionReadViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = SessionCursorPagination
    serializer_class = SessionSerialzer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        status = self.request.query_params.get('status', 'all')

        qs = Session.objects.filter(attendances__user = user).distinct()

        if status == 'active':
            return qs.filter(is_active = True,ended_at__isnull = True)
        elif status == 'past':
            return qs.filter(is_active = False,ended_at__isnull = False)
        return qs

    def get_object(self):
        obj = super().get_object()

        if not obj.attendances.filter(user = self.request.user).exists():
            raise PermissionDenied
        return obj

class SessionUpdateView(generics.UpdateAPIView):
    serializer_class = SessionUpdateSerializer
    queryset = Session.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()

        if not obj.attendances.filter(user = self.request.user).exists():
            raise PermissionDenied
        return obj
    

class AnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, period_type):
        param_mapping = {
            "daily": "date",
            "weekly": "week",
            "monthly": "month",
        }

        query_key = param_mapping.get(period_type)

        if not query_key:
            return JsonResponse({"error": "Endpoint not found."}, status=404)

        raw_val = request.GET.get(query_key)

        if not raw_val:
            # Default to current period
            from datetime import datetime as dt
            now = dt.now()
            if period_type == "daily":
                raw_val = now.strftime("%Y-%m-%d")
            elif period_type == "weekly":
                raw_val = now.strftime("%G-W%V")
            elif period_type == "monthly":
                raw_val = now.strftime("%Y-%m")

        user_tz = getattr(request.user, "timezone","Africa/Addis_Ababa")

        try:
            start,end = get_period_boundaries(raw_val,period_type,user_tz)

        except ValueError:
            return JsonResponse(
                {'error':f"Invalid format for {query_key}. Expected: daily (YYYY-MM-DD), weekly (YYYY-Www), monthly (YYYY-MM)."},
                status = 400
            )

        return JsonResponse(get_ranked_friends_by_shared_time(request.user,start,end), safe=False)


class NominatimRateThrottle(SimpleRateThrottle):
    scope = 'nominatim'
    rate = '1/sec'

    def get_cache_key(self, request, view):
        return 'throttle_nominatim_global'


class VenueView(APIView):
    """
    GET /api/venues/?lat=x&lng=y&source=cache
    GET /api/venues/?lat=x&lng=y&source=nominatim
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_throttles(self):
        source = self.request.query_params.get('source', 'cache').lower()
        if source == 'nominatim':
            return [NominatimRateThrottle()]
        return []

    def get(self, request):
        lat_raw = request.query_params.get('lat')
        lng_raw = request.query_params.get('lng') or request.query_params.get('lon')
        source = request.query_params.get('source', 'cache').lower()

        if lat_raw is None or lng_raw is None:
            return Response(
                {"error": "Missing required query parameters: 'lat' and 'lng' (or 'lon')."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lat = float(lat_raw)
            lng = float(lng_raw)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid coordinates. 'lat' and 'lng' must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
            return Response(
                {"error": "Coordinates out of bounds. Latitude in [-90, 90], longitude in [-180, 180]."},
                status=status.HTTP_400_BAD_REQUEST
            )

        rounded_coords = (round(lat, 4), round(lng, 4))

        if source == 'cache':
            # 1. Check Redis
            v_id = get_venue(rounded_coords)
            if v_id:
                venue = Venue.objects.filter(id=v_id).first()
                if venue:
                    return Response(VenueSerializer(venue).data, status=status.HTTP_200_OK)

            # 2. Check Database directly
            venue = Venue.objects.filter(
                latitude__range=(rounded_coords[0] - 0.0001, rounded_coords[0] + 0.0001),
                longitude__range=(rounded_coords[1] - 0.0001, rounded_coords[1] + 0.0001)
            ).first()

            if not venue:
                venue = Venue.objects.filter(latitude=lat, longitude=lng).first()

            if venue:
                add_active_venue(str(venue.id), rounded_coords)
                return Response(VenueSerializer(venue).data, status=status.HTTP_200_OK)

            return Response(
                {"detail": "Venue not found in cache or database."},
                status=status.HTTP_404_NOT_FOUND
            )

        elif source == 'nominatim':
            venue_info = reverse_geocode_centroid(lat, lng)

            if venue_info:
                venue_name = venue_info.get('venue_name', 'Unlisted Location')
                venue_lat = venue_info.get('latitude', lat)
                venue_lng = venue_info.get('longitude', lng)

                venue, created = Venue.objects.get_or_create(
                    latitude=venue_lat,
                    longitude=venue_lng,
                    defaults={'name': venue_name}
                )

                add_active_venue(str(venue.id), rounded_coords)
                add_active_venue(str(venue.id), (venue.latitude, venue.longitude))

                return Response(VenueSerializer(venue).data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "Nominatim reverse geocoding failed or returned no result."},
                    status=status.HTTP_502_BAD_GATEWAY
                )
        else:
            return Response(
                {"error": f"Invalid source '{source}'. Expected 'cache' or 'nominatim'."},
                status=status.HTTP_400_BAD_REQUEST
            )