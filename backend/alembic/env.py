from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from dotenv import load_dotenv

load_dotenv()

import os
import sys

sys.path.append(os.path.abspath("."))

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.models.base import Base
import app.models

# Import all models to ensure they are registered for Alembic autogenerate
# Commenting out models with foreign key dependencies that cause import errors during migration generation
# from app.models.user import User
# from app.models.audit_log import AuditLog
from app.models.branch import Branch
from app.models.camera import Camera
# from app.models.role import Role
# from app.models.device import Device
from app.models.site import Site
# from app.models.alerts import Alerts  # Commented out due to import error
# from app.models.current_device_state import CurrentDeviceState
# from app.models.telemetry_history import TelemetryHistory
# from app.models.stream_sessions import StreamSessions  # Commented out due to import error

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/cctv_db"
)

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()