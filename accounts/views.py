from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction

from .serializers import UserRegistrationSerializer, LogoutSerializer, ConsentSerializer
from utils.redis_utils import remove_active_user
from gatherings.services import end_attendance_for_user
from .models import Consent


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self,request,*args,**kwargs):
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            user = serializer.save()
            Consent.objects.create(id=user, is_tracking_enabled=False)

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'username': user.username,   
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)


class UpdateConsentView(generics.UpdateAPIView):
    """
    PUT /api/accounts/consent/
    Updates user consent status.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConsentSerializer

    def get_object(self):
        obj,created = Consent.objects.get_or_create(user = self.request.user)

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            if not instance.is_tracking_enabled:
                remove_active_user(str(self.request.user.id))
                end_attendance_for_user(self.request.user)
            


