from celery import shared_task
from django.contrib.auth import get_user_model
from .models import UserLocation
from social.models import Friendship
from django.utils import timezone
from utils.redis_utils import get_active_users as get_users_from_redis
from datetime import timedelta
from django.db.models import Q

User = get_user_model()

@shared_task
def check_proximity():
    cutoff = timezone.now()- timedelta(minutes=5)
    active_users = get_users_from_redis()
    friends = Friendship.objects.filter(
        user__id__in=active_users,
        friend__id__in = active_users)

    pairs = set()
    for f in friends:
        pairs.add(frozenset([f.user_id, f.friend_id]))

    graph = {}

    all_user_id = {u_id for pair in pairs for u_id in pair }

    recent_locations = UserLocation.objects.filter(
        user_id__in = all_user_id,
        timestamp__gte = cutoff,
    ).order_by('user_id','-timestamp').distinct('user_id')

    user_location_map = {loc.user_id: loc for loc in recent_locations}


    for pair in pairs:
        u1_id, u2_id = tuple(pair)

        u1_location = user_location_map.get(u1_id)
        u2_location = user_location_map.get(u2_id)

        if not u1_location or not u2_location:
            continue

        distance = u1_location.distance_to(u2_location) 

        if distance <= 0.01:
            graph.setdefault(u1_id,set()).add(u2_id)
            graph.setdefault(u2_id,set()).add(u1_id)
            
