"""Phase 9: Add playback_sessions table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-23 03:00:00.000000

Why this migration exists:
  Phase 9 introduces the Playback System.
  A new table is needed to track temporary playback sessions:

  playback_sessions
    Stores one row per active or recently-expired playback session.
    Each session maps a user request to a temporary go2rtc stream
    that replays a Hikvision recording segment.
    Sessions auto-expire after an idle timeout (default 5 minutes).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Table: playback_sessions
    # ------------------------------------------------------------------
    op.create_table(
        "playback_sessions",

        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),

        # Session data
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("channel", sa.Integer(), nullable=False),

        # Recording window (stored as naive UTC datetimes)
        sa.Column("start_time", sa.DateTime(timezone=False), nullable=False),
        sa.Column("end_time",   sa.DateTime(timezone=False), nullable=False),

        # Temporary go2rtc stream name — unique per session
        sa.Column("stream_name", sa.String(255), nullable=False, unique=True),

        # Lifecycle timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),

        # Audit — FK to users.id (nullable)
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Indexes for common query patterns
    op.create_index(
        "ix_playback_sessions_device_id",
        "playback_sessions",
        ["device_id"],
    )
    op.create_index(
        "ix_playback_sessions_expires_at",
        "playback_sessions",
        ["expires_at"],
    )
    op.create_index(
        "ix_playback_sessions_created_by",
        "playback_sessions",
        ["created_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_playback_sessions_created_by",  table_name="playback_sessions")
    op.drop_index("ix_playback_sessions_expires_at",  table_name="playback_sessions")
    op.drop_index("ix_playback_sessions_device_id",   table_name="playback_sessions")
    op.drop_table("playback_sessions")
