from .models import Session, Attendance, Venue
from django.db.models import Count,Q
from django.utils import timezone
from datetime import timedelta
from utils.calc import compute_centroid
from utils.venue import reverse_geocode_centroid
from utils.redis_utils import add_active_venue,get_venue
from django.db import transaction

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

def close_session_if_empty(session):
    remaining = Attendance.objects.filter(
            session = session,
            left_at__isnull = True 
        ).count()

    if remaining < 2:
        session.is_active = False
        session.ended_at = timezone.now()
        session.save()
    

def update_attendance_left_at(user):
    attendance = Attendance.objects.filter(
        user = user,
        left_at__isnull = True,
        last_in_range_at__lt = timezone.now() - timedelta(minutes = 5)
    )

    if not attendance:
        return None

    attendance.left_at = timezone.now()
    attendance.save()

    close_session_if_empty(attendance.session)

    return attendance

def create_session_for_group(group, locations):
    creator = group[0]
    centroid = compute_centroid(locations)
    venue = reverse_geocode_centroid(centroid[0],centroid[1]) 
    v_id = get_venue(centroid)

    v = None

    if v_id:
        try:
            v = Venue.objects.get(
                id = v_id
            )
        except Venue.DoesNotExist:
            v = None

    with transaction.atomic():    
        if not v:
            if venue:
                v , created = Venue.objects.get_or_create(
                    latitude = venue["latitude"],
                    longitude = venue['longitude']
                ) 
                add_active_venue(v.id,centroid)
            else:
                v = Venue.objects.create(
                        latitude = centroid[0],
                        longitude = centroid[1]
                    ) 


        session = Session.objects.create(
            creator = creator,
            venue = v,
            latitude = centroid[0],
            longitude = centroid[1]
        )   

        now = timezone.now()
        
        attendances = [
            Attendance(
                session = session,
                user_id = user_id,
                joined_at = now,
                last_in_range_at = now
            )
            for user_id in group
        ]
        Attendance.objects.bulk_create(attendances)
    return session

def end_attendance_for_user(user):
    attendance = Attendance.objects.filter(
            user = user,
            left_at__isnull = True,
        ).first()
    
    if not attendance:
        return None

    attendance.left_at = timezone.now()
    attendance.save()
    close_session_if_empty(attendance.session)

    return attendance