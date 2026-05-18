import asyncio
from sqlalchemy import text
from orm_models import DIRECT_DATABASE_URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from uuid import uuid4

async def main():
    print("[cache] Connecting to direct database URL...")
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
        print("[cache] Executing NOTIFY pgrst, 'reload schema'...")
        await conn.execute(text("NOTIFY pgrst, 'reload schema';"))
        print("[cache] Schema cache reload notification sent successfully!")
    await direct_engine.dispose()

asyncio.run(main())
