from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from typing import Optional
from uuid import UUID

from app.api.v1.dependencies import get_current_user
from app.models.user import User
from app.repositories.camera import CameraRepository
from app.db.session import get_db

from sqlalchemy.ext.asyncio import AsyncSession

from app.stream.manager import start_or_join_stream, leave_or_stop_stream, list_active_streams
from app.stream.models import StartStreamRequest, StartStreamResponse, StopStreamResponse
from app.security.stream_token import validate_stream_token
from app.api.v1.dependencies import user_has_permission, has_camera_access
from app.core.config import settings
import httpx


router = APIRouter(prefix="/streams", tags=["Streams"])


@router.post("/live/{camera_id}", response_model=StartStreamResponse)
async def start_stream(
    camera_id: UUID,
    payload: StartStreamRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cam = await CameraRepository(db).get_by_id(camera_id)
    if not cam or not cam.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found or disabled")

    # RBAC: require stream.live and camera.view permissions
    if not user_has_permission(current_user, "stream.live"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permission: stream.live")
    if not has_camera_access(current_user, cam):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this camera")

    viewer_id: Optional[str] = payload.viewer_id if payload else str(current_user.id)
    session = await start_or_join_stream(str(cam.id), cam.stream_name, viewer_id=viewer_id)

    # Build the direct go2rtc HLS URL that the browser can reach.
    # go2rtc_public_url is the browser-accessible base (e.g. http://localhost:1984).
    # Auth/RBAC has already been enforced above; the stream_name is the go2rtc key.
    public_base = settings.streaming.go2rtc_public_url.rstrip("/")
    hls_url = f"{public_base}/api/stream.m3u8?src={cam.stream_name}"

    return StartStreamResponse(
        session_id=session.session_id,
        camera_id=session.camera_id,
        stream_name=session.stream_name,
        hls_url=hls_url,
        viewer_count=session.viewer_count,
    )


@router.delete("/live/{camera_id}", response_model=StopStreamResponse)
async def stop_stream(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cam = await CameraRepository(db).get_by_id(camera_id)
    if not cam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    stopped = await leave_or_stop_stream(str(cam.id), viewer_id=str(current_user.id))
    return StopStreamResponse(stopped=stopped, session_id=str(cam.id), camera_id=str(cam.id))


@router.get("/active")
async def active_streams():
    streams = await list_active_streams()
    # Serialize datetimes to isoformat
    return [
        {
            "session_id": s.session_id,
            "camera_id": s.camera_id,
            "stream_name": s.stream_name,
            "viewer_count": s.viewer_count,
            "last_activity_at": s.last_activity_at.isoformat(),
            # Do not expose raw go2rtc URLs
            "hls_url": None,
        }
        for s in streams
    ]


async def _proxy_go2rtc_request(go2rtc_path: str) -> Response:
    base_host = settings.streaming.go2rtc_host
    base_addr = settings.streaming.go2rtc_http_address.lstrip(":") or "1984"
    url = f"http://{base_host}:{base_addr}{go2rtc_path}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        headers = {
            # propagate essential caching headers but keep short-lived
            "Content-Type": r.headers.get("Content-Type", "application/octet-stream"),
            "Cache-Control": "no-store, max-age=0",
        }
        return Response(content=r.content, status_code=r.status_code, headers=headers)


@router.get("/hls/{camera_id}/index.m3u8")
async def hls_master_playlist(camera_id: UUID, token: str = Query(...), db: AsyncSession = Depends(get_db)):
    # Validate token and camera binding
    try:
        payload = await validate_stream_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")
    if payload.get("cid") != str(camera_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token-camera mismatch")

    # Proxy to go2rtc master playlist for this camera's stream_name
    # Using src param keeps go2rtc routing internal
    src = str(camera_id)  # our manager uses camera UUID mapping to stream_name, but we need actual name
    # To avoid an extra DB hit, expect client to first call /live which ensures go2rtc route exists by stream_name
    # We fetch stream_name via ID
    cam = await CameraRepository(db).get_by_id(camera_id)
    if not cam or not cam.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found or disabled")
    return await _proxy_go2rtc_request(f"/api/stream.m3u8?src={cam.stream_name}")


@router.get("/hls/{camera_id}/{rest:path}")
async def hls_child(camera_id: UUID, rest: str, token: str = Query(...), db: AsyncSession = Depends(get_db)):
    # Validate token and camera binding for every HLS fetch (segments and variant playlists)
    try:
        payload = await validate_stream_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")
    if payload.get("cid") != str(camera_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token-camera mismatch")

    # Forward request to go2rtc HLS file for the stream
    cam = await CameraRepository(db).get_by_id(camera_id)
    if not cam or not cam.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found or disabled")

    # go2rtc serves segments under /api/stream/{stream_name}/{rest}
    return await _proxy_go2rtc_request(f"/api/stream/{cam.stream_name}/{rest}")
