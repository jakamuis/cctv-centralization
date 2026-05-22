from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.base import Base


DATABASE_URL = settings.database.get_database_url()


def get_engine():
    """Create the shared async engine used across the app.

    NOTE: We intentionally import ``Base`` from ``app.models.base`` so that
    *all* ORM models (including auth/RBAC models) share a single metadata
    object. Alembic's ``target_metadata`` points at this same Base, which
    ensures autogenerate can see every table.
    """

    return create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


def get_async_session_maker():
    engine = get_engine()
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db():
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        yield session