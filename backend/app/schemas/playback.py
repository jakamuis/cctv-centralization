"""
schemas/playback.py

Pydantic request/response schemas for the Phase 9 Playback API.

All schemas use strict typing and validation.
Credentials are never included in any response schema.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Recording search
# ---------------------------------------------------------------------------

class PlaybackSearchRequest(BaseModel):
    """Request body for POST /api/playback/search"""

    device_id: UUID = Field(..., description="UUID of the DiscoveredNVR")
    channel: int = Field(..., ge=1, le=64, description="NVR channel number (1-based)")
    start_time: datetime = Field(..., description="Search window start (UTC or offset-aware)")
    end_time: datetime = Field(..., description="Search window end (UTC or offset-aware)")

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v


class RecordingSegmentSchema(BaseModel):
    """One recording segment in the search response."""

    start: datetime
    end: datetime
    recording_type: str = "normal"
    duration_seconds: float

    model_config = {"from_attributes": True}


class PlaybackSearchResponse(BaseModel):
    """Response for POST /api/playback/search"""

    device_id: UUID
    channel: int
    segments: List[RecordingSegmentSchema]
    total_segments: int
    has_recordings: bool


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

class TimelineBlockSchema(BaseModel):
    """One block on the playback timeline (recording or gap)."""

    type: str  # "recording" | "gap"
    start: datetime
    end: datetime
    duration_seconds: float
    recording_type: Optional[str] = None


class PlaybackTimelineResponse(BaseModel):
    """Response for POST /api/playback/timeline"""

    device_id: UUID
    channel: int
    window_start: datetime
    window_end: datetime
    blocks: List[TimelineBlockSchema]
    total_recording_seconds: float
    has_recordings: bool


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------

class PlaybackSessionRequest(BaseModel):
    """Request body for POST /api/playback/session"""

    device_id: UUID = Field(..., description="UUID of the DiscoveredNVR")
    channel: int = Field(..., ge=1, le=64, description="NVR channel number (1-based)")
    start_time: datetime = Field(..., description="Playback start time")
    end_time: datetime = Field(..., description="Playback end time")

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v


class PlaybackSessionResponse(BaseModel):
    """
    Response for POST /api/playback/session.

    stream_url is the relative WebSocket path the frontend uses to
    connect to the go2rtc MSE/WebRTC stream — same protocol as live view.

    Credentials are NEVER included in this response.
    """

    session_id: UUID
    stream_name: str = Field(..., description="go2rtc stream key")
    stream_url: str = Field(
        ...,
        description="Relative WebSocket URL: /go2rtc/api/ws?src=<stream_name>",
    )
    expires_at: datetime
    device_id: UUID
    channel: int
    start_time: datetime
    end_time: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Session heartbeat / keep-alive
# ---------------------------------------------------------------------------

class PlaybackHeartbeatResponse(BaseModel):
    """Response for POST /api/playback/session/{id}/heartbeat"""

    session_id: UUID
    extended: bool
    expires_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Session deletion
# ---------------------------------------------------------------------------

class PlaybackSessionDeleteResponse(BaseModel):
    """Response for DELETE /api/playback/session/{id}"""

    session_id: UUID
    deleted: bool


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

class PlaybackDownloadRequest(BaseModel):
    """Request body for POST /api/playback/download"""

    device_id: UUID = Field(..., description="UUID of the DiscoveredNVR")
    channel: int = Field(..., ge=1, le=64, description="NVR channel number (1-based)")
    start_time: datetime = Field(..., description="Clip start time")
    end_time: datetime = Field(..., description="Clip end time")

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v

    @field_validator("end_time")
    @classmethod
    def max_clip_duration(cls, v: datetime, info) -> datetime:
        start = info.data.get("start_time")
        if start:
            duration = (v - start).total_seconds()
            if duration > 4 * 3600:  # 4 hours max
                raise ValueError("Clip duration cannot exceed 4 hours")
        return v
