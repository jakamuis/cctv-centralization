"""SQLAlchemy ORM models package.

Importing models here ensures they are registered on the shared ``Base``
metadata when ``app.models`` is imported (e.g. from Alembic's ``env.py``).

This is especially important for auth/RBAC models so that Alembic
autogenerate can see ``users``, ``roles``, ``permissions``, ``user_roles``,
``role_permissions`` and ``audit_logs`` tables.
"""

from .site import Site
from .device import Device
from .branch import Branch
from .camera import Camera
from .telemetry_history import TelemetryHistory
from .current_device_state import CurrentDeviceState
from .alerts import Alert
from .stream_sessions import StreamSession
from .audit_log import AuditLog
from .user import User  # auth model
from .role import Role, Permission  # auth/RBAC models

# Phase 7B — Discovery models (must be imported so Alembic sees the tables)
from .discovered_nvr import DiscoveredNVR
from .nvr_channel import NVRChannel

# Removed Region import as it is no longer used
# from app.models.region import Region
