from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase
from rest_framework import status
from social.models import FriendRequest
from gatherings.models import Session, Attendance, Venue
from notifications.models import Notification

User = get_user_model()


class NotificationSignalTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='Password123!',
            username='user1'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='Password123!',
            username='user2'
        )
        self.user3 = User.objects.create_user(
            email='user3@example.com',
            password='Password123!',
            username='user3'
        )

    def test_friend_request_signal_creates_notification_for_receiver(self):
        # Creating a pending friend request
        fr = FriendRequest.objects.create(
            sender=self.user1,
            receiver=self.user2,
            status='pending'
        )

        notifications = Notification.objects.filter(user=self.user2)
        self.assertEqual(notifications.count(), 1)
        notif = notifications.first()
        self.assertEqual(notif.type, Notification.NotificationType.request)
        self.assertEqual(notif.title, 'New Friend Request')
        self.assertIn('user1', notif.message)
        self.assertEqual(notif.object_id, fr.id)
        self.assertFalse(notif.is_read)

        # Sender should not get a notification
        self.assertEqual(Notification.objects.filter(user=self.user1).count(), 0)

    def test_session_signal_creates_notification_for_attendees_except_creator(self):
        venue = Venue.objects.create(
            name='Test Cafe',
            latitude=9.0123,
            longitude=38.7456
        )
        session = Session.objects.create(
            creator=self.user1,
            venue=venue,
            latitude="9.0123",
            longitude="38.7456"
        )
        # Add attendances
        Attendance.objects.create(session=session, user=self.user1)  # creator
        Attendance.objects.create(session=session, user=self.user2)  # attendee
        Attendance.objects.create(session=session, user=self.user3)  # attendee

        # Trigger session created notification (or via post_save)
        # Note: Session signal checks attendances and on_commit
        from notifications.signals import notify_on_session_created
        notify_on_session_created(Session, session, created=True)

        # Creator should NOT receive notification
        self.assertEqual(Notification.objects.filter(user=self.user1, type=Notification.NotificationType.session).count(), 0)

        # Attendee 2 and 3 should receive notifications
        notif_user2 = Notification.objects.filter(user=self.user2, type=Notification.NotificationType.session).first()
        self.assertIsNotNone(notif_user2)
        self.assertEqual(notif_user2.title, 'Session Started')
        self.assertEqual(notif_user2.object_id, session.id)

        notif_user3 = Notification.objects.filter(user=self.user3, type=Notification.NotificationType.session).first()
        self.assertIsNotNone(notif_user3)
        self.assertEqual(notif_user3.title, 'Session Started')
        self.assertEqual(notif_user3.object_id, session.id)


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='api_user@example.com',
            password='Password123!',
            username='apiuser'
        )
        self.other_user = User.objects.create_user(
            email='other_user@example.com',
            password='Password123!',
            username='otheruser'
        )

        self.list_url = reverse('notifications:notification-list')
        self.mark_all_read_url = reverse('notifications:notification-mark-all-read')

        # Create sample notifications for self.user
        ct = ContentType.objects.get_for_model(User)
        self.notif_unread_1 = Notification.objects.create(
            title='Unread 1',
            message='Unread message 1',
            user=self.user,
            type=Notification.NotificationType.request,
            is_read=False,
            content_type=ct,
            object_id=self.user.id
        )
        self.notif_read = Notification.objects.create(
            title='Read 1',
            message='Read message 1',
            user=self.user,
            type=Notification.NotificationType.session,
            is_read=True,
            content_type=ct,
            object_id=self.user.id
        )
        self.notif_unread_2 = Notification.objects.create(
            title='Unread 2',
            message='Unread message 2',
            user=self.user,
            type=Notification.NotificationType.request,
            is_read=False,
            content_type=ct,
            object_id=self.user.id
        )

        # Other user's notification
        self.other_notif = Notification.objects.create(
            title='Other User Notif',
            message='Other message',
            user=self.other_user,
            type=Notification.NotificationType.request,
            is_read=False,
            content_type=ct,
            object_id=self.other_user.id
        )

    def test_list_notifications_requires_auth(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_notifications_unread_first_and_paginated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 3)

        results = response.data['results']
        # Verify unread first
        self.assertFalse(results[0]['is_read'])
        self.assertFalse(results[1]['is_read'])
        self.assertTrue(results[2]['is_read'])

    def test_filter_notifications_by_is_read(self):
        self.client.force_authenticate(user=self.user)

        # Filter is_read=true
        response_read = self.client.get(f"{self.list_url}?is_read=true")
        self.assertEqual(response_read.status_code, status.HTTP_200_OK)
        self.assertEqual(response_read.data['count'], 1)
        self.assertTrue(response_read.data['results'][0]['is_read'])

        # Filter is_read=false
        response_unread = self.client.get(f"{self.list_url}?is_read=false")
        self.assertEqual(response_unread.status_code, status.HTTP_200_OK)
        self.assertEqual(response_unread.data['count'], 2)
        for item in response_unread.data['results']:
            self.assertFalse(item['is_read'])

    def test_patch_single_notification_as_owner(self):
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('notifications:notification-detail', kwargs={'pk': self.notif_unread_1.pk})

        response = self.client.patch(detail_url, {'is_read': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_read'])

        self.notif_unread_1.refresh_from_db()
        self.assertTrue(self.notif_unread_1.is_read)

    def test_patch_single_notification_read_only_fields_cannot_be_changed(self):
        self.client.force_authenticate(user=self.user)
        detail_url = reverse('notifications:notification-detail', kwargs={'pk': self.notif_unread_1.pk})

        response = self.client.patch(detail_url, {
            'is_read': True,
            'title': 'Hacked Title',
            'message': 'Hacked Message'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.notif_unread_1.refresh_from_db()
        self.assertTrue(self.notif_unread_1.is_read)
        self.assertEqual(self.notif_unread_1.title, 'Unread 1')
        self.assertEqual(self.notif_unread_1.message, 'Unread message 1')

    def test_patch_notification_non_owner_returns_404(self):
        self.client.force_authenticate(user=self.user)
        other_detail_url = reverse('notifications:notification-detail', kwargs={'pk': self.other_notif.pk})

        response = self.client.patch(other_detail_url, {'is_read': True})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.other_notif.refresh_from_db()
        self.assertFalse(self.other_notif.is_read)

    def test_mark_all_read_bulk_update(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.mark_all_read_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)

        # All of self.user's notifications should now be is_read=True
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

        # Other user's notifications must NOT be modified
        self.other_notif.refresh_from_db()
        self.assertFalse(self.other_notif.is_read)
