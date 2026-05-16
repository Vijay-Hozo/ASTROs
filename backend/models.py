"""
models.py - Merged file containing both Steve's Pydantic models 
AND the required SQLAlchemy database tables.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
from pydantic import BaseModel
from typing import Optional, List

# ─────────────────────────────────────────────
# 1. DATABASE TABLES (Satwiq's Fix)
# ─────────────────────────────────────────────

class Rule(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_text = Column(Text, nullable=False)
    parsed_json = Column(Text)  # JSON string
    severity = Column(String, default="error")
    created_at = Column(DateTime, default=datetime.utcnow)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    xml_content = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class ValidationResult(Base):
    __tablename__ = "validation_results"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    rule_id = Column(Integer, ForeignKey("rules.id"))
    status = Column(String) # PASS, FAIL, ERROR
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────
# 2. PYDANTIC SCHEMAS (Steve's Code)
# ─────────────────────────────────────────────

class RuleCreate(BaseModel):
    rule_text: str
    severity:  str = "error"

class RuleResponse(BaseModel):
    id:          int
    rule_text:   str
    rule_type:   Optional[str] = None
    parsed_json: str
    severity:    str
    created_at:  str

class InvoiceResponse(BaseModel):
    id:          int
    filename:    Optional[str] = None
    uploaded_at: str

class ValidateRequest(BaseModel):
    rule_text:   str
    xml_content: str

class BatchValidateRequest(BaseModel):
    invoice_id:  int
    rule_ids:    Optional[List[int]] = None

class ValidationResultItem(BaseModel):
    rule_id:    Optional[int] = None
    rule_text:  str
    rule_type:  Optional[str] = None
    status:     str
    message:    str
    field:      Optional[str] = None

class ValidationResponse(BaseModel):
    invoice_id: str
    summary: dict
    results: List[ValidationResultItem]

class DashboardStats(BaseModel):
    total_rules:       int
    total_invoices:    int
    total_validations: int
    passed:            int
    failed:            int

class HealthResponse(BaseModel):
    status:   str
    database: str
    version:  str = "1.0.0"
