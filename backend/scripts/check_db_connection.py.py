import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

async def test():
    database_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        result = await conn.execute("SELECT 1")
        print(result.scalar())
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test())