import os
import pymongo
from redis import StrictRedis


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

db = pymongo.MongoClient(host=os.getenv("MONGO_HOST", "mongodb1-instance-1"),
                         port=int(os.getenv("MONGO_PORT", "27017"))).mydb

redis_url = os.environ.get("REDIS_URL", None)
if redis_url:
    redis_conn = StrictRedis.from_url(redis_url)
else:
    redis_conn = StrictRedis(host=os.getenv("REDIS_HOST", "redis1-redis-1-vm"),
                             port=int(os.getenv("REDIS_PORT", "6379")))

redis_limit = 5000

fingerprint_version = 792015  # DayMonthYear

ImageStatus = enum('NEW', 'ADD_COLLECTION', 'RENEW_SEGMENTATION', 'IN_PROGRESS', 'READY', 'NOT_RELEVANT')
