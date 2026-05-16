#!/usr/bin/env python
"""
Initialize database schema only (no data)
Run this script to create a fresh database with empty tables
"""

import asyncio
from orm_models import init_db

async def main():
    """Initialize database and create all tables."""
    print("Initializing database schema...")
    await init_db()
    print("✓ Database schema created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
