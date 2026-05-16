"""
orm_models.py - SQLAlchemy ORM models for the PS-3 Rule Engine.

These are the database entity models (different from models.py which are Pydantic models).
Used with SQLAlchemy AsyncSession for async database operations.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
import os

# ── Database URL ──────────────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "database.db")
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Create async engine
engine = create_async_engine(DB_URL, echo=False)

# Session factory for async context managers
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# Base for all models
Base = declarative_base()


# ── ORM Models ────────────────────────────────────────────────────────────────

class Rule(Base):
    """Stored natural-language rules parsed and persisted by users."""
    __tablename__ = "rules"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_text: Mapped[str]
    parsed_json: Mapped[str]
    rule_type: Mapped[Optional[str]] = mapped_column(default=None)
    severity: Mapped[str] = mapped_column(default="error")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    validation_results: Mapped[List["ValidationResult"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Rule(id={self.id}, rule_type={self.rule_type}, severity={self.severity})>"


class Invoice(Base):
    """Uploaded or provided invoice XML documents."""
    __tablename__ = "invoices"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[Optional[str]] = mapped_column(default=None)
    xml_content: Mapped[str]
    uploaded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    validation_results: Mapped[List["ValidationResult"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Invoice(id={self.id}, filename={self.filename})>"


class ValidationResult(Base):
    """Results of running a rule against an invoice."""
    __tablename__ = "validation_results"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"), default=None)
    rule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rules.id"), default=None)
    rule_text: Mapped[str]
    status: Mapped[str]
    message: Mapped[Optional[str]] = mapped_column(default=None)
    rule_type: Mapped[Optional[str]] = mapped_column(default=None)
    validated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    invoice: Mapped[Optional["Invoice"]] = relationship(back_populates="validation_results")
    rule: Mapped[Optional["Rule"]] = relationship(back_populates="validation_results")

    def __repr__(self):
        return f"<ValidationResult(id={self.id}, status={self.status})>"


# ── Database initialization ───────────────────────────────────────────────────

async def init_db():
    """Create all tables on startup if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"Database initialised at {DB_PATH}")


async def get_db():
    """FastAPI dependency for getting an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
