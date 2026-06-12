"""
api/v1/routers/playback.py

Phase 9 — Playback System API router.

Endpoints:
  POST   /playback/search              — search recordings
  POST   /playback/timeline            — get timeline blocks
  POST   /playback/session             — create playback session
  POST   /playback/session/{id}/heartbeat — extend session TTL
  DELETE /playback/session/{id}        — destroy session
  POST   /playback/download            — download/export clip

Security:
  - All endpoints require JWT authentication
  - playback:view permission required for search/session/timeline
  - playback:download permission required for download
  - Credentials are NEVER returned to the frontend
  - Playback sessions auto-expire after idle timeout

Audit logging:
  - playback_opened
  - playback_closed
  - playback_download_requested
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from datetime import timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, require_permission, user_has_permission
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.discovered_nvr import DiscoveredNVR
from app.models.user import User
from app.schemas.playback import (
    PlaybackDownloadRequest,
    PlaybackHeartbeatResponse,
    PlaybackSearchRequest,
    PlaybackSearchResponse,
    PlaybackSessionDeleteResponse,
    PlaybackSessionRequest,
    PlaybackSessionResponse,
    PlaybackTimelineResponse,
    RecordingSegmentSchema,
    TimelineBlockSchema,
)
from app.services.playback.download_service import (
    DownloadError,
    build_download_filename,
    stream_recording,
)
from app.services.playback.hikvision_playback import (
    PlaybackSearchError,
    search_recordings,
)
from app.services.playback.acti_playback import probe_playback_available
from app.services.playback.playback_manager import (
    Go2RTCError,
    PlaybackManagerError,
    PrefetchError,
    build_playback_stream_url,
    create_playback_session,
    destroy_playback_session,
)
from app.services.playback.playback_session import (
    extend_session_ttl,
    get_session,
    get_session_temp_file_path,
)
from app.services.playback.timeline_parser import (
    build_timeline,
    segments_to_simple_list,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playback", tags=["Playback"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_nvr_or_404(db: AsyncSession, device_id: UUID) -> DiscoveredNVR:
    """Fetch a DiscoveredNVR by ID or raise 404."""
    result = await db.execute(
        select(DiscoveredNVR).where(DiscoveredNVR.id == device_id)
    )
    nvr = result.scalar_one_or_none()
    if not nvr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found",
        )
    return nvr


async def _audit(
    db: AsyncSession,
    action: str,
    user_id: int,
    target_id: str,
    ip_address: str | None = None,
) -> None:
    """Write an audit log entry (fire-and-forget, errors are swallowed)."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            target_type="playback_session",
            target_id=target_id,
            ip_address=ip_address,
        )
        db.add(entry)
        await db.commit()
    except Exception as exc:
        logger.warning("Audit log write failed: %s", exc)


# ---------------------------------------------------------------------------
# POST /playback/search
# ---------------------------------------------------------------------------

@router.post(
    "/search",
    response_model=PlaybackSearchResponse,
    summary="Search recordings on a device",
)
async def search_recordings_endpoint(
    body: PlaybackSearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("playback.view")),
):
    """
    Search for recording segments on a Hikvision NVR.

    Returns a list of recording segments within the requested time window.
    Credentials are fetched from the database — never from the request.
    """
    nvr = await _get_nvr_or_404(db, body.device_id)

    # Ensure datetimes are UTC-aware
    start = body.start_time
    end = body.end_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    vendor = getattr(nvr, "vendor", "hikvision") or "hikvision"
    if vendor == "acti_snvr":
        # ACTi SNVR has no recording search API.
        # Probe the /playback/ endpoint to see if the device actually has
        # recordings at the requested start time before claiming a segment exists.
        from app.services.playback.hikvision_playback import RecordingSegment
        has_recording = await probe_playback_available(
            nvr_ip=nvr.nvr_ip,
            http_port=nvr.http_port,
            username=nvr.username,
            password=nvr.password,
            channel=body.channel,
            start_time=start,
        )
        segments = (
            [RecordingSegment(start=start, end=end, track_id="1", recording_type="normal")]
            if has_recording
            else []
        )
    else:
        try:
            segments = await search_recordings(
                nvr_ip=nvr.nvr_ip,
                http_port=nvr.http_port,
                username=nvr.username,
                password=nvr.password,
                channel=body.channel,
                start_time=start,
                end_time=end,
                rtsp_port=nvr.rtsp_port,
                nvr_timezone=nvr.timezone,
            )
        except PlaybackSearchError as exc:
            logger.error("Recording search failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Recording search failed: {exc}",
            )

    segment_schemas = [
        RecordingSegmentSchema(
            start=seg.start,
            end=seg.end,
            recording_type=seg.recording_type,
            duration_seconds=(seg.end - seg.start).total_seconds(),
        )
        for seg in segments
    ]

    return PlaybackSearchResponse(
        device_id=body.device_id,
        channel=body.channel,
        segments=segment_schemas,
        total_segments=len(segment_schemas),
        has_recordings=len(segment_schemas) > 0,
    )


