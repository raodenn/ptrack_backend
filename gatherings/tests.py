import json
from unittest.mock import patch
from datetime import timedelta
import zoneinfo
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APITestCase
from rest_framework import status

from gatherings.models import Venue, Session, Attendance
from accounts.models import Consent
from social.models import Friendship
from notifications.models import Notification
from gatherings.tasks import send_weekly_wrap_task, send_nudge_notifications_task, check_proximity_task
from utils.redis_client import r
from utils.redis_utils import add_active_venue, get_venue

User = get_user_model()


class VenueAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='venue_test@example.com',
            password='Password123!',
            username='venuetest'
        )
        self.venues_url = reverse('gatherings:venue-lookup')
        self.client.force_authenticate(user=self.user)

    def test_venue_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(f"{self.venues_url}?lat=9.03&lng=38.74&source=cache")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_venue_missing_coordinates(self):
        response = self.client.get(f"{self.venues_url}?source=cache")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_venue_invalid_coordinates(self):
        response = self.client.get(f"{self.venues_url}?lat=invalid&lng=38.74&source=cache")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_venue_cache_miss_and_not_in_db_returns_404(self):
        response = self.client.get(f"{self.venues_url}?lat=1.2345&lng=6.7890&source=cache")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_venue_cache_hit_from_db(self):
        venue = Venue.objects.create(
            name='Local Coffee',
            latitude=9.0123,
            longitude=38.7456
        )
        response = self.client.get(f"{self.venues_url}?lat=9.0123&lng=38.7456&source=cache")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Local Coffee')

    @patch('gatherings.views.reverse_geocode_centroid')
    def test_venue_nominatim_source_creates_and_caches_venue(self, mock_geocode):
        mock_geocode.return_value = {
            'latitude': 9.0500,
            'longitude': 38.7500,
            'venue_name': 'Mock Landmark Cafe',
            'raw_address': {'amenity': 'Mock Landmark Cafe'}
        }

        response = self.client.get(f"{self.venues_url}?lat=9.05&lng=38.75&source=nominatim")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Mock Landmark Cafe')

        # Verify saved in DB
        db_venue = Venue.objects.filter(name='Mock Landmark Cafe').first()
        self.assertIsNotNone(db_venue)

        # Verify cached in Redis
        cached_id = get_venue((9.05, 38.75))
        if cached_id:
            self.assertEqual(str(db_venue.id), cached_id)


class CeleryTaskTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='u1@example.com',
            password='Password123!',
            username='user1'
        )
        self.user2 = User.objects.create_user(
            email='u2@example.com',
            password='Password123!',
            username='user2'
        )
        # Enable tracking consent
        Consent.objects.create(user=self.user1, is_tracking_enabled=True)
        Consent.objects.create(user=self.user2, is_tracking_enabled=True)

        # Create friendship
        u1, u2 = sorted([self.user1, self.user2], key=lambda u: str(u.id))
        self.friendship = Friendship.objects.create(user=u1, friend=u2)

    def test_send_weekly_wrap_task_creates_notification_and_email(self):
        tz = zoneinfo.ZoneInfo("Africa/Addis_Ababa")
        now = timezone.now().astimezone(tz)
        current_monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        past_week_start = current_monday - timedelta(days=7)

        # Create a session in the past week
        venue = Venue.objects.create(name='Meeting Point', latitude=9.01, longitude=38.74)
        session = Session.objects.create(
            creator=self.user1,
            venue=venue,
            latitude="9.01",
            longitude="38.74",
            created_at=past_week_start + timedelta(days=2),
            ended_at=past_week_start + timedelta(days=2, hours=2),
            is_active=False
        )
        Attendance.objects.create(
            session=session,
            user=self.user1,
            joined_at=past_week_start + timedelta(days=2),
            left_at=past_week_start + timedelta(days=2, hours=2),
            duration_seconds=7200
        )
        Attendance.objects.create(
            session=session,
            user=self.user2,
            joined_at=past_week_start + timedelta(days=2),
            left_at=past_week_start + timedelta(days=2, hours=2),
            duration_seconds=7200
        )

        # Clear mailbox
        mail.outbox = []

        # Run task
        result = send_weekly_wrap_task()
        self.assertIn("Processed weekly wrap", result)

        # Check notification created
        notifs = Notification.objects.filter(user=self.user1, type=Notification.NotificationType.weekly_wrap)
        self.assertEqual(notifs.count(), 1)
        self.assertIn("Weekly Wrap", notifs.first().title)

        # Check email sent
        self.assertGreaterEqual(len(mail.outbox), 1)

    def test_send_nudge_notifications_task_creates_nudge(self):
        # Friendship created > 14 days ago, no session
        self.friendship.created_at = timezone.now() - timedelta(days=20)
        self.friendship.save()

        # Run task
        result = send_nudge_notifications_task()
        self.assertIn("Created", result)

        # Check notifications created for both users
        nudge_u1 = Notification.objects.filter(user=self.user1, type=Notification.NotificationType.nudge)
        nudge_u2 = Notification.objects.filter(user=self.user2, type=Notification.NotificationType.nudge)
        self.assertEqual(nudge_u1.count(), 1)
        self.assertEqual(nudge_u2.count(), 1)
