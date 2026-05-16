"""
database.py - SQLAlchemy database setup.
Provides the async engine and session factory.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./invoice_rules.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
"""
database.py — Forwarding imports from orm_models for backward compatibility.

The actual SQLAlchemy ORM setup is in orm_models.py
"""

# Forward imports for backward compatibility
from orm_models import (
    engine,
    AsyncSessionLocal,
    get_db,
    init_db,
    Base,
    Rule,
    Invoice,
    ValidationResult,
)

__all__ = [
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    "Base",
    "Rule",
    "Invoice",
    "ValidationResult",
]
