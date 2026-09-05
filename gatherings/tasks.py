import json
import logging
import zoneinfo
from datetime import timedelta, datetime
from celery import shared_task
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models import Q

from .models import UserLocation, Session, Attendance
from social.models import Friendship, ExcludedFriend
from notifications.models import Notification
from utils.redis_client import r
from utils.redis_utils import get_active_users as get_users_from_redis
from utils.graph import connected_components
from .services.session_utils import (
    get_active_session_for_group,
    update_attendance_left_at,
    create_session_for_group,
    get_ranked_friends_by_shared_time,
)

User = get_user_model()
logger = logging.getLogger(__name__)
PROXIMITY_THRESHOLD_KM = 0.01  # 10 meters


@shared_task
def check_proximity():
    cutoff = timezone.now() - timedelta(minutes=2)
    active_users = get_users_from_redis()
    friends = Friendship.objects.filter(
        user__id__in=active_users,
        friend__id__in=active_users
    )

    pairs = set()
    for f in friends:
        pairs.add(frozenset([f.user_id, f.friend_id]))

    # Filter out excluded friend pairs from proximity detection
    excluded = ExcludedFriend.objects.filter(
        user__id__in=active_users,
        friend__id__in=active_users
    )
    excluded_pairs = set()
    for ex in excluded:
        excluded_pairs.add(frozenset([ex.user_id, ex.friend_id]))
    pairs -= excluded_pairs

    graph = {}
    all_user_id = {u_id for pair in pairs for u_id in pair}

    recent_locations = UserLocation.objects.filter(
        user_id__in=all_user_id,
        timestamp__gte=cutoff,
    ).order_by('user_id', '-timestamp').distinct('user_id')

    user_location_map = {loc.user_id: loc for loc in recent_locations}

    for pair in pairs:
        u1_id, u2_id = tuple(pair)
        u1_location = user_location_map.get(u1_id)
        u2_location = user_location_map.get(u2_id)

        if not u1_location or not u2_location:
            continue

        distance = u1_location.distance_to(u2_location)

        if distance <= PROXIMITY_THRESHOLD_KM:
            graph.setdefault(u1_id, set()).add(u2_id)
            graph.setdefault(u2_id, set()).add(u1_id)

    components = connected_components(graph)

    for group in components:
        if len(group) >= 2:
            session = get_active_session_for_group(group)
            if not session:
                locations = [user_location_map[u] for u in group if u in user_location_map]
                create_session_for_group(group, locations)
        else:
            update_attendance_left_at(user_id=group[0])


@shared_task
def check_proximity_task():
    """Alias for check_proximity task for Celery beat schedule."""
    return check_proximity()


