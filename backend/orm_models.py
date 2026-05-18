"""
orm_models.py - SQLAlchemy ORM models.
Supabase (PostgreSQL) primary -> SQLite fallback.
"""

import os
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

# Database URL
# Enforce Supabase PostgreSQL as primary database (no SQLite fallback)
SUPABASE_URL = os.getenv("SUPABASE_DB_URL", "").strip()
if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_DB_URL is not set in the environment. SQLite is disabled.")

DATABASE_URL = SUPABASE_URL
DIRECT_DATABASE_URL = SUPABASE_URL.replace(":6543", ":5432")
print("[db] Using Supabase PostgreSQL (Production)")

from sqlalchemy.pool import NullPool

from uuid import uuid4

# Setup connect_args for PostgreSQL
connect_args = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


class Rule(Base):
    __tablename__ = "rules"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    xslt_id: Mapped[Optional[str]] = mapped_column(ForeignKey("xslt_files.id"), default=None)
    rule_text: Mapped[str]
    parsed_json: Mapped[str]
    rule_type: Mapped[Optional[str]] = mapped_column(default=None)
    field: Mapped[Optional[str]] = mapped_column(default=None)
    operation: Mapped[Optional[str]] = mapped_column(default=None)
    severity: Mapped[str] = mapped_column(default="error")
    xslt_logic: Mapped[Optional[str]] = mapped_column(default=None)
    xpath_logic: Mapped[Optional[str]] = mapped_column(default=None)
    python_logic: Mapped[Optional[str]] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    validation_results: Mapped[List["ValidationResult"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )
    logic_versions: Mapped[List["ValidationLogic"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class Invoice(Base):
    __tablename__ = "invoices"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[Optional[str]] = mapped_column(default=None)
    xslt_filename: Mapped[Optional[str]] = mapped_column(default=None)
    xml_content: Mapped[str]
    file_size: Mapped[Optional[int]] = mapped_column(default=None)
    upload_status: Mapped[str] = mapped_column(default="uploaded")
    total_rules_tested: Mapped[int] = mapped_column(default=0)
    passed_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    uploaded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    validation_results: Mapped[List["ValidationResult"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    reports: Mapped[List["FileValidationReport"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class ValidationResult(Base):
    __tablename__ = "validation_results"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"), default=None)
    rule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rules.id"), default=None)
    rule_text: Mapped[str]
    status: Mapped[str]
    message: Mapped[Optional[str]] = mapped_column(default=None)
    rule_type: Mapped[Optional[str]] = mapped_column(default=None)
    rule_severity: Mapped[Optional[str]] = mapped_column(default=None)
    field_checked: Mapped[Optional[str]] = mapped_column(default=None)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(default=None)
    xslt_result: Mapped[Optional[str]] = mapped_column(default=None)
    parsed_validation_result: Mapped[Optional[str]] = mapped_column(default=None)
    validated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    invoice: Mapped[Optional["Invoice"]] = relationship(back_populates="validation_results")
    rule: Mapped[Optional["Rule"]] = relationship(back_populates="validation_results")


class Sample(Base):
    __tablename__ = "samples"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str]
    xml_content: Mapped[str]
    tags_json: Mapped[str] = mapped_column(default="{}")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class XsltSampleLink(Base):
    __tablename__ = "xslt_sample_links"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey("samples.id"))
    xslt_file_id: Mapped[str]  # UUID reference to Supabase Storage XSLT file
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class ActiveWorkspace(Base):
    __tablename__ = "active_workspace"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(default="default", unique=True)
    sample_id: Mapped[Optional[int]] = mapped_column(ForeignKey("samples.id"), default=None)
    xslt_id: Mapped[Optional[str]] = mapped_column(default=None)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class XsltFile(Base):
    __tablename__ = "xslt_files"
    __allow_unmapped__ = True

    id: Mapped[str] = mapped_column(primary_key=True)
    filename: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)



class ValidationLogic(Base):
    __tablename__ = "validation_logic"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id"))
    xpath_logic: Mapped[Optional[str]] = mapped_column(default=None)
    xslt_logic: Mapped[Optional[str]] = mapped_column(default=None)
    python_logic: Mapped[Optional[str]] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    rule: Mapped["Rule"] = relationship(back_populates="logic_versions")


class FileValidationReport(Base):
    __tablename__ = "file_validation_reports"
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    passed_rules: Mapped[int] = mapped_column(default=0)
    failed_rules: Mapped[int] = mapped_column(default=0)
    summary_json: Mapped[Optional[str]] = mapped_column(default=None)
    execution_status: Mapped[str] = mapped_column(default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    invoice: Mapped["Invoice"] = relationship(back_populates="reports")


async def init_db():
    global engine, AsyncSessionLocal
    try:
        # use a NullPool direct engine on port 5432
        direct_engine = create_async_engine(
            DIRECT_DATABASE_URL,  # port 5432, not 6543
            poolclass=NullPool,
            connect_args={
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
            },
        )
        async with direct_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await direct_engine.dispose()
        print("Database initialised (Supabase via Direct Connection)")
    except Exception as e:
        print(f"[db] Database initialization failed: {e}")
        raise e


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
