import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django_cryptography.fields import encrypt
from utils.calc import haversine_distance
User = get_user_model()

class Venue(models.Model):
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    google_places_id = models.CharField(max_length = 255, unique=True, blank=True, null=True)
    name = models.CharField(max_length= 255, null=True, default='Unlisted Location')
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add= True)

    def __str__(self):
        if self.google_places_id:
            return f"{self.name} ({self.google_places_id})"
        return f"{self.name} @ ({self.latitude}, {self.longitude})"

class UserLocation(models.Model):
    id = models.UUIDField(primary_key= True, default= uuid.uuid4 ,editable= False)
    user = models.ForeignKey(User, on_delete= models.CASCADE, related_name= 'locations')
    latitude = encrypt(models.TextField())
    longitude = encrypt(models.TextField())
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"location for {self.user} @ {self.timestamp}"

    @property
    def lat(self) -> float:
        return float(self.latitude)

    @property
    def lon(self) -> float:
        return float(self.longitude)

    def distance_to(self,other_location) -> float:
        return haversine_distance(
            self.lat, self.lon, other_location.lat, other_location.lon
        )
class Session(models.Model):
    id = models.UUIDField(primary_key= True,default = uuid.uuid4, editable= False)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name= 'created_sessions')
    venue = models.ForeignKey(Venue, blank=True ,null=True ,on_delete=models.SET_NULL, related_name = "sessions")
    latitude = encrypt(models.TextField())
    longitude = encrypt(models.TextField())
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Session {self.id} (Active: {self.is_active})"

class Attendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4,editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendances')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_attendances')
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null = True, blank = True)
    last_in_range_at = models.DateTimeField(default=timezone.now)
    duration_seconds = models.PositiveIntegerField(null=True,blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = ['session','user'],
                condition=Q(left_at__isnull = True),
                name = 'unique_active_user_per_session'
            )
        ]

    def save(self,*args, **kwargs):
        # auto populate durations seconds when left_at is populated
        if self.left_at and self.joined_at and not self.duration_seconds:
            delta = self.left_at - self.joined_at
            self.duration_seconds = int(delta.total_seconds())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"User {self.user_id} in Session {self.session_id}"