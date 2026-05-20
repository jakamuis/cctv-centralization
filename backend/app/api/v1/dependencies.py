from typing import AsyncGenerator
from app.db.session import async_session_maker, AsyncSession

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session