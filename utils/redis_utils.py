from .redis_client import r

ACTIVE_USER_EXPIRY = 120 # 2 minutes
ACTIVE_VENUE_EXPIRY = 604,800 # 7 days

def add_active_user(user_id):
    r.set(f"active_user:{user_id}", '1',ex = ACTIVE_USER_EXPIRY)

def remove_active_user(user_id):
    r.delete(f"active_user:{user_id}")

def get_active_users():
    key = r.keys('active_user:*')

    return [k.split(':')[1] for k in key]

def refresh_active_user(user_id):
    r.expire(f"active_user:{user_id}",ACTIVE_USER_EXPIRY)

def add_active_venue(venue_id,centroid):
    r.set(f"venue:{round(centroid[0],4)}:{round(centroid[1],4)}",venue_id, ex = ACTIVE_VENUE_EXPIRY)

def remove_active_venue(centroid):
    key = f"venue:{centroid[0]:.4f}:{centroid[1]:.4f}"
    r.delete(key)

def get_venue(centroid):
    value = r.get(f"venue:{round(centroid[0],4)}:{round(centroid[1],4)}")
    return value