# ---------------------------------------------------------------------------
# POST /playback/timeline
# ---------------------------------------------------------------------------

@router.post(
    "/timeline",
    response_model=PlaybackTimelineResponse,
    summary="Get timeline blocks for a device/channel/window",
)
async def get_timeline_endpoint(
    body: PlaybackSearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("playback.view")),
):
    """
    Return a structured timeline (recording blocks + gap blocks) for the
    requested time window.  Useful for rendering the timeline scrubber.
    """
    nvr = await _get_nvr_or_404(db, body.device_id)

    start = body.start_time
    end = body.end_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    vendor = getattr(nvr, "vendor", "hikvision") or "hikvision"
    if vendor == "acti_snvr":
        from app.services.playback.hikvision_playback import RecordingSegment
        has_recording = await probe_playback_available(
            nvr_ip=nvr.nvr_ip,
            http_port=nvr.http_port,
            username=nvr.username,
            password=nvr.password,
            channel=body.channel,
            start_time=start,
        )
        segments = (
            [RecordingSegment(start=start, end=end, track_id="1", recording_type="normal")]
            if has_recording
            else []
        )
    else:
        try:
            segments = await search_recordings(
                nvr_ip=nvr.nvr_ip,
                http_port=nvr.http_port,
                username=nvr.username,
                password=nvr.password,
                channel=body.channel,
                start_time=start,
                end_time=end,
                rtsp_port=nvr.rtsp_port,
                nvr_timezone=nvr.timezone,
            )
        except PlaybackSearchError as exc:
            logger.error("Timeline search failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Recording search failed: {exc}",
            )

    timeline = build_timeline(segments, start, end)

    blocks = [
        TimelineBlockSchema(
            type=b.type,
            start=b.start,
            end=b.end,
            duration_seconds=b.duration_seconds,
            recording_type=b.recording_type,
        )
        for b in timeline.blocks
    ]

    return PlaybackTimelineResponse(
        device_id=body.device_id,
        channel=body.channel,
        window_start=timeline.window_start,
        window_end=timeline.window_end,
        blocks=blocks,
        total_recording_seconds=timeline.total_recording_seconds,
        has_recordings=timeline.has_recordings,
    )


# ---------------------------------------------------------------------------
# POST /playback/session
# ---------------------------------------------------------------------------

@router.post(
    "/session",
    response_model=PlaybackSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a playback session",
)
async def create_session_endpoint(
    body: PlaybackSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("playback.view")),
):
    """
    Create a playback session for a recorded segment.

    Flow:
      1. Validate device
      2. Build authenticated RTSP URL (stays in backend)
      3. Register temporary go2rtc stream
      4. Persist session record
      5. Return stream_url for frontend WebSocket connection

    The frontend uses the same MSE/WebRTC player as live view.
    Only the stream_name changes.
    """
    nvr = await _get_nvr_or_404(db, body.device_id)

    start = body.start_time
    end = body.end_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    vendor = getattr(nvr, "vendor", "hikvision") or "hikvision"
    is_prefetched = vendor == "acti_snvr"

    try:
        session = await create_playback_session(
            db=db,
            nvr=nvr,
            channel=body.channel,
            start_time=start,
            end_time=end,
            created_by=current_user.id,
        )
    except PrefetchError as exc:
        logger.error("ACTi recording prefetch failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Recording download failed: {exc}",
        )
    except Go2RTCError as exc:
        logger.error("go2rtc stream registration failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stream registration failed: {exc}",
        )
    except PlaybackManagerError as exc:
        logger.error("Playback session creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session creation failed: {exc}",
        )

    # Audit log
    await _audit(
        db=db,
        action="playback_opened",
        user_id=current_user.id,
        target_id=str(session.id),
        ip_address=request.client.host if request.client else None,
    )

    if is_prefetched:
        stream_url = f"/api/v1/playback/session/{session.id}/stream"
    else:
        stream_url = build_playback_stream_url(session.stream_name)

    return PlaybackSessionResponse(
        session_id=session.id,
        stream_name=session.stream_name,
        stream_url=stream_url,
        is_prefetched=is_prefetched,
        expires_at=session.expires_at,
        device_id=session.device_id,
        channel=session.channel,
        start_time=session.start_time,
        end_time=session.end_time,
    )


