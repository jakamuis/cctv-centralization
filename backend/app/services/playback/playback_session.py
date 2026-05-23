"""
services/playback/playback_session.py

Database and Redis helpers for playback session CRUD.

Responsibilities:
  - Create playback session records in PostgreSQL
  - Track active sessions in Redis for fast expiry checks
  - Retrieve and delete sessions
  - List expired sessions for cleanup

Redis key schema:
  playback:session:{session_id}  → hash {stream_name, device_id, channel, expires_at}
  playback:active                → set of session_id strings
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.playback_session import PlaybackSession
from app.utils.redis_client import get_redis

logger = logging.getLogger(__name__)

# Default session TTL in seconds (5 minutes idle timeout)
DEFAULT_SESSION_TTL_SECONDS = 300


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

async def create_session(
    db: AsyncSession,
    device_id: uuid.UUID,
    channel: int,
    start_time: datetime,
    end_time: datetime,
    stream_name: str,
    created_by: Optional[int] = None,
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
) -> PlaybackSession:
    """
    Persist a new PlaybackSession to the database and register it in Redis.

    Returns the created PlaybackSession ORM object.
    """
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    session = PlaybackSession(
        id=uuid.uuid4(),
        device_id=device_id,
        channel=channel,
        start_time=start_time,
        end_time=end_time,
        stream_name=stream_name,
        expires_at=expires_at,
        created_by=created_by,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Mirror in Redis for fast expiry checks
    await _redis_register_session(session, ttl_seconds)

    logger.info(
        "Created playback session %s: device=%s ch=%d stream=%r expires=%s",
        session.id, device_id, channel, stream_name, expires_at.isoformat(),
    )
    return session


async def get_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> Optional[PlaybackSession]:
    """Retrieve a PlaybackSession by ID."""
    result = await db.execute(
        select(PlaybackSession).where(PlaybackSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def delete_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> bool:
    """
    Delete a PlaybackSession from the database and Redis.

    Returns True if the session existed and was deleted, False otherwise.
    """
    session = await get_session(db, session_id)
    if not session:
        return False

    stream_name = session.stream_name
    await db.delete(session)
    await db.commit()

    await _redis_unregister_session(str(session_id))

    logger.info("Deleted playback session %s (stream=%r)", session_id, stream_name)
    return True


async def list_expired_sessions(db: AsyncSession) -> List[PlaybackSession]:
    """
    Return all sessions whose expires_at is in the past.

    Used by the cleanup worker.
    """
    now = datetime.now(tz=timezone.utc)
    result = await db.execute(
        select(PlaybackSession).where(PlaybackSession.expires_at <= now)
    )
    return list(result.scalars().all())


async def extend_session_ttl(
    db: AsyncSession,
    session_id: uuid.UUID,
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
) -> bool:
    """
    Extend the expiry of an active session (heartbeat / keep-alive).

    Returns True if the session was found and updated.
    """
    session = await get_session(db, session_id)
    if not session:
        return False

    new_expires = datetime.now(tz=timezone.utc) + timedelta(seconds=ttl_seconds)
    session.expires_at = new_expires
    await db.commit()

    # Update Redis TTL
    redis = get_redis()
    key = f"playback:session:{session_id}"
    await redis.expire(key, ttl_seconds)

    logger.debug("Extended TTL for session %s → %s", session_id, new_expires.isoformat())
    return True


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

async def _redis_register_session(
    session: PlaybackSession,
    ttl_seconds: int,
) -> None:
    """Store session metadata in Redis with TTL for fast expiry detection."""
    redis = get_redis()
    key = f"playback:session:{session.id}"
    mapping = {
        "stream_name": session.stream_name,
        "device_id": str(session.device_id),
        "channel": str(session.channel),
        "expires_at": session.expires_at.isoformat(),
    }
    await redis.hset(key, mapping=mapping)
    await redis.expire(key, ttl_seconds)
    await redis.sadd("playback:active", str(session.id))


async def _redis_unregister_session(session_id: str) -> None:
    """Remove session from Redis."""
    redis = get_redis()
    await redis.delete(f"playback:session:{session_id}")
    await redis.srem("playback:active", session_id)


async def get_active_session_ids_from_redis() -> List[str]:
    """Return all currently tracked session IDs from Redis."""
    redis = get_redis()
    members = await redis.smembers("playback:active")
    return list(members)


async def get_session_stream_name_from_redis(session_id: str) -> Optional[str]:
    """Fast lookup of stream_name from Redis (avoids DB hit)."""
    redis = get_redis()
    key = f"playback:session:{session_id}"
    return await redis.hget(key, "stream_name")
