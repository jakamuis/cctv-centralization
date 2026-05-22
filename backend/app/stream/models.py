from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class ViewerSession(BaseModel):
    viewer_id: str
    connected_at: datetime


class StreamSession(BaseModel):
    session_id: str
    camera_id: str
    stream_name: str
    started_at: datetime
    last_activity_at: datetime
    viewer_count: int = 0
    hls_url: Optional[str] = None


class StartStreamRequest(BaseModel):
    viewer_id: Optional[str] = None


class StartStreamResponse(BaseModel):
    session_id: str
    camera_id: str
    stream_name: str
    hls_url: str
    viewer_count: int


class StopStreamResponse(BaseModel):
    stopped: bool
    session_id: str
    camera_id: str


class ActiveStream(BaseModel):
    session_id: str
    camera_id: str
    stream_name: str
    viewer_count: int
    last_activity_at: datetime
    hls_url: Optional[str] = None
