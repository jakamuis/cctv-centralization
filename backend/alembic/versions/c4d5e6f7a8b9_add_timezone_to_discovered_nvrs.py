"""Add timezone column to discovered_nvrs

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-05-25 00:00:00.000000

Adds a timezone column to discovered_nvrs so the UI can correctly
convert user-entered local times to UTC when building RTSP playback queries.

Values: WIB (UTC+7), WITA (UTC+8), WIT (UTC+9). Defaults to WIB.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "discovered_nvrs",
        sa.Column("timezone", sa.String(10), nullable=False, server_default="WIB"),
    )


def downgrade() -> None:
    op.drop_column("discovered_nvrs", "timezone")
