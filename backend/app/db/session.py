from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings


DATABASE_URL = settings.database.database_url

def get_engine():
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

Base = declarative_base()


async def get_db():
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        yield session