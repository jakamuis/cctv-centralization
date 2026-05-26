"""Add vendor column to discovered_nvrs

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-05-26 00:00:00.000000

Adds a vendor column so the discovery pipeline can handle both Hikvision
(ISAPI) and ACTi SNVR (HTTP multipart/H264) devices from the same CSV.

Values: "hikvision" (default, backward-compatible) | "acti_snvr"
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "discovered_nvrs",
        sa.Column("vendor", sa.String(50), nullable=False, server_default="hikvision"),
    )


def downgrade() -> None:
    op.drop_column("discovered_nvrs", "vendor")
