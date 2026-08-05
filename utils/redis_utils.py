from .redis_client import r

ACTIVE_USER_EXPIRY = 120 # 2 minutes

def add_active_user(user_id):
    r.set(f"active_user:{user_id}", '1',ex = ACTIVE_USER_EXPIRY)

def remove_active_user(user_id):
    r.delete(f"active_user:{user_id}")

def get_active_users():
    key = r.keys('active_user:*')

    return [k.split(':')[1] for k in key]

def refresh_active_user(user_id):
    r.expire(f"active_user:{user_id}",ACTIVE_USER_EXPIRY)
    