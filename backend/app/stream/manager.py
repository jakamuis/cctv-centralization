from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import HTTPException

from app.core.config import settings
from app.stream.models import StreamSession, ActiveStream
from app.utils.redis_client import get_redis


# Redis keys
# stream:active -> set of camera_id
# stream:session:{camera_id} -> hash {session_id, stream_name, started_at, last_activity_at, viewer_count, hls_url}
# stream:viewers:{camera_id} -> set of viewer_ids
# lock:stream:{camera_id} -> string lock with short TTL


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _hls_url(stream_name: str) -> str:
    host = settings.streaming.go2rtc_host
    addr = settings.streaming.go2rtc_http_address.lstrip(":") or "1984"
    return f"http://{host}:{addr}/api/stream.m3u8?src={stream_name}"


async def start_or_join_stream(camera_id: str, stream_name: str, viewer_id: Optional[str] = None) -> StreamSession:
    redis = get_redis()
    session_key = f"stream:session:{camera_id}"
    active_key = "stream:active"

    # Acquire a short lock to avoid race on first creation
    lock_key = f"lock:stream:{camera_id}"
    got_lock = await redis.set(lock_key, "1", ex=5, nx=True)

    try:
        if await redis.exists(session_key):
            data = await redis.hgetall(session_key)
            # increment viewer set and count
            if viewer_id:
                await redis.sadd(f"stream:viewers:{camera_id}", viewer_id)
            await redis.hincrby(session_key, "viewer_count", 1)
            await redis.hset(session_key, mapping={"last_activity_at": _now_iso()})
            data = await redis.hgetall(session_key)
        else:
            # create new session
            sid = str(uuid.uuid4())
            started_at = _now_iso()
            last_activity_at = started_at
            hls = _hls_url(stream_name)
            mapping = {
                "session_id": sid,
                "camera_id": camera_id,
                "stream_name": stream_name,
                "started_at": started_at,
                "last_activity_at": last_activity_at,
                "viewer_count": "1",
                "hls_url": hls,
            }
            await redis.hset(session_key, mapping=mapping)
            # track viewers
            if viewer_id:
                await redis.sadd(f"stream:viewers:{camera_id}", viewer_id)
            # add to active set
            await redis.sadd(active_key, camera_id)
            data = mapping

        return StreamSession(
            session_id=data["session_id"],
            camera_id=data["camera_id"],
            stream_name=data["stream_name"],
            started_at=datetime.fromisoformat(data["started_at"]),
            last_activity_at=datetime.fromisoformat(data["last_activity_at"]),
            viewer_count=int(data.get("viewer_count", 0)),
            hls_url=data.get("hls_url"),
        )
    finally:
        # Release lock if we acquired it
        if got_lock:
            await redis.delete(lock_key)


async def leave_or_stop_stream(camera_id: str, viewer_id: Optional[str] = None) -> bool:
    redis = get_redis()
    session_key = f"stream:session:{camera_id}"
    if not await redis.exists(session_key):
        return False

    if viewer_id:
        await redis.srem(f"stream:viewers:{camera_id}", viewer_id)

    # decrement viewer count with floor at 0
    try:
        count = int(await redis.hget(session_key, "viewer_count") or 0)
    except ValueError:
        count = 0

    new_count = max(0, count - 1)
    await redis.hset(session_key, mapping={
        "viewer_count": new_count,
        "last_activity_at": _now_iso(),
    })

    return True


async def list_active_streams() -> List[ActiveStream]:
    redis = get_redis()
    cameras = await redis.smembers("stream:active")
    result: List[ActiveStream] = []
    for cam in cameras:
        data = await redis.hgetall(f"stream:session:{cam}")
        if not data:
            # cleanup zombie membership
            await redis.srem("stream:active", cam)
            continue
        result.append(ActiveStream(
            session_id=data.get("session_id"),
            camera_id=data.get("camera_id"),
            stream_name=data.get("stream_name"),
            viewer_count=int(data.get("viewer_count", 0)),
            last_activity_at=datetime.fromisoformat(data.get("last_activity_at")),
            hls_url=data.get("hls_url"),
        ))
    return result


async def cleanup_idle_streams():
    """Stop streams with zero viewers for longer than idle_timeout_seconds."""
    redis = get_redis()
    timeout = settings.streaming.idle_timeout_seconds
    cameras = await redis.smembers("stream:active")
    for cam in cameras:
        key = f"stream:session:{cam}"
        data = await redis.hgetall(key)
        if not data:
            await redis.srem("stream:active", cam)
            continue
        try:
            last = datetime.fromisoformat(data.get("last_activity_at"))
        except Exception:
            last = datetime.utcnow()
        viewers = int(data.get("viewer_count", 0))
        if viewers <= 0 and (datetime.utcnow() - last).total_seconds() >= timeout:
            # Remove keys; go2rtc will auto-stop on no consumers; place holder for hard stop
            await redis.delete(key)
            await redis.delete(f"stream:viewers:{cam}")
            await redis.srem("stream:active", cam)


_cleanup_task: Optional[asyncio.Task] = None


def start_background_cleanup():
    global _cleanup_task

    async def _runner():
        # backoff-friendly ticker
        while True:
            try:
                await cleanup_idle_streams()
            except Exception:
                # swallow to keep the loop alive
                pass
            await asyncio.sleep(5)

    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_runner())
