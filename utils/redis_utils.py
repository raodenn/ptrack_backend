import logging
from .redis_client import r

logger = logging.getLogger(__name__)

ACTIVE_USER_EXPIRY = 120  # 2 minutes
ACTIVE_VENUE_EXPIRY = 604_800  # 7 days


def add_active_user(user_id):
    try:
        r.set(f"active_user:{user_id}", '1', ex=ACTIVE_USER_EXPIRY)
    except Exception as e:
        logger.warning(f"Redis add_active_user failed: {e}")


def remove_active_user(user_id):
    try:
        r.delete(f"active_user:{user_id}")
    except Exception as e:
        logger.warning(f"Redis remove_active_user failed: {e}")


def get_active_users():
    try:
        keys = r.keys('active_user:*')
        return [k.split(':', 1)[1] for k in keys]
    except Exception as e:
        logger.warning(f"Redis get_active_users failed: {e}")
        return []


def refresh_active_user(user_id):
    try:
        r.expire(f"active_user:{user_id}", ACTIVE_USER_EXPIRY)
    except Exception as e:
        logger.warning(f"Redis refresh_active_user failed: {e}")


def add_active_venue(venue_id, centroid):
    try:
        r.set(f"venue:{round(centroid[0],4)}:{round(centroid[1],4)}", venue_id, ex=ACTIVE_VENUE_EXPIRY)
    except Exception as e:
        logger.warning(f"Redis add_active_venue failed: {e}")


def remove_active_venue(centroid):
    try:
        key = f"venue:{centroid[0]:.4f}:{centroid[1]:.4f}"
        r.delete(key)
    except Exception as e:
        logger.warning(f"Redis remove_active_venue failed: {e}")


def get_venue(centroid):
    try:
        value = r.get(f"venue:{round(centroid[0],4)}:{round(centroid[1],4)}")
        return value
    except Exception as e:
        logger.warning(f"Redis get_venue failed: {e}")
        return None
