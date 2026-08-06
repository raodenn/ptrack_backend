from .models import Session, Attendance
from django.db.models import Count,Q
from django.utils import timezone


def get_active_session_for_group(users):
    """get active user session if available"""

    total_target_users = len(users)

    session_with_all_present = Session.objects.filter(
        is_active = True,
        ended_at__isnull = True,
    ).annotate(
        active_target_user_count = Count(
            'attendances__user',
            filter=Q(
                attendances__user_id__in = users,
                attendances__left_at__isnull = True
            ),
            distinct=True
        ),
        total_active_user_count = Count(
            'attendances__user',
            filter = Q(
                attendances__left_at__isnull = True
            ),
            distinct=True
        )
    ).filter(
        active_target_user_count = total_target_users,
        total_active_user_count = total_target_users
    )

    session = session_with_all_present.first()

    if session:
        upated_count = Attendance.objects.filter(
            session = session,
            user__in = users
        ).update(
            last_in_range_at = timezone.now()
        )
    return session if session_with_all_present else None
