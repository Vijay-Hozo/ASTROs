"""
orm_models.py - SQLAlchemy ORM models for the PS-3 Rule Engine.

These are the database entity models (different from models.py which are Pydantic models).
Used with SQLAlchemy AsyncSession for async database operations.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_text = Column(Text, nullable=False, doc="Original natural language rule")
    parsed_json = Column(Text, nullable=False, doc="Parsed JSON representation")
    rule_type = Column(String(50), nullable=True, doc="Type of rule (e.g., required_field)")
    severity = Column(String(20), default="error", doc="Severity level")
    created_at = Column(DateTime, default=datetime.utcnow, doc="Timestamp of rule creation")

    # Relationships
    validation_results: List["ValidationResult"] = relationship(
        "ValidationResult", back_populates="rule", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Rule(id={self.id}, rule_type={self.rule_type}, severity={self.severity})>"


class Invoice(Base):
    """Uploaded or provided invoice XML documents."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=True, doc="Original filename if uploaded")
    xml_content = Column(Text, nullable=False, doc="Raw XML invoice content")
    uploaded_at = Column(DateTime, default=datetime.utcnow, doc="Timestamp of upload/creation")

    # Relationships
    validation_results: List["ValidationResult"] = relationship(
        "ValidationResult", back_populates="invoice", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Invoice(id={self.id}, filename={self.filename})>"


class ValidationResult(Base):
    """Results of running a rule against an invoice."""
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=True)
    rule_text = Column(Text, nullable=False, doc="Rule text for reference")
    status = Column(String(20), nullable=False, doc="PASS / FAIL / ERROR / SKIP")
    message = Column(Text, doc="Explanation of result")
    rule_type = Column(String(50), nullable=True, doc="Type of validation")
    validated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="validation_results")
    rule = relationship("Rule", back_populates="validation_results")

    def __repr__(self):
        return f"<ValidationResult(id={self.id}, status={self.status})>"


# ── Database initialization ───────────────────────────────────────────────────

async def init_db():
    """Create all tables on startup if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"✅ Database initialised at {DB_PATH}")


async def get_db():
    """FastAPI dependency for getting an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
