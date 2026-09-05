from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from gatherings.models import Session, Attendance
from social.models import FriendRequest
from .models import Notification


@receiver(post_save, sender=FriendRequest)
def notify_on_friend_request(sender, instance, created, **kwargs):
    if instance.status == 'pending':
        request_content_type = ContentType.objects.get_for_model(FriendRequest)
        if not Notification.objects.filter(
            content_type=request_content_type,
            object_id=instance.id,
            user=instance.receiver,
            type=Notification.NotificationType.request
        ).exists():
            sender_name = instance.sender.username or instance.sender.email
            Notification.objects.create(
                title='New Friend Request',
                message=f'{sender_name} wants to be your friend',
                user=instance.receiver,
                type=Notification.NotificationType.request,
                content_type=request_content_type,
                object_id=instance.id
            )


@receiver(post_save, sender=Session)
def notify_on_session_created(sender, instance, created, **kwargs):
    if not created:
        return

    def _create_session_notifications():
        session_content_type = ContentType.objects.get_for_model(Session)
        attendances = Attendance.objects.filter(
            session_id=instance.id
        ).exclude(user_id=instance.creator_id)

        already_notified = set(
            Notification.objects.filter(
                content_type=session_content_type,
                object_id=instance.id,
                type=Notification.NotificationType.session
            ).values_list('user_id', flat=True)
        )

        notifications = [
            Notification(
                title='Session Started',
                message='You have been added to a new active session.',
                type=Notification.NotificationType.session,
                user_id=att.user_id,
                content_type=session_content_type,
                object_id=instance.id
            )
            for att in attendances
            if att.user_id not in already_notified
        ]

        if notifications:
            Notification.objects.bulk_create(notifications)

    transaction.on_commit(_create_session_notifications)
