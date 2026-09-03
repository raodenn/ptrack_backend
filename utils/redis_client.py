import redis
import os

r = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'), 
    port=int(os.environ.get('REDIS_PORT', 6379)), 
    db=0, 
    decode_responses=True)