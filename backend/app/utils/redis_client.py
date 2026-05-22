import aioredis
from app.core.config import settings

redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)

async def publish(channel: str, message: str):
    await redis.publish(channel, message)

async def subscribe(channel: str):
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    return pubsub