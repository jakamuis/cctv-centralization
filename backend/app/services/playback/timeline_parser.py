"""
services/playback/timeline_parser.py

Converts raw ISAPI recording segments into structured timeline blocks
suitable for frontend rendering.

Responsibilities:
  - Merge overlapping/adjacent segments
  - Detect gaps between segments
  - Generate timeline blocks with type annotations
  - Support future zoom/resolution levels
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.services.playback.hikvision_playback import RecordingSegment

logger = logging.getLogger(__name__)

# Minimum gap duration to be reported as a gap block (seconds)
MIN_GAP_SECONDS = 5


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TimelineBlock:
    """
    One block on the playback timeline.

    type:
      "recording" — a continuous recording segment
      "gap"       — a period with no recording
    """
    type: str           # "recording" | "gap"
    start: datetime     # UTC-aware
    end: datetime       # UTC-aware
    recording_type: Optional[str] = None  # "normal", "motion", "alarm", etc.
    duration_seconds: float = field(init=False)

    def __post_init__(self):
        self.duration_seconds = (self.end - self.start).total_seconds()

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_seconds": self.duration_seconds,
            "recording_type": self.recording_type,
        }


@dataclass
class TimelineResult:
    """Full timeline for a requested time window."""
    window_start: datetime
    window_end: datetime
    blocks: List[TimelineBlock]
    total_recording_seconds: float
    has_recordings: bool

    def to_dict(self) -> dict:
        return {
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "blocks": [b.to_dict() for b in self.blocks],
            "total_recording_seconds": self.total_recording_seconds,
            "has_recordings": self.has_recordings,
        }


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is UTC-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _merge_segments(segments: List[RecordingSegment]) -> List[RecordingSegment]:
    """
    Merge overlapping or adjacent recording segments.

    Two segments are merged if the gap between them is less than
    MIN_GAP_SECONDS (avoids spurious gaps from NVR clock jitter).
    """
    if not segments:
        return []

    sorted_segs = sorted(segments, key=lambda s: s.start)
    merged: List[RecordingSegment] = [sorted_segs[0]]

    for seg in sorted_segs[1:]:
        last = merged[-1]
        gap = (seg.start - last.end).total_seconds()
        if gap <= MIN_GAP_SECONDS:
            # Extend the last segment
            merged[-1] = RecordingSegment(
                start=last.start,
                end=max(last.end, seg.end),
                track_id=last.track_id,
                recording_type=last.recording_type,
            )
        else:
            merged.append(seg)

    return merged


def build_timeline(
    segments: List[RecordingSegment],
    window_start: datetime,
    window_end: datetime,
) -> TimelineResult:
    """
    Build a complete timeline for the requested window.

    Steps:
      1. Clamp segments to the requested window
      2. Merge overlapping/adjacent segments
      3. Fill gaps between segments with gap blocks
      4. Fill leading/trailing gaps if needed

    Returns a TimelineResult with all blocks sorted by start time.
    """
    ws = _ensure_utc(window_start)
    we = _ensure_utc(window_end)

    # Clamp and filter segments to the window
    clamped: List[RecordingSegment] = []
    for seg in segments:
        seg_start = _ensure_utc(seg.start)
        seg_end = _ensure_utc(seg.end)
        # Skip segments entirely outside the window
        if seg_end <= ws or seg_start >= we:
            continue
        # Clamp to window boundaries
        clamped.append(RecordingSegment(
            start=max(seg_start, ws),
            end=min(seg_end, we),
            track_id=seg.track_id,
            recording_type=seg.recording_type,
        ))

    merged = _merge_segments(clamped)

    blocks: List[TimelineBlock] = []
    cursor = ws

    for seg in merged:
        seg_start = _ensure_utc(seg.start)
        seg_end = _ensure_utc(seg.end)

        # Gap before this segment
        if seg_start > cursor:
            gap_duration = (seg_start - cursor).total_seconds()
            if gap_duration >= MIN_GAP_SECONDS:
                blocks.append(TimelineBlock(
                    type="gap",
                    start=cursor,
                    end=seg_start,
                ))

        # Recording block
        blocks.append(TimelineBlock(
            type="recording",
            start=seg_start,
            end=seg_end,
            recording_type=seg.recording_type,
        ))
        cursor = seg_end

    # Trailing gap
    if cursor < we:
        gap_duration = (we - cursor).total_seconds()
        if gap_duration >= MIN_GAP_SECONDS:
            blocks.append(TimelineBlock(
                type="gap",
                start=cursor,
                end=we,
            ))

    total_recording = sum(
        b.duration_seconds for b in blocks if b.type == "recording"
    )

    logger.debug(
        "Timeline built: %d blocks, %.1fs recording in window [%s, %s]",
        len(blocks), total_recording,
        ws.isoformat(), we.isoformat(),
    )

    return TimelineResult(
        window_start=ws,
        window_end=we,
        blocks=blocks,
        total_recording_seconds=total_recording,
        has_recordings=total_recording > 0,
    )


def segments_to_simple_list(segments: List[RecordingSegment]) -> List[dict]:
    """
    Convert recording segments to the simple list format used by
    POST /api/playback/search response.
    """
    return [
        {
            "start": seg.start.isoformat(),
            "end": seg.end.isoformat(),
            "recording_type": seg.recording_type,
            "duration_seconds": (seg.end - seg.start).total_seconds(),
        }
        for seg in segments
    ]
