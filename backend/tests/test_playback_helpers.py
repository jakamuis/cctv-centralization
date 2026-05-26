from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.services.playback.playback_manager import _build_stream_name
from app.services.playback.playback_session import _to_utc_naive


pytestmark = pytest.mark.unit


def test_to_utc_naive_converts_aware_datetime_to_naive_utc():
    value = datetime.fromisoformat("2026-05-24T14:30:00+07:00")

    result = _to_utc_naive(value)

    assert result == datetime(2026, 5, 24, 7, 30, 0)
    assert result.tzinfo is None


def test_to_utc_naive_keeps_naive_datetime_unchanged():
    value = datetime(2026, 5, 24, 7, 30, 0)

    result = _to_utc_naive(value)

    assert result == value
    assert result.tzinfo is None


def test_build_stream_name_includes_device_channel_timestamp_and_unique_nonce():
    device_id = UUID("12345678-1234-5678-1234-567812345678")
    start_time = datetime(2026, 5, 24, 7, 30, 0, tzinfo=timezone.utc)

    first = _build_stream_name(device_id, 3, start_time)
    second = _build_stream_name(device_id, 3, start_time)

    assert first.startswith("playback_12345678_ch3_20260524T073000Z_")
    assert second.startswith("playback_12345678_ch3_20260524T073000Z_")
    assert first != second
