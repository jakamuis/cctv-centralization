"""Initial Phase 5 tables migration with soft delete for devices"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql

revision = "1da1b116d228"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    # =========================
    # ENUMS
    # =========================

    device_type_enum = psql.ENUM(
        "NVR",
        "CAMERA",
        "ENCODER",
        "DECODER",
        "SWITCH",
        "SERVER",
        name="devicetypeenum",
        create_type=False,
    )

    device_status_enum = psql.ENUM(
        "ONLINE",
        "OFFLINE",
        "DEGRADED",
        "UNKNOWN",
        "MAINTENANCE",
        name="devicestatusenum",
        create_type=False,
    )

    online_status_enum = psql.ENUM(
        "ONLINE",
        "OFFLINE",
        "DEGRADED",
        "UNKNOWN",
        "MAINTENANCE",
        name="onlinestatusenum",
        create_type=False,
    )

    alert_type_enum = psql.ENUM(
        "DEVICE_OFFLINE",
        "DEVICE_ONLINE",
        "STORAGE_WARNING",
        "RECORDING_FAILURE",
        "STREAM_DOWN",
        "DEVICE_FLAPPING",
        name="alerttypeenum",
        create_type=False,
    )

    alert_severity_enum = psql.ENUM(
        "INFO",
        "WARNING",
        "CRITICAL",
        name="alertseverityenum",
        create_type=False,
    )

    stream_session_status_enum = psql.ENUM(
        "ACTIVE",
        "ENDED",
        "FAILED",
        name="streamsessionstatusenum",
        create_type=False,
    )

    # CREATE ENUM TYPES MANUALLY

    device_type_enum.create(op.get_bind(), checkfirst=True)
    device_status_enum.create(op.get_bind(), checkfirst=True)
    online_status_enum.create(op.get_bind(), checkfirst=True)
    alert_type_enum.create(op.get_bind(), checkfirst=True)
    alert_severity_enum.create(op.get_bind(), checkfirst=True)
    stream_session_status_enum.create(op.get_bind(), checkfirst=True)

    # =========================
    # SITES
    # =========================

    op.create_table(
        "sites",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # =========================
    # DEVICES
    # =========================

    op.create_table(
        "devices",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "site_id",
            psql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_type", device_type_enum, nullable=False),
        sa.Column("vendor", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("serial_number", sa.String(length=100), nullable=True),
        sa.Column("firmware_version", sa.String(length=50), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("port", sa.Integer, nullable=True),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("encrypted_password", sa.String(length=255), nullable=True),
        sa.Column("mac_address", sa.String(length=17), nullable=True),
        sa.Column("status", device_status_enum, nullable=False),
        sa.Column("heartbeat_interval_seconds", sa.Integer, nullable=False),
        sa.Column("offline_threshold_seconds", sa.Integer, nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_online_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_offline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # =========================
    # CAMERAS
    # =========================

    op.create_table(
        "cameras",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "device_id",
            psql.UUID(as_uuid=True),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel_number", sa.Integer, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("resolution", sa.String(length=50), nullable=True),
        sa.Column("codec", sa.String(length=50), nullable=True),
        sa.Column("fps", sa.Integer, nullable=True),
        sa.Column("bitrate", sa.Integer, nullable=True),
        sa.Column("stream_url", sa.String(length=500), nullable=True),
        sa.Column("recording_enabled", sa.Boolean(), nullable=False),
        sa.Column("motion_detection", sa.Boolean(), nullable=False),
        sa.Column("audio_enabled", sa.Boolean(), nullable=False),
        sa.Column("ptz_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # =========================
    # CURRENT DEVICE STATE
    # =========================

    op.create_table(
        "current_device_state",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "device_id",
            psql.UUID(as_uuid=True),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("online_status", online_status_enum, nullable=False),
        sa.Column("storage_usage", sa.Float(), nullable=True),
        sa.Column("recording_ok", sa.Boolean(), nullable=True),
        sa.Column("stream_ok", sa.Boolean(), nullable=True),
        sa.Column("cpu_usage", sa.Float(), nullable=True),
        sa.Column("memory_usage", sa.Float(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("health_score", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # =========================
    # TELEMETRY HISTORY
    # =========================

    op.create_table(
        "telemetry_history",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "device_id",
            psql.UUID(as_uuid=True),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )

    # =========================
    # ALERTS
    # =========================

    op.create_table(
        "alerts",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "device_id",
            psql.UUID(as_uuid=True),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("alert_type", alert_type_enum, nullable=False),
        sa.Column("severity", alert_severity_enum, nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
    )

    # =========================
    # STREAM SESSIONS
    # =========================

    op.create_table(
        "stream_sessions",
        sa.Column("id", psql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "camera_id",
            psql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewer_count", sa.Integer(), nullable=False),
        sa.Column("status", stream_session_status_enum, nullable=False),
    )


def downgrade():

    op.drop_table("stream_sessions")
    op.drop_table("alerts")
    op.drop_table("telemetry_history")
    op.drop_table("current_device_state")
    op.drop_table("cameras")
    op.drop_table("devices")
    op.drop_table("sites")

    op.execute("DROP TYPE IF EXISTS streamsessionstatusenum")
    op.execute("DROP TYPE IF EXISTS alertseverityenum")
    op.execute("DROP TYPE IF EXISTS alerttypeenum")
    op.execute("DROP TYPE IF EXISTS onlinestatusenum")
    op.execute("DROP TYPE IF EXISTS devicestatusenum")
    op.execute("DROP TYPE IF EXISTS devicetypeenum")