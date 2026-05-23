from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.base import Base


DATABASE_URL = settings.database.get_database_url()

# ---------------------------------------------------------------------------
# Shared module-level singletons
# ---------------------------------------------------------------------------
# Create the engine ONCE at import time so the connection pool is shared
# across all requests and background workers.

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Shared session factory — used by both FastAPI dependency injection (get_db)
# and background workers (e.g. playback cleanup) that need a DB session
# outside of a request context.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_db():
    """Yield an AsyncSession for use in FastAPI route dependencies."""
    async with AsyncSessionLocal() as session:
        yield session