@shared_task
def send_weekly_wrap_task():
    """
    Weekly wrap task: fires every Monday at 8am Addis Ababa time (Africa/Addis_Ababa, UTC+3).
    For each user with consent.is_tracking_enabled=True:
    - Compute top 3 friends by shared time for the past week
    - Compute total social hours for the week
    - Compare vs previous week (↑↓ change)
    - Generate highlight stat: 'You spent X% of social time with {top_friend.name}'
    - Send email via Django's email backend
    - Create a Notification record with type='weekly_wrap'
    - Cache the result in Redis with 7 day expiry key weekly_wrap:{user_id}:{week_string}
    """
    tz = zoneinfo.ZoneInfo("Africa/Addis_Ababa")
    now = timezone.now().astimezone(tz)

    # Current Monday 00:00:00
    current_monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start_past_week = current_monday - timedelta(days=7)
    end_past_week = current_monday
    week_string = start_past_week.strftime("%G-W%V")

    start_prev_week = start_past_week - timedelta(days=7)
    end_prev_week = start_past_week

    user_ct = ContentType.objects.get_for_model(User)

    users = User.objects.filter(user_consent__is_tracking_enabled=True)
    processed_count = 0

    for user in users:
        try:
            # Top 3 friends by shared time for past week
            ranked_past = get_ranked_friends_by_shared_time(user, start=start_past_week, end=end_past_week)
            top_3_friends = ranked_past[:3]

            total_seconds_past = sum(f['total_shared_seconds'] for f in ranked_past)
            total_hours_past = round(total_seconds_past / 3600, 2)

            # Previous week comparison
            ranked_prev = get_ranked_friends_by_shared_time(user, start=start_prev_week, end=end_prev_week)
            total_seconds_prev = sum(f['total_shared_seconds'] for f in ranked_prev)
            total_hours_prev = round(total_seconds_prev / 3600, 2)

            diff_hours = round(total_hours_past - total_hours_prev, 2)
            if diff_hours > 0:
                change_str = f"↑ +{diff_hours} hrs"
            elif diff_hours < 0:
                change_str = f"↓ {abs(diff_hours)} hrs"
            else:
                change_str = "No change (0.0 hrs)"

            # Highlight stat
            if top_3_friends and total_seconds_past > 0:
                top_friend_entry = top_3_friends[0]
                top_friend_user = top_friend_entry['user']
                top_friend_name = top_friend_user.get('username') or top_friend_user['email']
                pct = round((top_friend_entry['total_shared_seconds'] / total_seconds_past) * 100, 1)
                highlight_stat = f"You spent {pct}% of social time with {top_friend_name}"
            else:
                highlight_stat = "You had no logged social time with friends this week."

            # Send email via Django email backend
            subject = f"Your Weekly Wrap ({week_string})"
            email_body = (
                f"Hi {user.username or user.email},\n\n"
                f"Here is your Weekly Wrap for {week_string}:\n"
                f"• Total Social Time: {total_hours_past} hrs ({change_str} vs previous week)\n"
                f"• Highlight: {highlight_stat}\n\n"
                f"Top Friends this week:\n" +
                ("\n".join([f"  {i+1}. {f['user'].get('username') or f['user']['email']} ({f['total_shared_hours']} hrs)" for i, f in enumerate(top_3_friends)]) if top_3_friends else "  No friend sessions recorded.") +
                f"\n\nKeep connecting!\n"
            )
            # send_mail(
            #     subject=subject,
            #     message=email_body,
            #     from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@ptrack.local'),
            #     recipient_list=[user.email],
            #     fail_silently=True
            # )

            # Create Notification record with type='weekly_wrap'
            Notification.objects.create(
                title=f"Weekly Wrap ({week_string})",
                message=f"You spent {total_hours_past} hrs socially this week. {highlight_stat}",
                user=user,
                type=Notification.NotificationType.weekly_wrap,
                content_type=user_ct,
                object_id=user.id
            )

            # Cache the result in Redis with 7 day expiry
            cache_key = f"weekly_wrap:{user.id}:{week_string}"
            cache_data = {
                "user_id": str(user.id),
                "week": week_string,
                "total_social_hours": total_hours_past,
                "change_vs_previous_week": change_str,
                "highlight_stat": highlight_stat,
                "top_friends": [
                    {
                        "user_id": f['user']['id'],
                        "name": f['user'].get('username') or f['user']['email'],
                        "total_shared_seconds": f['total_shared_seconds'],
                        "total_shared_hours": f['total_shared_hours'],
                    }
                    for f in top_3_friends
                ]
            }
            r.set(cache_key, json.dumps(cache_data), ex=604800)  # 7 days
            processed_count += 1
        except Exception as e:
            logger.error(f"Weekly wrap failed for user {user.id}: {e}", exc_info=True)

    return f"Processed weekly wrap for {processed_count} users."


@shared_task
def send_nudge_notifications_task():
    """
    Daily task: finds friendships where last session together > 14 days,
    and creates a nudge notification for both users.
    """
    cutoff = timezone.now() - timedelta(days=14)
    friendships = Friendship.objects.select_related('user', 'friend').all()
    friendship_ct = ContentType.objects.get_for_model(Friendship)
    count = 0

    for friendship in friendships:
        try:
            u1 = friendship.user
            u2 = friendship.friend

            # Find the latest shared session attendance
            last_attendance = Attendance.objects.filter(
                user_id=u1.id,
                session__attendances__user_id=u2.id
            ).order_by('-joined_at').first()

            is_stale = False
            if not last_attendance:
                if friendship.created_at < cutoff:
                    is_stale = True
            else:
                last_date = last_attendance.left_at or last_attendance.joined_at
                if last_date < cutoff:
                    is_stale = True

            if is_stale:
                # Check if a nudge was already sent in the last 7 days to avoid daily spam
                recent_nudge = Notification.objects.filter(
                    content_type=friendship_ct,
                    object_id=friendship.id,
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).exists()

                if not recent_nudge:
                    Notification.objects.create(
                        title="Time to catch up!",
                        message=f"It's been a while since you and {u2.username or u2.email} hung out.",
                        user=u1,
                        type=Notification.NotificationType.nudge,
                        content_type=friendship_ct,
                        object_id=friendship.id
                    )
                    Notification.objects.create(
                        title="Time to catch up!",
                        message=f"It's been a while since you and {u1.username or u1.email} hung out.",
                        user=u2,
                        type=Notification.NotificationType.nudge,
                        content_type=friendship_ct,
                        object_id=friendship.id
                    )
                    count += 2
        except Exception as e:
            logger.error(f"Nudge failed for friendship {friendship.id}: {e}", exc_info=True)

    return f"Created {count} nudge notifications."
