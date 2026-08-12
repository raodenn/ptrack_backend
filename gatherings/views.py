from rest_framework import generics, permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import CursorPagination
from .models import UserLocation, Session, Venue
from accounts.models import Consent
from .serializers import UserLocationSerializer, SessionSerialzer, SessionUpdateSerializer
from utils.redis_utils import add_active_user   

class UserLocationView(generics.CreateAPIView):
    """
    POST /api/v1/locations/
    Ingests and encrypts user coordinates.
    """
    serializer_class = UserLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
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
    
        