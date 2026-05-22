import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def execute_sql_file(file_path):
    database_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        with open(file_path, "r") as f:
            sql = f.read()
        statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
        for statement in statements:
            await conn.execute(text(statement))
    await engine.dispose()
    print(f"Executed SQL file: {file_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python execute_sql_file.py <sql_file_path>")
        sys.exit(1)
    sql_file_path = sys.argv[1]
    asyncio.run(execute_sql_file(sql_file_path))