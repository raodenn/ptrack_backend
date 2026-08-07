from .models import UserLocation
from rest_framework import serializers
from django.contrib.auth import get_user_model

class UserLocationSerializer(serializers.Serializer):
    class Meta:
        model = UserLocation
        fields = ['id','latitude','longitude','timestamp']
        read_only_fields = ['id','timestamp']

    def validate_latitude(self, value: float) -> float:
        if not (-90.0 <= value <= 90.0):
            raise serializers.ValidationError("Latitude must be between -90.0 and 90.0 degrees.")
        return value

    def validate_longitude(self, value: float) -> float:
        if not (-180.0 <= value <= 180.0):
            raise serializers.ValidationError("Longitude must be between -180.0 and 180.0 degrees.")
        return value

