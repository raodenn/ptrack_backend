from .models import UserLocation, Session, Attendance, Venue
from social.serializers import UserMinimalSerializer
from rest_framework import serializers
from django.utils import timezone
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

class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'latitude', 'longitude']

class AttendanceSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only = True)
    class Meta:
        model = Attendance
        fields = ['id','user','joined_at','left_at','duration_seconds']
        read_only_fields = ['id','user','joined_at','left_at','duration_seconds']

class SessionSerialzer(serializers.ModelSerializer):
    creator = UserMinimalSerializer(read_only=True)
    venue = VenueSerializer(read_only = True)
    attendances = AttendanceSerializer(many = True,read_only = True)

    session_duration = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = ['id','creator','venue','is_active','created_at','ended_at','attendances','session_duration']
        read_only_fields = fields
    def get_session_duration(self,obj):
        end_time = obj.ended_at or timezone.now()
        delta = end_time - obj.created_at
        return int(delta.total_seconds())

class SessionUpdateSerializer(serializers.ModelSerializer):
    venue = VenueSerializer()
    class Meta:
        model = Session
        fields = ['id','venue']
    def update(self, instance, validated_data):
        venue_data = validated_data.pop('venue',None)

        if venue_data and instance.venue:
            instance.venue.name = venue_data.get('name',instance.venue.name)
            instance.venue.save()

        return super().update(instance, validated_data)

