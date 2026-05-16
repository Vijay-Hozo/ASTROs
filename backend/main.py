"""
main.py — FastAPI application. Clean, fully wired.
Pipeline: llm_rule_parser → xslt_templates → xslt_executor
CRITICAL: All CPU-bound operations run off event loop via run_in_threadpool
"""

import json
import os
from typing import List, Optional
from datetime import datetime, timezone
import asyncio
import logging

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from orm_models import get_db, init_db, Rule, Invoice, ValidationResult
from schemas import (
    ValidateRequest,
    ValidateBatchRequest,
    SaveRuleRequest,
    BatchEvaluateRequest,
    ValidationResult as ValidationResultSchema,
    BatchValidationResponse,
    BatchSummary,
    SavedRuleResponse,
    InvoiceResponse,
    DashboardStats,
    HealthResponse,
)
from evaluator import evaluate_one, evaluate_batch
from llm_rule_parser import parse_rule_and_build_xslt

# ─── Configuration ────────────────────────────────────────────────────────────

BATCH_VALIDATION_TIMEOUT = 60  # 60 seconds timeout for batch validations
PARSE_TIMEOUT = 30  # 30 seconds timeout for parsing
MAX_XML_SIZE = 1_000_000  # 1MB max XML size
# ─── Logging ──────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)
# ─── Rule text sanity guard ───────────────────────────────────────────────────

_SUSPICIOUS_TOKENS = [
    "' or", "or 1=1", "--", "drop table", "insert into",
    "select *", "<script", "exec(", "union select",
]

def _validate_rule_text(rule_text: str) -> None:
    """
    Lightweight sanity check before sending rule_text to the LLM.
    Raises HTTPException(400) on bad input. Not a security boundary —
    the LLM sanitises output — but prevents junk from reaching the DB.
    """
    text = rule_text.strip()
    if len(text) < 5:
        raise HTTPException(status_code=400, detail="rule_text too short (min 5 chars)")
    if len(text) > 500:
        raise HTTPException(status_code=422, detail="rule_text too long (max 500 chars)")
    lower = text.lower()
    for token in _SUSPICIOUS_TOKENS:
        if token in lower:
            raise HTTPException(status_code=400, detail="rule_text contains disallowed content")

# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PS-3 Natural Language Rule Engine",
    description="Plain English invoice validation rules → XSLT → XML validation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Exception Middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def exception_middleware(request: Request, call_next):
    """
    Global exception handler middleware.
    Prevents stacktrace leakage and sanitizes error responses.
    """
    try:
        return await call_next(request)
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except asyncio.TimeoutError:
        logger.warning(f"Request timeout: {request.url.path}")
        return JSONResponse(
            status_code=504,
            content={"detail": "Request timeout"},
        )
    except Exception as e:
        logger.error(f"Unhandled exception: {type(e).__name__}: {str(e)[:100]}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},  # Don't leak details
        )


