import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_tables_and_version():
    database_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        # Check if branches table exists
        result = await conn.execute(text(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'branches'"
            ");"
        ))
        branches_exists = result.scalar()

        # Check if cameras table exists
        result = await conn.execute(text(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'cameras'"
            ");"
        ))
        cameras_exists = result.scalar()

        # Get current alembic version
        result = await conn.execute(text(
            "SELECT version_num FROM alembic_version LIMIT 1;"
        ))
        alembic_version = result.scalar()

    await engine.dispose()

    print(f"branches table exists: {branches_exists}")
    print(f"cameras table exists: {cameras_exists}")
    print(f"alembic current version: {alembic_version}")

if __name__ == "__main__":
    asyncio.run(check_tables_and_version())