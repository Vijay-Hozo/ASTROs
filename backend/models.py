"""
models.py — Pydantic request/response models for FastAPI.
These define what the API accepts and returns.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─── Rule models ──────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    rule_text: str
    severity:  str = "error"


class RuleResponse(BaseModel):
    id:          int
    rule_text:   str
    rule_type:   Optional[str]
    parsed_json: str
    severity:    str
    created_at:  str


# ─── Invoice models ───────────────────────────────────────────────────────────

class InvoiceResponse(BaseModel):
    id:          int
    filename:    Optional[str]
    uploaded_at: str


# ─── Validation models ────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    rule_text:   str
    xml_content: str


class BatchValidateRequest(BaseModel):
    invoice_id:  int              # stored invoice ID
    rule_ids:    Optional[list[int]] = None   # None = run all saved rules


class ValidationResultItem(BaseModel):
    rule_id:    Optional[int]
    rule_text:  str
    rule_type:  Optional[str]
    status:     str               # PASS / FAIL / SKIP / ERROR
    message:    str
    field:      Optional[str]


class ValidationResponse(BaseModel):
    invoice_id: str
    summary: dict                 # { total, passed, failed }
    results: list[ValidationResultItem]


# ─── Dashboard models ─────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_rules:       int
    total_invoices:    int
    total_validations: int
    passed:            int
    failed:            int


# ─── Health model ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:   str
    database: str
    version:  str = "1.0.0"