from .models import Session, Attendance
from django.db.models import Count,Q
from django.utils import timezone
from datetime import timedelta

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

def update_attendance_left_at(user):
    attendance = Attendance.objects.filter(
        user = user,
        left_at__isnull = True,
        last_in_range_at__lt = timezone.now() - timedelta(minutes = 5)
    ).first()

    if not attendance:
        return None

    attendance.left_at = timezone.now()
    attendance.save()

    remaining = Attendance.objects.filter(
        session = attendance.session,
        left_at__isnull = True 
    ).count()

    if remaining < 2:
        attendance.session.is_active = False
        attendance.session.ended_at = timezone.now()
        attendance.session.save()
    
    return attendance

def create_session_for_group(group):
    session = Session.objects.create(
        creator = group[0]
    )
    
        
