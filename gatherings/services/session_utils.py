from collections import defaultdict

from ..models import Session, Attendance, Venue
from django.db.models import Count,Q, Exists, OuterRef
from django.utils import timezone
from datetime import timedelta
from utils.calc import compute_centroid
from utils.venue import reverse_geocode_centroid
from utils.redis_utils import add_active_venue,get_venue
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from notifications.models import Notification
from social.models import Friendship

User = get_user_model()

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
        updated_count = Attendance.objects.filter(
            session = session,
            user__in = users
        ).update(
            last_in_range_at = timezone.now()
        )
    return session 

def close_session_if_empty(session):
    remaining = Attendance.objects.filter(
            session = session,
            left_at__isnull = True 
        ).count()

    if remaining < 2:
        session.is_active = False
        session.ended_at = timezone.now()
        session.save()
    

def update_attendance_left_at(user_id):
    attendance = Attendance.objects.filter(
        user_id = user_id,
        left_at__isnull = True,
        last_in_range_at__lt = timezone.now() - timedelta(minutes = 5)
    ).first()

    if not attendance:
        return None

    attendance.left_at = timezone.now()
    attendance.save()

    close_session_if_empty(attendance.session)

    return attendance

def create_session_for_group(group, locations):
    creator_id = group[0]
    creator = User.objects.get(id=creator_id)
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
                v, created = Venue.objects.get_or_create(
                    latitude=venue["latitude"],
                    longitude=venue['longitude'],
                    defaults={'name': venue.get('venue_name', 'Unlisted Location')}
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

def get_ranked_friends_by_shared_time(current_user, start = None, end = None):

    cur_filters = {
        'user': current_user,
        'session__ended_at__isnull': False,
        'joined_at__isnull': False,
        'left_at__isnull': False,
    }

    if start:
        cur_filters['left_at__gt'] = start

    if end:
        cur_filters['joined_at__lt'] = end

    my_attendances = Attendance.objects.filter(**cur_filters)

    my_times_per_session = {
        att.session_id: (att.joined_at,att.left_at)
        for att in my_attendances
    }

    if not my_times_per_session:
        return []
    
    friendship_check = Exists(Friendship.objects.filter((
        Q(user=current_user, friend_id=OuterRef("user_id"))) |
        (Q(friend=current_user, user_id=OuterRef("user_id")))
    ))

    other_attendances = (Attendance.objects.select_related('user').filter(
        session_id__in = my_times_per_session.keys(),
        joined_at__isnull = False,
        left_at__isnull = False
    ).exclude(user = current_user)
    .annotate(is_friend = friendship_check)
    )

    shared_seconds_map = defaultdict(int)
    friend_objects = {}

    for friend_att in other_attendances:
        if not friend_att.is_friend:
            continue
        my_joined, my_left = my_times_per_session[friend_att.session_id]

        overlap_start = max(my_joined, friend_att.joined_at)
        overlap_end = min(my_left, friend_att.left_at)

        if start:
            overlap_start = max(overlap_start, start)
        if end:
            overlap_end = min(overlap_end, end)

        if overlap_end > overlap_start:
            delta = overlap_end - overlap_start
            shared_seconds_map[friend_att.user_id] += int(delta.total_seconds())

        if friend_att.user_id not in friend_objects:
            friend_objects[friend_att.user_id] = friend_att.user

    ranked_friends = [
        {
            'user': friend_objects[uid],
            'total_shared_seconds': secs,
            'total_shared_minutes': round(secs / 60, 1),
            'total_shared_hours': round(secs / 3600, 2),
        }
        for uid, secs in shared_seconds_map.items()
    ]

    ranked_friends.sort(key=lambda x: x['total_shared_seconds'], reverse=True)

    return ranked_friends