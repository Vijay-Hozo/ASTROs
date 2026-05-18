import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("SUPABASE_DB_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("SUPABASE_DB_URL is not set in the environment. SQLite is disabled.")

DIRECT_DATABASE_URL = DATABASE_URL.replace(":6543", ":5432")

async def run_migration():
    from uuid import uuid4
    from sqlalchemy.pool import NullPool
    engine = create_async_engine(
        DIRECT_DATABASE_URL,
        echo=True,
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        },
    )
    
    # 1. Add xslt_id to rules
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE rules ADD COLUMN xslt_id VARCHAR;"))
            print("Added xslt_id to rules")
        except Exception as e:
            print(f"Error adding xslt_id (maybe already exists): {e}")

    # 2. Add xslt_filename to invoices
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE invoices ADD COLUMN xslt_filename VARCHAR;"))
            print("Added xslt_filename to invoices")
        except Exception as e:
            print(f"Error adding xslt_filename (maybe already exists): {e}")
            
    # 3. Create xslt_files table
    async with engine.begin() as conn:
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS xslt_files (
                    id VARCHAR PRIMARY KEY,
                    filename VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT now()
                );
            """))
            print("Created xslt_files table")
        except Exception as e:
            print(f"Error creating xslt_files table: {e}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
