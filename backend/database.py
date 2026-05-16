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