@app.on_event("startup")
async def on_startup():
    await init_db()


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    return {
        "status":    "ok",
        "version":   "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Rules CRUD ───────────────────────────────────────────────────────────────

@app.post("/rules", response_model=SavedRuleResponse)
async def create_rule(body: SaveRuleRequest, db: AsyncSession = Depends(get_db)):
    """Save a new English rule — LLM parses it and stores XSLT too."""
    _validate_rule_text(body.rule_text)
    try:
        # Run CPU-bound LLM parsing off the event loop with timeout protection
        try:
            result = await asyncio.wait_for(
                run_in_threadpool(parse_rule_and_build_xslt, body.rule_text),
                timeout=PARSE_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Rule parsing timeout (30s limit)")

        structured = result["structured"]
        xslt_str   = result["xslt"]

        # Store both structured rule AND xslt in parsed_json
        stored = {**structured, "xslt": xslt_str}

        new_rule = Rule(
            rule_text=body.rule_text,
            parsed_json=json.dumps(stored),
            rule_type=structured.get("rule_type"),
            severity=body.severity,
        )
        db.add(new_rule)
        await db.commit()
        await db.refresh(new_rule)

        return {
            "id":          new_rule.id,
            "rule_text":   new_rule.rule_text,
            "parsed_json": stored,
            "severity":    new_rule.severity,
            "created_at":  new_rule.created_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Rule creation failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Rule creation failed")


@app.get("/rules", response_model=List[SavedRuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    """List all saved rules."""
    try:
        result = await db.execute(select(Rule).order_by(Rule.created_at.desc()))
        rules  = result.scalars().all()
        return [
            {
                "id":          r.id,
                "rule_text":   r.rule_text,
                "parsed_json": json.loads(r.parsed_json) if r.parsed_json else {},
                "severity":    r.severity,
                "created_at":  r.created_at.isoformat(),
            }
            for r in rules
        ]
    except Exception as e:
        logger.error(f"Failed to list rules: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to list rules")


@app.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a rule by ID."""
    try:
        result = await db.execute(select(Rule).where(Rule.id == rule_id))
        rule   = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        await db.delete(rule)
        await db.commit()
        return {"message": "Rule deleted", "id": rule_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Delete failed")


# ─── Validate — single rule + single XML ──────────────────────────────────────

@app.post("/validate")
async def validate_single(body: ValidateRequest, db: AsyncSession = Depends(get_db)):
    """Validate one rule against one XML (not saved to DB)."""
    _validate_rule_text(body.rule_text)
    
    # Validate XML size
    if len(body.xml_content) > MAX_XML_SIZE:
        raise HTTPException(status_code=413, detail=f"XML too large (max {MAX_XML_SIZE} bytes)")
    
    # Guard: reject plaintext/badly malformed XML before hitting the executor
    try:
        from lxml import etree as _etree
        _etree.fromstring(body.xml_content.encode())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML format: {str(e)[:80]}")
    
    try:
        # Run evaluation off event loop
        result = await asyncio.wait_for(
            run_in_threadpool(evaluate_one, body.rule_text, body.xml_content),
            timeout=PARSE_TIMEOUT
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Validation timeout (30s limit)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Validation failed")


# ─── Validate — all saved rules against one XML ───────────────────────────────

@app.post("/validate/all-rules")
async def validate_all_rules(body: BatchEvaluateRequest, db: AsyncSession = Depends(get_db)):
    """Run all saved rules against a single XML invoice. Stores results."""
    
    # Validate XML size
    if len(body.xml_content) > MAX_XML_SIZE:
        raise HTTPException(status_code=413, detail=f"XML too large (max {MAX_XML_SIZE} bytes)")
    
    # Fetch all rules
    try:
        result = await db.execute(select(Rule).order_by(Rule.id))
        rules  = result.scalars().all()

        if not rules:
            raise HTTPException(status_code=404, detail="No rules saved yet. Add rules first.")

        rule_list = [
            {
                "id":          r.id,
                "rule_text":   r.rule_text,
                "parsed_json": r.parsed_json,
            }
            for r in rules
        ]

        # Run batch evaluation off event loop with timeout
        try:
            out = await asyncio.wait_for(
                run_in_threadpool(evaluate_batch, rule_list, body.xml_content),
                timeout=BATCH_VALIDATION_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail=f"Batch validation timeout ({BATCH_VALIDATION_TIMEOUT}s limit)")

        # Store invoice
        new_invoice = Invoice(
            filename="inline_upload",
            xml_content=body.xml_content,
        )
        db.add(new_invoice)
        await db.commit()
        await db.refresh(new_invoice)

        # Store results
        for r in out["results"]:
            vr = ValidationResult(
                invoice_id=new_invoice.id,
                rule_id=r.get("rule_id"),
                rule_text=r.get("rule_text", ""),
                status=r.get("status", "ERROR"),
                message=r.get("message", ""),
                rule_type=r.get("rule_type"),
            )
            db.add(vr)
        await db.commit()

        return out
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Batch validation failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Batch validation failed")


# ─── Upload XML file ──────────────────────────────────────────────────────────

@app.post("/invoices/upload", response_model=InvoiceResponse)
async def upload_invoice(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload an XML invoice file — stores it, returns invoice ID."""
    try:
        if not file.filename.endswith(".xml"):
            raise HTTPException(status_code=400, detail="Only .xml files accepted")

        content = await file.read()
        if len(content) > MAX_XML_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large (max {MAX_XML_SIZE} bytes)")

        xml_str = content.decode("utf-8", errors="replace")

        # Validate XML
        try:
            from lxml import etree as _etree
            _etree.fromstring(xml_str.encode())
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid XML file: {str(e)[:80]}")

        new_invoice = Invoice(
            filename=file.filename,
            xml_content=xml_str,
        )
        db.add(new_invoice)
        await db.commit()
        await db.refresh(new_invoice)

        return {
            "id":          new_invoice.id,
            "filename":    new_invoice.filename,
            "uploaded_at": new_invoice.uploaded_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Upload failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Upload failed")


@app.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(db: AsyncSession = Depends(get_db)):
    """List all uploaded invoices."""
    try:
        result   = await db.execute(select(Invoice).order_by(Invoice.uploaded_at.desc()))
        invoices = result.scalars().all()
        return [
            {
                "id":          i.id,
                "filename":    i.filename or "unknown",
                "uploaded_at": i.uploaded_at.isoformat(),
            }
            for i in invoices
        ]
    except Exception as e:
        logger.error(f"Failed to list invoices: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to list invoices")


# ─── Validate stored invoice against all saved rules ──────────────────────────

@app.post("/invoices/{invoice_id}/validate")
async def validate_stored_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Run all saved rules against a stored invoice."""
    try:
        inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice    = inv_result.scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        rule_result = await db.execute(select(Rule).order_by(Rule.id))
        rules       = rule_result.scalars().all()
        if not rules:
            raise HTTPException(status_code=404, detail="No rules saved yet")

        rule_list = [
            {"id": r.id, "rule_text": r.rule_text, "parsed_json": r.parsed_json}
            for r in rules
        ]

        # Run batch evaluation off event loop with timeout
        try:
            out = await asyncio.wait_for(
                run_in_threadpool(evaluate_batch, rule_list, invoice.xml_content),
                timeout=BATCH_VALIDATION_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail=f"Validation timeout ({BATCH_VALIDATION_TIMEOUT}s limit)")

        # Store results
        for r in out["results"]:
            vr = ValidationResult(
                invoice_id=invoice_id,
                rule_id=r.get("rule_id"),
                rule_text=r.get("rule_text", ""),
                status=r.get("status", "ERROR"),
                message=r.get("message", ""),
                rule_type=r.get("rule_type"),
            )
            db.add(vr)
        await db.commit()

        return out
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Validation failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Validation failed")


# ─── Results ──────────────────────────────────────────────────────────────────

@app.get("/results")
async def list_results(db: AsyncSession = Depends(get_db)):
    """All validation results."""
    try:
        result  = await db.execute(
            select(ValidationResult).order_by(ValidationResult.validated_at.desc()).limit(200)
        )
        results = result.scalars().all()
        return [
            {
                "id":           r.id,
                "invoice_id":   r.invoice_id,
                "rule_id":      r.rule_id,
                "rule_text":    r.rule_text,
                "rule_type":    r.rule_type,
                "status":       r.status,
                "message":      r.message,
                "validated_at": r.validated_at.isoformat(),
            }
            for r in results
        ]
    except Exception as e:
        logger.error(f"Failed to list results: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to list results")


@app.get("/results/{invoice_id}")
async def results_for_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """All results for one invoice. Returns 404 if none found."""
    try:
        result  = await db.execute(
            select(ValidationResult).where(ValidationResult.invoice_id == invoice_id)
        )
        results = result.scalars().all()
        if not results:
            raise HTTPException(status_code=404, detail=f"No validation results found for invoice {invoice_id}")
        return [
            {
                "id":         r.id,
                "rule_text":  r.rule_text,
                "rule_type":  r.rule_type,
                "status":     r.status,
                "message":    r.message,
            }
            for r in results
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to get results")


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics."""
    try:
        total_rules = (await db.execute(select(func.count(Rule.id)))).scalar() or 0
        total_inv   = (await db.execute(select(func.count(Invoice.id)))).scalar() or 0
        total_val   = (await db.execute(select(func.count(ValidationResult.id)))).scalar() or 0
        passed      = (await db.execute(
            select(func.count(ValidationResult.id)).where(ValidationResult.status == "PASS")
        )).scalar() or 0
        failed      = (await db.execute(
            select(func.count(ValidationResult.id)).where(ValidationResult.status == "FAIL")
        )).scalar() or 0

        pass_rate = round((passed / total_val * 100), 1) if total_val > 0 else 0.0

        return {
            "total_rules":       total_rules,
            "total_invoices":    total_inv,
            "total_validations": total_val,
            "total_passed":      passed,
            "total_failed":      failed,
            "pass_rate":         pass_rate,
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to get stats")
