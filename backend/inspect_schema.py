import asyncio
from sqlalchemy import text
from orm_models import DIRECT_DATABASE_URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from uuid import uuid4

async def main():
    direct_engine = create_async_engine(
        DIRECT_DATABASE_URL,
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        },
    )
    async with direct_engine.begin() as conn:
        res = await conn.execute(text("SELECT column_name, ordinal_position, data_type FROM information_schema.columns WHERE table_name = 'samples' ORDER BY ordinal_position;"))
        print("SAMPLES TABLE COLUMNS:")
        for row in res:
            print(f" {row[0]}: position {row[1]}, type {row[2]}")
    await direct_engine.dispose()

asyncio.run(main())
