import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv
import os
import asyncio

from app.db.session import get_async_session_maker

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from main import app

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

from sqlalchemy import text

@pytest_asyncio.fixture(autouse=True)
async def cleanup_database():
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        # Truncate or delete from tables to clean test data
        await session.execute(text("TRUNCATE TABLE sites CASCADE;"))
        await session.execute(text("TRUNCATE TABLE devices CASCADE;"))
        await session.execute(text("TRUNCATE TABLE cameras CASCADE;"))
        await session.commit()

@pytest_asyncio.fixture
async def async_client(event_loop):

    transport = ASGITransport(
        app=app,
        raise_app_exceptions=True
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver"
    ) as client:

        yield client

    await transport.aclose()