# ---------------------------------------------------------------------------
# POST /playback/session/{id}/heartbeat
# ---------------------------------------------------------------------------

@router.post(
    "/session/{session_id}/heartbeat",
    response_model=PlaybackHeartbeatResponse,
    summary="Extend playback session TTL (keep-alive)",
)
async def heartbeat_session_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("playback.view")),
):
    """
    Extend the expiry of an active playback session.

    The frontend should call this every 60 seconds while the user is
    actively watching playback to prevent the session from expiring.
    """
    session = await get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playback session {session_id} not found",
        )

    extended = await extend_session_ttl(db, session_id)
    updated_session = await get_session(db, session_id)

    return PlaybackHeartbeatResponse(
        session_id=session_id,
        extended=extended,
        expires_at=updated_session.expires_at if updated_session else None,
    )


# ---------------------------------------------------------------------------
# DELETE /playback/session/{id}
# ---------------------------------------------------------------------------

@router.delete(
    "/session/{session_id}",
    response_model=PlaybackSessionDeleteResponse,
    summary="Destroy a playback session",
)
async def delete_session_endpoint(
    session_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("playback.view")),
):
    """
    Destroy a playback session.

    Removes the go2rtc stream and cleans up DB + Redis records.
    The frontend should call this when the user closes the player.
    """
    # Fetch session for audit before deletion
    session = await get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playback session {session_id} not found",
        )

    deleted = await destroy_playback_session(db, session_id)

    # Audit log
    await _audit(
        db=db,
        action="playback_closed",
        user_id=current_user.id,
        target_id=str(session_id),
        ip_address=request.client.host if request.client else None,
    )

    return PlaybackSessionDeleteResponse(
        session_id=session_id,
        deleted=deleted,
    )


# ---------------------------------------------------------------------------
# GET /playback/session/{id}/stream  — serve prefetched MP4 file
# ---------------------------------------------------------------------------

@router.get(
    "/session/{session_id}/stream",
    summary="Stream a prefetched ACTi recording (MP4)",
)
async def stream_prefetched_recording(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("playback.view")),
):
    """
    Stream the server-side MP4 file that was pre-downloaded from an ACTi SNVR.

    Supports HTTP Range requests so the browser can seek within the recording.
    Only available for sessions created with is_prefetched=True.
    """
    session = await get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    temp_path = await get_session_temp_file_path(str(session_id))
    if not temp_path or not os.path.exists(temp_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prefetched recording not found — session may have expired",
        )

    return FileResponse(
        path=temp_path,
        media_type="video/mp4",
        filename=f"recording_ch{session.channel}.mp4",
    )


# ---------------------------------------------------------------------------
# POST /playback/download
# ---------------------------------------------------------------------------

@router.post(
    "/download",
    summary="Download/export a recording clip",
)
async def download_recording_endpoint(
    body: PlaybackDownloadRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("playback.download")),
):
    """
    Stream a recording clip directly from the NVR via ffmpeg.

    The backend probes for the correct RTSP playback URL (handles PSIA fallback
    for older firmware), then streams fragmented MP4 bytes as ffmpeg produces
    them. The browser download starts immediately and shows real progress.
    Credentials are never exposed to the frontend.
    """
    nvr = await _get_nvr_or_404(db, body.device_id)

    start = body.start_time
    end = body.end_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    await _audit(
        db=db,
        action="playback_download_requested",
        user_id=current_user.id,
        target_id=f"{body.device_id}:ch{body.channel}:{start.isoformat()}",
        ip_address=request.client.host if request.client else None,
    )

    filename = build_download_filename(
        nvr_ip=nvr.nvr_ip,
        channel=body.channel,
        start_time=start,
        end_time=end,
    )

    try:
        gen = stream_recording(
            nvr=nvr,
            channel=body.channel,
            start_time=start,
            end_time=end,
        )
        # Consume the first item to trigger URL probe / DownloadError before headers are sent
        first_chunk = None
        async for chunk in gen:
            first_chunk = chunk
            break
    except DownloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Download failed: {exc}",
        )

    async def _combined() -> AsyncIterator[bytes]:
        if first_chunk:
            yield first_chunk
        async for chunk in gen:
            yield chunk

    return StreamingResponse(
        _combined(),
        media_type="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
