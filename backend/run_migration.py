import asyncio
import os
from sqlalchemy import text
from orm_models import DIRECT_DATABASE_URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from uuid import uuid4

async def main():
    print(f"[migration] Connecting to direct URL...")
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
        print("[migration] Running migrations...")
        
        # samples migrations
        print(" - Modifying samples table...")
        await conn.execute(text("ALTER TABLE samples ADD COLUMN IF NOT EXISTS status varchar DEFAULT 'default';"))
        await conn.execute(text("ALTER TABLE samples ADD COLUMN IF NOT EXISTS extracted_tags jsonb DEFAULT '[]'::jsonb;"))
        
        # xslt_files migrations
        print(" - Modifying xslt_files table...")
        await conn.execute(text("ALTER TABLE xslt_files ADD COLUMN IF NOT EXISTS status varchar DEFAULT 'default';"))
        await conn.execute(text("ALTER TABLE xslt_files ADD COLUMN IF NOT EXISTS description varchar;"))
        await conn.execute(text("ALTER TABLE xslt_files ADD COLUMN IF NOT EXISTS xslt_content varchar;"))
        await conn.execute(text("ALTER TABLE xslt_files ADD COLUMN IF NOT EXISTS rules_count integer DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE xslt_files ADD COLUMN IF NOT EXISTS rule_count integer DEFAULT 0;"))
        
        # xslt_sample_links migrations
        print(" - Modifying xslt_sample_links table...")
        await conn.execute(text("ALTER TABLE xslt_sample_links ADD COLUMN IF NOT EXISTS xslt_id varchar;"))
        await conn.execute(text("ALTER TABLE xslt_sample_links ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();"))

        # active_workspace migrations
        print(" - Modifying active_workspace table...")
        await conn.execute(text("ALTER TABLE active_workspace ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();"))
        
        print("[migration] Migrations executed successfully!")
        
    await direct_engine.dispose()

asyncio.run(main())
