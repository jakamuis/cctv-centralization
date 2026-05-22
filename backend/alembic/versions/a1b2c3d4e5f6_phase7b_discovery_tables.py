"""Phase 7B: Add discovered_nvrs and nvr_channels tables

Revision ID: a1b2c3d4e5f6
Revises: e3f8b87c7984
Create Date: 2026-05-23 01:00:00.000000

Why this migration exists:
  Phase 7B introduces the Seeded Hikvision Auto Discovery pipeline.
  Two new tables are needed:

  discovered_nvrs
    Stores one row per NVR device seeded from the Google Sheet CSV.
    Acts as the parent for nvr_channels.
    Natural unique key: (site_code, nvr_ip, http_port).

  nvr_channels
    Stores one row per camera channel on a discovered NVR.
    Natural unique key: (nvr_id, channel_id).
    Cascade-deletes when the parent NVR row is deleted.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "e3f8b87c7984"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Table: discovered_nvrs
    # ------------------------------------------------------------------
    op.create_table(
        "discovered_nvrs",

        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),

        # Seed data (from CSV)
        sa.Column("site_code",   sa.String(100),  nullable=False),
        sa.Column("branch_name", sa.String(255),  nullable=True),
        sa.Column("nvr_ip",      sa.String(45),   nullable=False),
        sa.Column("http_port",   sa.Integer(),    nullable=False, server_default="80"),
        sa.Column("rtsp_port",   sa.Integer(),    nullable=False, server_default="554"),
        sa.Column("username",    sa.String(100),  nullable=False),
        sa.Column("password",    sa.String(255),  nullable=False),

        # Device info (from ISAPI)
        sa.Column("device_name",      sa.String(255), nullable=True),
        sa.Column("model",            sa.String(100), nullable=True),
        sa.Column("serial_number",    sa.String(100), nullable=True),
        sa.Column("mac_address",      sa.String(17),  nullable=True),
        sa.Column("firmware_version", sa.String(50),  nullable=True),
        sa.Column("device_type",      sa.String(50),  nullable=True),

        # Sync metadata
        sa.Column("sync_status",   sa.String(50),  nullable=False, server_default="synced"),
        sa.Column("sync_error",    sa.String(500), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),

        # Unique constraint — prevents duplicate rows for the same device
        sa.UniqueConstraint(
            "site_code", "nvr_ip", "http_port",
            name="uq_discovered_nvr_site_ip_port",
        ),
    )

    # Indexes for common query patterns
    op.create_index(
        "ix_discovered_nvrs_site_code",
        "discovered_nvrs",
        ["site_code"],
    )
    op.create_index(
        "ix_discovered_nvrs_nvr_ip",
        "discovered_nvrs",
        ["nvr_ip"],
    )
    op.create_index(
        "ix_discovered_nvrs_serial_number",
        "discovered_nvrs",
        ["serial_number"],
    )

    # ------------------------------------------------------------------
    # Table: nvr_channels
    # ------------------------------------------------------------------
    op.create_table(
        "nvr_channels",

        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),

        # Foreign key → discovered_nvrs
        sa.Column(
            "nvr_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovered_nvrs.id", ondelete="CASCADE"),
            nullable=False,
        ),

        # Channel data (from ISAPI)
        sa.Column("channel_id",   sa.String(20),  nullable=False),
        sa.Column("channel_name", sa.String(255), nullable=True),
        sa.Column("ip_address",   sa.String(45),  nullable=True),
        sa.Column("manage_port",  sa.Integer(),   nullable=True),
        sa.Column("protocol",     sa.String(50),  nullable=True),
        sa.Column("is_enabled",   sa.Boolean(),   nullable=False, server_default="true"),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),

        # Unique constraint — one channel_id per NVR
        sa.UniqueConstraint(
            "nvr_id", "channel_id",
            name="uq_nvr_channel_nvr_channel_id",
        ),
    )

    # Index for FK lookups (channel list by NVR)
    op.create_index(
        "ix_nvr_channels_nvr_id",
        "nvr_channels",
        ["nvr_id"],
    )


def downgrade() -> None:
    # Drop child table first (FK dependency)
    op.drop_index("ix_nvr_channels_nvr_id", table_name="nvr_channels")
    op.drop_table("nvr_channels")

    op.drop_index("ix_discovered_nvrs_serial_number", table_name="discovered_nvrs")
    op.drop_index("ix_discovered_nvrs_nvr_ip",        table_name="discovered_nvrs")
    op.drop_index("ix_discovered_nvrs_site_code",     table_name="discovered_nvrs")
    op.drop_table("discovered_nvrs")
