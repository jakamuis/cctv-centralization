"""
services/playback/playback_cleanup.py

Background cleanup worker for expired playback sessions.

Responsibilities:
  - Periodically scan for expired PlaybackSession rows
  - Remove corresponding go2rtc streams
  - Delete expired DB records and Redis keys
  - Run as an asyncio background task (started at app startup)

Cleanup triggers:
  - Session expires_at is in the past (idle timeout)
  - Manual session close (handled by destroy_playback_session)
  - App shutdown (best-effort)

Default cleanup interval: 30 seconds
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.db.session import AsyncSessionLocal
from app.services.playback.playback_session import list_expired_sessions
from app.services.playback.playback_manager import destroy_playback_session

logger = logging.getLogger(__name__)

# How often the cleanup loop runs (seconds)
CLEANUP_INTERVAL_SECONDS = 30

_cleanup_task: Optional[asyncio.Task] = None


async def _run_cleanup_cycle() -> int:
    """
    One cleanup cycle: find and destroy all expired sessions.

    Returns the number of sessions cleaned up.
    """
    cleaned = 0
    async with AsyncSessionLocal() as db:
        expired = await list_expired_sessions(db)
        if not expired:
            return 0

        logger.info("Playback cleanup: found %d expired session(s)", len(expired))

        for session in expired:
            try:
                await destroy_playback_session(db, session.id)
                cleaned += 1
                logger.info(
                    "Cleaned up expired playback session %s (stream=%r)",
                    session.id, session.stream_name,
                )
            except Exception as exc:
                logger.error(
                    "Error cleaning up session %s: %s",
                    session.id, exc, exc_info=True,
                )

    return cleaned


async def _cleanup_runner() -> None:
    """
    Infinite loop that runs cleanup cycles at CLEANUP_INTERVAL_SECONDS.

    Errors in individual cycles are caught and logged so the loop
    never dies silently.
    """
    logger.info(
        "Playback cleanup worker started (interval=%ds)",
        CLEANUP_INTERVAL_SECONDS,
    )
    while True:
        try:
            cleaned = await _run_cleanup_cycle()
            if cleaned:
                logger.info("Playback cleanup cycle: removed %d session(s)", cleaned)
        except Exception as exc:
            logger.error("Playback cleanup cycle error: %s", exc, exc_info=True)

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


def start_playback_cleanup_worker() -> None:
    """
    Start the background cleanup task.

    Safe to call multiple times — only one task is created.
    Call this from the FastAPI startup event.
    """
    global _cleanup_task

    if _cleanup_task is not None and not _cleanup_task.done():
        logger.debug("Playback cleanup worker already running")
        return

    _cleanup_task = asyncio.create_task(_cleanup_runner())
    logger.info("Playback cleanup worker task created")


def stop_playback_cleanup_worker() -> None:
    """
    Cancel the background cleanup task.

    Call this from the FastAPI shutdown event.
    """
    global _cleanup_task

    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.info("Playback cleanup worker stopped")
    _cleanup_task = None
