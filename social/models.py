from django.db import models
from django.conf import settings
import uuid
from django.db.models import F,Q


class Friendship (models.Model):
    id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friendships')
    friend = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friends')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'friend'], name='unique_friendship'),
            models.CheckConstraint(check = ~Q(user = F("friend")), name = "prevent_self_friendship")
            ]

    def save(self, *args, **kwargs):
        if str(self.user_id) > str(self.friend_id):
            self.user, self.friend = self.friend, self.user
        super().save(*args, **kwargs)

class FriendRequest(models.Model):
    id = models.UUIDField(primary_key=True, default = uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_friend_requests')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'),('cancelled', 'Cancelled')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields = ['sender','receiver'], name = 'unique_friend_request')
        ]

class ExcludedFriend(models.Model):
    """Allows a user to exclude a specific friend from proximity detection."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='excluded_friends')
    friend = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='excluded_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'friend'], name='unique_excluded_friend'),
            models.CheckConstraint(check=~Q(user=F("friend")), name="prevent_self_exclusion"),
        ]

    def save(self, *args, **kwargs):
        # Canonical ordering — same pattern as Friendship
        if str(self.user_id) > str(self.friend_id):
            self.user, self.friend = self.friend, self.user
        super().save(*args, **kwargs)

    def __str__(self):
        return f"ExcludedFriend({self.user_id}, {self.friend_id})"