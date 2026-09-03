from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        request = 'FR', 'Friend Request'
        session = 'SS', 'Session'
        weekly_wrap = 'WW', 'Weekly Wrap'
        nudge = 'ND', 'Nudge'

    title = models.TextField()
    message = models.TextField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name='notifications'
    )
    type = models.CharField(max_length=20, choices=NotificationType.choices)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type','object_id')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} -> {self.user}'