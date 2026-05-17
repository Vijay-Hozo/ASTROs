import asyncio
import os
from sqlalchemy import text
from orm_models import engine

async def main():
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            ORDER BY table_name, column_name;
        """))
        current_table = ""
        for r in res:
            table, col, dtype = r[0], r[1], r[2]
            if table != current_table:
                print(f"\nTABLE: {table}")
                current_table = table
            print(f" - {col}: {dtype}")

asyncio.run(main())
