from rest_framework import generics, permissions
from .models import UserLocation
from .serializers import UserLocationSerializer

class UserLocationView(generics.CreateAPIView):
    """
    POST /api/v1/locations/
    Ingests and encrypts user coordinates.
    """
    serializer_class = UserLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user = self.request.user)


