"""
main.py - FastAPI application entry point for the PS-3 Natural Language Rule Engine.

All routes are defined here. Business logic is delegated to:
  - rule_parser.py  (parse natural language → JSON)
  - xml_reader.py   (extract fields from XML)
  - evaluator.py    (batch scoring engine)          ← Satwiq
  - executor.py     (low-level rule execution)      ← Steve
  - database.py     (DB session factory)            ← Steve
  - models.py       (ORM models)                    ← Steve
  - schemas.py      (Pydantic models)               ← Satwiq

Run locally:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware

from evaluator import Evaluator
from rule_parser import RuleParser
from schemas import (
    ValidateRequest,
    ValidateBatchRequest,
    SaveRuleRequest,
    BatchEvaluateRequest,
    ValidationResult,
    BatchValidationResponse,
    BatchSummary,
    SavedRuleResponse,
    InvoiceResponse,
    ResultRecord,
    DashboardStats,
    TrendResponse,
    TrendPoint,
    HealthResponse,
    DatasetGenerateResponse,
    DeleteResponse,
    ParsedRule,
)

# ── DB imports (Steve's modules) ─────────────────────────────────────────────
# Imported defensively so main.py still boots if Steve's files aren't ready yet.
try:
    from orm_models import (
        get_db, init_db, Rule, Invoice, ValidationResult, AsyncSessionLocal
    )
    from sqlalchemy.ext.asyncio import AsyncSession
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False
    AsyncSession = None  # type: ignore
    get_db = None  # type: ignore

# ── Dataset generator (dataset_gen.py, moved by Steve) ───────────────────────
try:
    from dataset_gen import generate_dataset
    _DATASET_GEN_AVAILABLE = True
except ImportError:
    _DATASET_GEN_AVAILABLE = False

# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────

app = FastAPI(
    title="PS-3 Natural Language Rule Engine",
    description=(
        "Converts plain-English invoice validation rules into executable logic "
        "and validates XML invoices — no XSLT or hardcoded scripts required."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Vercel frontend and local dev
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    os.getenv("FRONTEND_URL", "https://ps3-rule-engine.vercel.app"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared evaluator instance (stateless, safe to reuse)
evaluator = Evaluator()
parser = RuleParser()


# ── DB lifecycle ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    if _DB_AVAILABLE:
        await init_db()


# ─────────────────────────────────────────────
# HELPER: build ValidationResult response dict
# ─────────────────────────────────────────────

def _to_validation_result(er) -> dict:
    """Convert an EvaluationResult to a schema-compatible dict."""
    parsed = er.parsed_rule
    parsed_schema = None
    if isinstance(parsed, dict):
        parsed_schema = {
            "rule_type": parsed.get("rule_type", "unknown"),
            "field": parsed.get("field"),
            "operation": parsed.get("operation"),
            "base_field": parsed.get("base_field"),
            "value": parsed.get("value"),
            "condition_field": parsed.get("condition_field"),
            "condition_value": parsed.get("condition_value"),
        }
    return {
        "rule_id": er.rule_id,
        "rule_text": er.rule_text,
        "parsed_rule": parsed_schema,
        "result": er.result,
        "message": er.message,
        "invoice_id": er.invoice_id,
    }


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Quick system status check. Returns 200 if the API is running."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────
# VALIDATE — single rule + single XML
# ─────────────────────────────────────────────

@app.post("/validate", response_model=ValidationResult, tags=["Validation"])
async def validate_single(body: ValidateRequest):
    """
    Validate ONE natural-language rule against ONE XML invoice.

    Steps:
    1. Parse rule text → structured JSON
    2. Extract fields from XML
    3. Execute the rule
    4. Return PASS / FAIL / ERROR with an explanation message
    """
    er = evaluator.evaluate_one(body.rule_text, body.xml_content)
    return _to_validation_result(er)


# ─────────────────────────────────────────────
# VALIDATE — single rule + many XMLs
# ─────────────────────────────────────────────

@app.post("/validate/batch", response_model=BatchValidationResponse, tags=["Validation"])
async def validate_batch(body: ValidateBatchRequest):
    """
    Validate ONE natural-language rule against MANY XML invoices.

    Returns an array of results plus a summary (total / passed / failed).
    """
    results, summary = evaluator.evaluate_rule_against_many(
        body.rule_text, body.xml_files
    )
    return {
        "results": [_to_validation_result(r) for r in results],
        "summary": summary.to_dict(),
    }


# ─────────────────────────────────────────────
# VALIDATE — all saved rules against one XML
# ─────────────────────────────────────────────

@app.post("/validate/all-rules", response_model=BatchValidationResponse, tags=["Validation"])
async def validate_all_saved_rules(body: BatchEvaluateRequest):
    """
    Run ALL saved rules in the database against ONE XML invoice.

    Requires database.py to be available.
    """
    if not _DB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Database not available. Check database.py is present.",
        )

    async for db in get_db():
        from sqlalchemy import select
        stmt = select(models.Rule)
        result = await db.execute(stmt)
        rules = result.scalars().all()

    if not rules:
        raise HTTPException(status_code=404, detail="No rules saved in the database")

    rule_dicts = [
        {"id": r.id, "rule_text": r.rule_text}
        for r in rules
    ]
    results, summary = evaluator.evaluate_many_rules(rule_dicts, body.xml_content)
    return {
        "results": [_to_validation_result(r) for r in results],
        "summary": summary.to_dict(),
    }


# ─────────────────────────────────────────────
# RULES — CRUD
# ─────────────────────────────────────────────

@app.post("/rules", response_model=SavedRuleResponse, tags=["Rules"])
async def save_rule(body: SaveRuleRequest):
    """
    Parse and persist a new natural-language rule to the database.
    Returns the stored rule including its generated ID.
    """
    if not _DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    parsed = parser.parse(body.rule_text)

    async for db in get_db():
        rule = models.Rule(
            rule_text=body.rule_text,
            parsed_json=json.dumps(parsed),
            severity=body.severity,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)

    return {
        "id": rule.id,
        "rule_text": rule.rule_text,
        "parsed_json": parsed,
        "severity": rule.severity,
        "created_at": rule.created_at.isoformat() if rule.created_at else "",
    }


@app.get("/rules", response_model=List[SavedRuleResponse], tags=["Rules"])
async def list_rules():
    """Return all saved rules, newest first."""
    if not _DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    async for db in get_db():
        from sqlalchemy import select
        stmt = select(models.Rule).order_by(models.Rule.created_at.desc())
        result = await db.execute(stmt)
        rules = result.scalars().all()

    return [
        {
            "id": r.id,
            "rule_text": r.rule_text,
            "parsed_json": json.loads(r.parsed_json) if r.parsed_json else None,
            "severity": r.severity,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rules
    ]


@app.delete("/rules/{rule_id}", response_model=DeleteResponse, tags=["Rules"])
async def delete_rule(rule_id: int):
    """Delete a saved rule by its ID."""
    if not _DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    async for db in get_db():
        rule = await db.get(models.Rule, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        await db.delete(rule)
        await db.commit()

    return {"message": f"Rule {rule_id} deleted", "id": rule_id}


# ─────────────────────────────────────────────
# INVOICES
# ─────────────────────────────────────────────

@app.post("/invoices", response_model=InvoiceResponse, tags=["Invoices"])
async def upload_invoice(file: UploadFile = File(...)):
    """
    Upload an XML invoice file. Stores the raw content in the database.
    Returns the stored invoice record with its ID.
    """
    if not _DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    if not file.filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="Only .xml files are accepted")

    content = await file.read()
    xml_str = content.decode("utf-8")

    async for db in get_db():
        invoice = models.Invoice(
            filename=file.filename,
            xml_content=xml_str,
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

    return {
        "id": invoice.id,
        "filename": invoice.filename,
        "uploaded_at": invoice.uploaded_at.isoformat() if invoice.uploaded_at else "",
        "validation_status": None,
    }


@app.get("/invoices", response_model=List[InvoiceResponse], tags=["Invoices"])
async def list_invoices():
    """Return all uploaded invoices, newest first."""
    if not _DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    async for db in get_db():
        from sqlalchemy import select
        stmt = select(models.Invoice).order_by(models.Invoice.uploaded_at.desc())
        result = await db.execute(stmt)
        invoices = result.scalars().all()

    return [
        {
            "id": inv.id,
            "filename": inv.filename,
            "uploaded_at": inv.uploaded_at.isoformat() if inv.uploaded_at else "",
            "validation_status": None,
        }
        for inv in invoices
    ]


# ─────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────

@app.get("/results", response_model=List[ResultRecord], tags=["Results"])
async def list_results():
    """Return all stored validation results, newest first."""
    if not _DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    async for db in get_db():
        from sqlalchemy import select
        stmt = select(models.ValidationResult).order_by(
            models.ValidationResult.id.desc()
        )
        result = await db.execute(stmt)
        records = result.scalars().all()

    return [
        {
            "id": r.id,
            "invoice_id": r.invoice_id,
            "rule_id": r.rule_id,
            "status": r.status,
            "message": r.message,
        }
        for r in records
    ]


@app.get("/results/{invoice_id}", response_model=List[ResultRecord], tags=["Results"])
async def get_results_for_invoice(invoice_id: int):
    """Return all validation results for a specific invoice."""
    if not _DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")

    async for db in get_db():
        from sqlalchemy import select
        stmt = select(models.ValidationResult).where(
            models.ValidationResult.invoice_id == invoice_id
        )
        result = await db.execute(stmt)
        records = result.scalars().all()

    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No results found for invoice {invoice_id}",
        )

    return [
        {
            "id": r.id,
            "invoice_id": r.invoice_id,
            "rule_id": r.rule_id,
            "status": r.status,
            "message": r.message,
        }
        for r in records
    ]


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.get("/dashboard/stats", response_model=DashboardStats, tags=["Dashboard"])
async def dashboard_stats():
    """
    Return aggregated stat counts for the dashboard cards:
    total rules, total invoices, total validations, pass/fail counts.
    """
    if not _DB_AVAILABLE:
        # Return zeros so the frontend still renders
        return {
            "total_rules": 0,
            "total_invoices": 0,
            "total_validations": 0,
            "total_passed": 0,
            "total_failed": 0,
            "pass_rate": 0.0,
        }

    from sqlalchemy import select, func

    async for db in get_db():
        total_rules = (await db.execute(select(func.count(models.Rule.id)))).scalar() or 0
        total_invoices = (await db.execute(select(func.count(models.Invoice.id)))).scalar() or 0
        total_validations = (
            await db.execute(select(func.count(models.ValidationResult.id)))
        ).scalar() or 0
        total_passed = (
            await db.execute(
                select(func.count(models.ValidationResult.id)).where(
                    models.ValidationResult.status == "PASS"
                )
            )
        ).scalar() or 0
        total_failed = (
            await db.execute(
                select(func.count(models.ValidationResult.id)).where(
                    models.ValidationResult.status == "FAIL"
                )
            )
        ).scalar() or 0

    pass_rate = (
        round(total_passed / total_validations * 100, 1) if total_validations > 0 else 0.0
    )

    return {
        "total_rules": total_rules,
        "total_invoices": total_invoices,
        "total_validations": total_validations,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "pass_rate": pass_rate,
    }


@app.get("/dashboard/trends", response_model=TrendResponse, tags=["Dashboard"])
async def dashboard_trends():
    """
    Return pass/fail counts grouped by date for the last 7 days.
    Used to render the trend chart on the dashboard.
    """
    if not _DB_AVAILABLE:
        return {"points": []}

    from sqlalchemy import select, func, cast
    from sqlalchemy import Date as SADate

    async for db in get_db():
        stmt = (
            select(
                cast(models.ValidationResult.created_at, SADate).label("day"),
                models.ValidationResult.status,
                func.count(models.ValidationResult.id).label("cnt"),
            )
            .group_by("day", models.ValidationResult.status)
            .order_by("day")
        )
        rows = (await db.execute(stmt)).all()

    # Pivot into {date: {PASS: n, FAIL: n}}
    pivot: dict = {}
    for day, status, cnt in rows:
        key = str(day)
        if key not in pivot:
            pivot[key] = {"PASS": 0, "FAIL": 0}
        pivot[key][status] = pivot[key].get(status, 0) + cnt

    points = [
        {"date": k, "passed": v.get("PASS", 0), "failed": v.get("FAIL", 0)}
        for k, v in sorted(pivot.items())
    ]
    return {"points": points}


# ─────────────────────────────────────────────
# DATASET GENERATOR
# ─────────────────────────────────────────────

@app.post("/dataset/generate", response_model=DatasetGenerateResponse, tags=["Dataset"])
async def dataset_generate():
    """
    Trigger synthetic dataset generation.
    Calls dataset_gen.py (Steve's module) if available.
    """
    if not _DATASET_GEN_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="dataset_gen.py not found. Steve needs to move generate_dataset.py here.",
        )

    try:
        files_created, count = generate_dataset()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Dataset generation failed: {exc}")

    return {
        "message": "Dataset generated successfully",
        "files_created": files_created,
        "invoice_count": count,
    }
