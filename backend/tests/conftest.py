import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv
import os

from app.db.session import AsyncSessionLocal

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from main import app

from sqlalchemy import text

@pytest_asyncio.fixture(autouse=True)
async def cleanup_database(request):
    if "unit" in request.keywords:
        yield
        return

    async with AsyncSessionLocal() as session:
        # Truncate or delete from tables to clean test data
        await session.execute(text("TRUNCATE TABLE sites CASCADE;"))
        await session.execute(text("TRUNCATE TABLE branches CASCADE;"))
        await session.execute(text("TRUNCATE TABLE devices CASCADE;"))
        await session.execute(text("TRUNCATE TABLE cameras CASCADE;"))
        await session.commit()
    yield

@pytest_asyncio.fixture
async def async_client():

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
