from redis.asyncio import Redis
from app.core.config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis


async def publish(channel: str, message: str):
    redis = get_redis()
    await redis.publish(channel, message)


async def subscribe(channel: str):
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    return pubsub