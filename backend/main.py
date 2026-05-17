"""
main.py — FastAPI application. Clean, fully wired.
Pipeline: llm_rule_parser → xslt_templates → xslt_executor
CRITICAL: All CPU-bound operations run off event loop via run_in_threadpool
"""

import json
import os
import re
from typing import List, Optional
from datetime import datetime, timezone
import asyncio
import logging
from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError, ProgrammingError

from orm_models import (
    get_db, init_db, Rule, Invoice,
    ValidationResult as ValidationResultORM,
    ValidationLogic,
    FileValidationReport,
)
from schemas import (
    ValidateRequest,
    ValidateBatchRequest,
    SaveRuleRequest,
    ParseRuleRequest,
    BatchEvaluateRequest,
    ValidateWorkspaceRequest,
    ValidationResult as ValidationResultSchema,
    BatchValidationResponse,
    BatchSummary,
    SavedRuleResponse,
    ParseRuleResponse,
    InvoiceResponse,
    DashboardStats,
    HealthResponse,
    UpdateRuleRequest,
    UpdateValidationLogicRequest,
)
from evaluator import evaluate_one, evaluate_batch
from llm_rule_parser import parse_rule_and_build_xslt
from xslt_executor import execute_workspace_xslt
from xml_reader import parse_invoice_xml, extract_xml_tags

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


_INVOICE_ID_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")
_PDF_FILENAME_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")
_INVOICE_ID_XML_RE = re.compile(r"<invoice_id>\s*([^<\s][^<]*)\s*</invoice_id>", re.IGNORECASE)


def _safe_invoice_identifier(raw_value: Optional[str], fallback_invoice_id: int) -> str:
    value = (raw_value or "").strip()
    value = _INVOICE_ID_SANITIZER.sub("-", value).strip("-")
    if not value:
        return f"INV-{fallback_invoice_id}"
    return value[:64]


def _extract_invoice_identifier_from_xml(xml_content: Optional[str], fallback_invoice_id: int) -> str:
    if not xml_content:
        return f"INV-{fallback_invoice_id}"
    match = _INVOICE_ID_XML_RE.search(xml_content)
    if not match:
        return f"INV-{fallback_invoice_id}"
    return _safe_invoice_identifier(match.group(1), fallback_invoice_id)


def _overall_status(total: int, passed: int, failed: int, errors: int) -> str:
    if total <= 0:
        return "PARTIAL"
    if failed > 0:
        return "FAIL"
    if passed == total and errors == 0:
        return "PASS"
    return "PARTIAL"


def _safe_text(value: Optional[str], max_len: int = 300) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", str(value)).strip()
    return cleaned[:max_len]


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_simple_pdf(lines: List[str]) -> bytes:
    content_lines = [
        "BT",
        "/F1 10 Tf",
        "40 800 Td",
        "12 TL",
    ]
    for idx, line in enumerate(lines):
        if idx == 0:
            content_lines.append(f"({_pdf_escape(line)}) Tj")
        else:
            content_lines.append(f"T* ({_pdf_escape(line)}) Tj")
    content_lines.append("ET")
    content = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
    )
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(
        b"5 0 obj << /Length " + str(len(content)).encode("ascii") + b" >> stream\n" + content + b"\nendstream endobj\n"
    )

    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(output.tell())
        output.write(obj)

    xref_start = output.tell()
    output.write(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        output.write(f"{off:010d} 00000 n \n".encode("ascii"))
    output.write(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("ascii")
    )
    return output.getvalue()


class LowLevelPDFBuilder:
    def __init__(self):
        self.pages_content = []
        self.current_stream = []
        self.y = 780
        self.margin_left = 40
        self.margin_right = 555
        self.line_height = 13

    def new_page(self):
        if self.current_stream:
            self.current_stream.append("ET")
            self.pages_content.append("\n".join(self.current_stream).encode("latin-1", errors="replace"))
        self.current_stream = [
            "BT",
            "/F1 9 Tf",
            "12 TL",
        ]
        self.y = 780

    def draw_rect(self, x, y, w, h, r, g, b, stroke=False, fill=True):
        self.current_stream.append("ET")
        self.current_stream.append(f"{r} {g} {b} rg")
        if stroke:
            self.current_stream.append("0.5 0.5 0.5 RG")
            self.current_stream.append("0.5 w")
        self.current_stream.append(f"{x} {y} {w} {h} re")
        if fill and stroke:
            self.current_stream.append("B")
        elif fill:
            self.current_stream.append("f")
        else:
            self.current_stream.append("S")
        self.current_stream.append("BT /F1 9 Tf 12 TL")

    def draw_line(self, x1, y1, x2, y2, r=0.7, g=0.7, b=0.7):
        self.current_stream.append("ET")
        self.current_stream.append(f"{r} {g} {b} RG")
        self.current_stream.append("0.5 w")
        self.current_stream.append(f"{x1} {y1} m {x2} {y2} l S")
        self.current_stream.append("BT /F1 9 Tf 12 TL")

    def draw_text(self, text, x, y, size=9, bold=False, color=(0.1, 0.1, 0.1)):
        escaped = _pdf_escape(text)
        font_ref = "/F2" if bold else "/F1"
        self.current_stream.append(f"ET BT {font_ref} {size} Tf {color[0]} {color[1]} {color[2]} rg 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET BT /F1 9 Tf 12 TL")

    def wrap_text(self, text, max_width, size=9):
        words = str(text).split(" ")
        lines = []
        current_line = []
        current_width = 0
        char_width = size * 0.50
        for word in words:
            if "\n" in word:
                parts = word.split("\n")
            else:
                parts = [word]
            
            for part_idx, part in enumerate(parts):
                if part_idx > 0 and current_line:
                    lines.append(" ".join(current_line))
                    current_line = []
                    current_width = 0
                
                word_width = len(part) * char_width
                if current_width + word_width > max_width and current_line:
                    lines.append(" ".join(current_line))
                    current_line = [part]
                    current_width = word_width
                else:
                    current_line.append(part)
                    current_width += word_width + (char_width * 0.5)
                    
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def build(self) -> bytes:
        if self.current_stream:
            self.current_stream.append("ET")
            self.pages_content.append("\n".join(self.current_stream).encode("latin-1", errors="replace"))

        objects = []
        num_pages = len(self.pages_content)
        page_object_ids = []
        content_object_ids = []
        
        current_id = 5
        for i in range(num_pages):
            page_object_ids.append(current_id)
            content_object_ids.append(current_id + 1)
            current_id += 2
            
        objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
        
        kids_str = " ".join([f"{pid} 0 R" for pid in page_object_ids])
        objects.append(f"2 0 obj << /Type /Pages /Count {num_pages} /Kids [{kids_str}] >> endobj\n".encode("ascii"))
        
        objects.append(b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
        objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n")
        
        for i in range(num_pages):
            pid = page_object_ids[i]
            cid = content_object_ids[i]
            content_bytes = self.pages_content[i]
            
            page_str = (
                f"{pid} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {cid} 0 R >> endobj\n"
            )
            objects.append(page_str.encode("ascii"))
            
            objects.append(
                f"{cid} 0 obj << /Length {len(content_bytes)} >> stream\n".encode("ascii") +
                content_bytes +
                b"\nendstream endobj\n"
            )
            
        output = BytesIO()
        output.write(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(output.tell())
            output.write(obj)

        xref_start = output.tell()
        output.write(f"xref\n0 {len(offsets)}\n".encode("ascii"))
        output.write(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            output.write(f"{off:010d} 00000 n \n".encode("ascii"))
        output.write(
            f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("ascii")
        )
        return output.getvalue()


def _build_beautiful_report_pdf(details: dict) -> bytes:
    builder = LowLevelPDFBuilder()
    builder.new_page()

    # --- Title Header ---
    builder.draw_rect(40, 780, 515, 30, 0.05, 0.1, 0.25)
    builder.draw_text("INVOICE VALIDATION REPORT", 50, 790, size=12, bold=True, color=(1, 1, 1))

    # --- Summary Box ---
    builder.draw_rect(40, 700, 515, 70, 0.96, 0.97, 0.99, stroke=True)
    
    builder.draw_text("Invoice ID:", 55, 750, bold=True)
    builder.draw_text(details['invoice_identifier'], 130, 750)

    builder.draw_text("Generated At:", 55, 735, bold=True)
    gen_time = details.get('processed_at') or details.get('uploaded_at') or datetime.now(timezone.utc).isoformat()
    builder.draw_text(gen_time, 130, 735)

    builder.draw_text("Checks Run:", 55, 720, bold=True)
    summary_str = f"Total: {details['summary']['total']}  |  Passed: {details['summary']['passed']}  |  Failed: {details['summary']['failed']}  |  Errors: {details['summary']['errors']}"
    builder.draw_text(summary_str, 130, 720)

    status = details['overall_status']
    if status == "PASS":
        builder.draw_rect(440, 720, 100, 25, 0.85, 0.95, 0.88, fill=True)
        builder.draw_text("STATUS: PASS", 455, 728, bold=True, color=(0.1, 0.45, 0.2))
    elif status == "FAIL":
        builder.draw_rect(440, 720, 100, 25, 0.98, 0.88, 0.88, fill=True)
        builder.draw_text("STATUS: FAIL", 455, 728, bold=True, color=(0.7, 0.1, 0.1))
    else:
        builder.draw_rect(440, 720, 100, 25, 0.98, 0.95, 0.85, fill=True)
        builder.draw_text("STATUS: WARNING", 445, 728, bold=True, color=(0.6, 0.4, 0.1))

    def draw_table_headers(y_coord):
        builder.draw_rect(40, y_coord - 18, 515, 18, 0.1, 0.15, 0.3)
        builder.draw_text("Rule Description", 45, y_coord - 12, bold=True, color=(1, 1, 1))
        builder.draw_text("Status", 295, y_coord - 12, bold=True, color=(1, 1, 1))
        builder.draw_text("Message", 365, y_coord - 12, bold=True, color=(1, 1, 1))
        return y_coord - 18

    y = 670
    y = draw_table_headers(y)

    for item in details["checklist"]:
        rule_text = item.get("rule_text", "")
        status = item.get("status", "FAIL")
        message = item.get("message", "") or "-"

        rule_lines = builder.wrap_text(rule_text, 240, size=9)
        message_lines = builder.wrap_text(message, 180, size=9)

        line_count = max(len(rule_lines), len(message_lines))
        row_height = line_count * 12 + 12

        if y - row_height < 50:
            builder.new_page()
            y = draw_table_headers(780)

        is_pass = status == "PASS"
        if is_pass:
            builder.draw_rect(40, y - row_height, 515, row_height, 0.96, 0.99, 0.97, fill=True)
        else:
            builder.draw_rect(40, y - row_height, 515, row_height, 0.99, 0.96, 0.96, fill=True)

        for idx, line in enumerate(rule_lines):
            builder.draw_text(line, 45, y - 13 - (idx * 12), color=(0.15, 0.15, 0.15))

        badge_y = y - 16
        if is_pass:
            builder.draw_rect(295, badge_y, 55, 12, 0.8, 0.92, 0.85)
            builder.draw_text("PASS", 310, badge_y + 3, bold=True, color=(0.1, 0.45, 0.2), size=7)
        else:
            builder.draw_rect(295, badge_y, 55, 12, 0.95, 0.82, 0.82)
            builder.draw_text("FAIL", 312, badge_y + 3, bold=True, color=(0.75, 0.1, 0.1), size=7)

        for idx, line in enumerate(message_lines):
            builder.draw_text(line, 365, y - 13 - (idx * 12), color=(0.3, 0.3, 0.3))

        builder.draw_line(40, y - row_height, 555, y - row_height, r=0.85, g=0.85, b=0.85)

        y -= row_height

    if y - 40 < 50:
        builder.new_page()
        y = 780

    y -= 25
    builder.draw_text("XSLT/XPath References", 40, y, bold=True, size=11, color=(0.1, 0.15, 0.3))
    builder.draw_line(40, y - 4, 555, y - 4, r=0.7, g=0.7, b=0.7)
    y -= 15

    for section_name in ("xpath", "xslt", "python"):
        refs = details["references"].get(section_name, [])
        if not refs:
            continue
        
        if y - 20 < 50:
            builder.new_page()
            y = 780

        builder.draw_text(f"{section_name.upper()} Logic Templates:", 40, y, bold=True, size=9, color=(0.2, 0.2, 0.2))
        y -= 12

        for ref in refs:
            ref_lines = builder.wrap_text(ref, 500, size=7)
            block_height = len(ref_lines) * 9 + 8

            if y - block_height < 50:
                builder.new_page()
                y = 780

            builder.draw_rect(40, y - block_height, 515, block_height, 0.97, 0.97, 0.98, stroke=True)

            for idx, line in enumerate(ref_lines):
                builder.draw_text(line, 45, y - 7 - (idx * 9), size=7, color=(0.2, 0.4, 0.3))

            y -= block_height + 8

    return builder.build()


def _is_missing_schema_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "no such table" in msg
        or "relation" in msg and "does not exist" in msg
        or "undefinedtable" in msg
    )

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


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

@app.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get system-wide statistics for dashboard."""
    try:
        # Count rules
        rules_result = await db.execute(select(func.count(Rule.id)).where(Rule.is_active == True))
        total_rules = rules_result.scalar() or 0
        
        # Count invoices
        invoices_result = await db.execute(select(func.count(Invoice.id)))
        total_invoices = invoices_result.scalar() or 0
        
        # Count validations
        validations_result = await db.execute(select(func.count(ValidationResultORM.id)))
        total_validations = validations_result.scalar() or 0
        
        # Count passed/failed
        passed_result = await db.execute(select(func.count(ValidationResultORM.id)).where(ValidationResultORM.status == "PASS"))
        passed_count = passed_result.scalar() or 0
        
        failed_result = await db.execute(select(func.count(ValidationResultORM.id)).where(ValidationResultORM.status == "FAIL"))
        failed_count = failed_result.scalar() or 0
        
        # Calculate pass rate
        pass_rate = (passed_count / total_validations * 100) if total_validations > 0 else 0
        
        return {
            "total_rules": total_rules,
            "total_invoices": total_invoices,
            "total_validations": total_validations,
            "passed_validations": passed_count,
            "failed_validations": failed_count,
            "pass_rate": round(pass_rate, 1),
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


# ─── Parse Rule (non-saving) ──────────────────────────────────────────────────

from tag_registry import resolve_tag, register_resolved_tag, CANONICAL_FIELDS

def extract_field_tokens(rule_text: str) -> list[str]:
    """
    Extract candidate field name tokens from rule text.
    Looks for CamelCase words and known XML-style tokens.
    """
    import re
    # match CamelCase or snake_case words that look like field names
    return re.findall(r'\b[A-Z][a-zA-Z]+|[a-z]+_[a-z_]+\b', rule_text)


def generate_skip_xslt(description: str) -> str:
    safe = description.replace("<", "&lt;").replace(">", "&gt;")
    return f"""<status>UNSUPPORTED</status>
<message>Field not recognised: {safe}</message>
<suggestion>Use one of: tax_amount, taxable_amount, payable_amount,
invoice_id, seller_name, buyer_name, issue_date, currency_code,
tax_category, tax_exemption_reason, buyer_vat, purchase_order</suggestion>
<field></field>"""


@app.post("/parse-rule", response_model=ParseRuleResponse)
async def parse_rule(body: ParseRuleRequest):
    """Parse a natural language rule without saving it to database."""
    rule_text = body.rule_text.strip()

    if not rule_text:
        raise HTTPException(status_code=422, detail="Rule text cannot be empty.")

    # Step 1 — extract any XML tag tokens from the rule text
    # (tags are words that don't match canonical fields exactly)
    tokens = extract_field_tokens(rule_text)
    normalized_rule = rule_text
    resolution_warnings = []

    for token in tokens:
        if token in CANONICAL_FIELDS:
            continue  # already canonical, skip

        canonical, confidence, warnings = resolve_tag(token)
        resolution_warnings.extend(warnings)

        if canonical:
            # replace the raw token in the rule text before sending to LLM
            normalized_rule = normalized_rule.replace(token, canonical)
            if confidence < 1.0:
                resolution_warnings.append(
                    f"'{token}' auto-mapped to '{canonical}' "
                    f"(confidence {confidence}). Please verify."
                )
        # else: unknown — let LLM handle it with context

    # Step 2 — send normalized rule to LLM
    try:
        # Run CPU-bound LLM parsing off the event loop with timeout protection
        try:
            result = await asyncio.wait_for(
                run_in_threadpool(parse_rule_and_build_xslt, normalized_rule),
                timeout=PARSE_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Rule parsing timeout (30s limit)")

        llm_result = result["structured"]
        xslt_str   = result["xslt"]
    except Exception as e:
        # NEVER return 500 for a bad rule — return structured unsupported
        unsupported_struct = {
            "rule_type": "unsupported",
            "field": None,
            "confidence": 0.0,
            "description": rule_text,
            "warnings": [
                f"LLM parsing failed: {str(e)}",
                "Please rephrase the rule using supported fields.",
            ],
        }
        return {
            "rule_text": rule_text,
            "parsed_rule": unsupported_struct,
            "xslt": generate_skip_xslt(rule_text),
            "xpath": None,
            "python_logic": None,
            **unsupported_struct
        }

    # Step 3 — if LLM resolved an unknown tag, register it
    if llm_result.get("rule_type") != "unsupported":
        for token in tokens:
            resolved_field = llm_result.get("field")
            if resolved_field and token not in CANONICAL_FIELDS:
                register_resolved_tag(token, resolved_field)

    # Step 4 — merge registry warnings into LLM result
    llm_result.setdefault("warnings", [])
    llm_result["warnings"] = resolution_warnings + llm_result["warnings"]

    # Return structure matching ParseRuleResponse and user requirements
    return {
        "rule_text": body.rule_text,
        "parsed_rule": llm_result,
        "xslt": xslt_str,
        "xpath": llm_result.get("xpath") or llm_result.get("xpath_logic"),
        "python_logic": llm_result.get("python_logic"),
        **llm_result
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
            field=structured.get("field"),
            operation=structured.get("operation"),
            severity=body.severity,
            xslt_logic=xslt_str,
            xpath_logic=structured.get("xpath"),
            python_logic=structured.get("python_logic"),
            is_active=True,
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


@app.get("/rules")
async def list_rules(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Rule).order_by(Rule.created_at.desc()))
        rules  = result.scalars().all()
        return [
            {
                "id":          r.id,
                "rule_text":   r.rule_text,
                "parsed_json": json.loads(r.parsed_json) if r.parsed_json else {},
                "severity":    r.severity,
                "created_at":  str(r.created_at),
            }
            for r in rules
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.put("/rules/{rule_id}", response_model=SavedRuleResponse)
async def update_rule(rule_id: int, body: UpdateRuleRequest, db: AsyncSession = Depends(get_db)):
    """Update an existing rule text/severity and regenerate parsed logic."""
    if body.rule_text is not None:
        _validate_rule_text(body.rule_text)
    try:
        result = await db.execute(select(Rule).where(Rule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        if body.rule_text is not None and body.rule_text != rule.rule_text:
            parsed = await asyncio.wait_for(
                run_in_threadpool(parse_rule_and_build_xslt, body.rule_text),
                timeout=PARSE_TIMEOUT,
            )
            structured = parsed["structured"]
            xslt_str = parsed["xslt"]
            stored = {**structured, "xslt": xslt_str}
            rule.rule_text = body.rule_text
            rule.parsed_json = json.dumps(stored)
            rule.rule_type = structured.get("rule_type")
            rule.field = structured.get("field")
            rule.operation = structured.get("operation")
            rule.xpath_logic = structured.get("xpath")
            rule.xslt_logic = xslt_str
            rule.python_logic = structured.get("python_logic")

        if body.severity is not None:
            rule.severity = body.severity

        await db.commit()
        await db.refresh(rule)
        return {
            "id": rule.id,
            "rule_text": rule.rule_text,
            "parsed_json": json.loads(rule.parsed_json) if rule.parsed_json else {},
            "severity": rule.severity,
            "created_at": rule.created_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Rule update failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Rule update failed")


@app.get("/rules/{rule_id}/logic")
async def get_rule_logic(rule_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Rule).where(Rule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        return {
            "rule_id": rule.id,
            "xpath_logic": rule.xpath_logic,
            "xslt_logic": rule.xslt_logic,
            "python_logic": rule.python_logic,
            "updated_at": rule.updated_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get logic failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to fetch logic")


@app.put("/rules/{rule_id}/logic")
async def update_rule_logic(rule_id: int, body: UpdateValidationLogicRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Rule).where(Rule.id == rule_id))
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        if body.xpath_logic is not None:
            rule.xpath_logic = body.xpath_logic
        if body.xslt_logic is not None:
            rule.xslt_logic = body.xslt_logic
        if body.python_logic is not None:
            rule.python_logic = body.python_logic

        logic_record = ValidationLogic(
            rule_id=rule.id,
            xpath_logic=rule.xpath_logic,
            xslt_logic=rule.xslt_logic,
            python_logic=rule.python_logic,
        )
        db.add(logic_record)
        await db.commit()
        await db.refresh(rule)

        return {
            "rule_id": rule.id,
            "xpath_logic": rule.xpath_logic,
            "xslt_logic": rule.xslt_logic,
            "python_logic": rule.python_logic,
            "updated_at": rule.updated_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Update logic failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to update logic")


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

    # Guard: reject plaintext/badly malformed XML before hitting the executor
    try:
        from lxml import etree as _etree
        _etree.fromstring(body.xml_content.encode())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML format: {str(e)[:80]}")
    
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

        # Store invoice with extracted metadata
        new_invoice = Invoice(
            filename="inline_upload",
            xml_content=body.xml_content,
        )
        db.add(new_invoice)
        await db.commit()
        await db.refresh(new_invoice)

        # Store results with full schema
        for r in out["results"]:
            vr = ValidationResultORM(
                invoice_id=new_invoice.id,
                rule_id=r.get("rule_id"),
                rule_text=r.get("rule_text", ""),
                rule_type=r.get("rule_type"),
                rule_severity=r.get("severity", "high"),
                status=r.get("status", "ERROR"),
                message=r.get("message", ""),
                field_checked=r.get("field"),
                execution_time_ms=r.get("execution_time_ms"),
                xslt_result=r.get("xslt_result"),
            )
            db.add(vr)
        
        # Update invoice stats
        new_invoice.total_rules_tested = len(out["results"])
        new_invoice.passed_count = len([r for r in out["results"] if r.get("status") == "PASS"])
        new_invoice.failed_count = len([r for r in out["results"] if r.get("status") == "FAIL"])
        new_invoice.processed_at = datetime.utcnow()
        
        await db.commit()

        return out
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Batch validation failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Batch validation failed")


@app.post("/validate/workspace")
async def validate_workspace(body: ValidateWorkspaceRequest):
    """Validate one XML invoice against one selected XSLT workspace file."""

    if len(body.xml_content) > MAX_XML_SIZE:
        raise HTTPException(status_code=413, detail=f"XML too large (max {MAX_XML_SIZE} bytes)")

    if len(body.xslt_content) > MAX_XML_SIZE:
        raise HTTPException(status_code=413, detail=f"XSLT too large (max {MAX_XML_SIZE} bytes)")

    try:
        from lxml import etree as _etree
        _etree.fromstring(body.xml_content.encode())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML format: {str(e)[:80]}")

    try:
        result = await asyncio.wait_for(
            run_in_threadpool(execute_workspace_xslt, body.xslt_content, body.xml_content, body.xslt_name or ""),
            timeout=BATCH_VALIDATION_TIMEOUT,
        )
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"Workspace validation timeout ({BATCH_VALIDATION_TIMEOUT}s limit)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workspace validation failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Workspace validation failed")


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
            file_size=len(content),
            upload_status="uploaded",
        )
        db.add(new_invoice)
        await db.commit()
        await db.refresh(new_invoice)

        return {
            "id":          new_invoice.id,
            "filename":    new_invoice.filename,
            "uploaded_at": new_invoice.uploaded_at.isoformat(),
            "size":        new_invoice.file_size,
            "status":      new_invoice.upload_status,
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
                "size":        i.file_size,
                "status":      i.upload_status,
            }
            for i in invoices
        ]
    except Exception as e:
        logger.error(f"Failed to list invoices: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to list invoices")

@app.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Delete one uploaded invoice and all linked validation data."""
    if invoice_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")
    try:
        invoice = (
            await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        ).scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        report_rows = (
            await db.execute(select(FileValidationReport).where(FileValidationReport.file_id == invoice_id))
        ).scalars().all()
        for report in report_rows:
            await db.delete(report)

        validation_rows = (
            await db.execute(select(ValidationResultORM).where(ValidationResultORM.invoice_id == invoice_id))
        ).scalars().all()
        for row in validation_rows:
            await db.delete(row)

        await db.delete(invoice)
        await db.commit()
        return {"message": "Invoice deleted", "id": invoice_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Invoice delete failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to delete invoice")


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
            vr = ValidationResultORM(
                invoice_id=invoice_id,
                rule_id=r.get("rule_id"),
                rule_text=r.get("rule_text", ""),
                status=r.get("status", "ERROR"),
                message=r.get("message", ""),
                rule_type=r.get("rule_type"),
            )
            db.add(vr)

        passed_count = len([r for r in out["results"] if r.get("status") == "PASS"])
        failed_count = len([r for r in out["results"] if r.get("status") == "FAIL"])
        invoice.total_rules_tested = len(out["results"])
        invoice.passed_count = passed_count
        invoice.failed_count = failed_count
        invoice.upload_status = "validated"
        invoice.processed_at = datetime.utcnow()

        report = FileValidationReport(
            file_id=invoice.id,
            passed_rules=passed_count,
            failed_rules=failed_count,
            summary_json=json.dumps(out.get("summary", {})),
            execution_status="COMPLETED",
        )
        db.add(report)
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
    async def _load_rows():
        invoices = (
            await db.execute(select(Invoice).order_by(Invoice.processed_at.desc(), Invoice.uploaded_at.desc()).limit(200))
        ).scalars().all()
        if not invoices:
            return []

        invoice_ids = [inv.id for inv in invoices]
        all_rows = (
            await db.execute(
                select(ValidationResultORM).where(ValidationResultORM.invoice_id.in_(invoice_ids))
            )
        ).scalars().all()

        rows_by_invoice = {}
        for row in all_rows:
            rows_by_invoice.setdefault(row.invoice_id, []).append(row)

        out = []
        for inv in invoices:
            rows = rows_by_invoice.get(inv.id, [])
            total = len(rows)
            passed = len([r for r in rows if r.status == "PASS"])
            failed = len([r for r in rows if r.status == "FAIL"])
            errors = len([r for r in rows if r.status == "ERROR"])
            invoice_identifier = _extract_invoice_identifier_from_xml(inv.xml_content, inv.id)
            message = "Validation pending"
            first_fail = next((r for r in rows if r.status == "FAIL"), None)
            if first_fail and first_fail.message:
                message = _safe_text(first_fail.message, max_len=180)
            elif total > 0:
                message = f"{passed}/{total} checks passed"

            out.append(
                {
                    "id": inv.id,
                    "invoice_id": inv.id,
                    "invoice_identifier": invoice_identifier,
                    "overall_status": _overall_status(total, passed, failed, errors),
                    "message": message,
                    "validated_at": (inv.processed_at or inv.uploaded_at).isoformat(),
                    "total_rules": total,
                    "passed_rules": passed,
                    "failed_rules": failed,
                    "error_rules": errors,
                    "execution_status": _safe_text(inv.upload_status or "unknown", max_len=40).upper(),
                }
            )
        return out

    try:
        return await _load_rows()
    except (OperationalError, ProgrammingError) as e:
        if _is_missing_schema_error(e):
            logger.warning("Schema missing while listing results; initializing DB and retrying once")
            await init_db()
            return await _load_rows()
        logger.error(f"DB error while listing results: {str(e)[:120]}")
        raise HTTPException(status_code=500, detail="Failed to list results")
    except Exception as e:
        logger.error(f"Failed to list results: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to list results")


@app.get("/results/{invoice_id}")
async def results_for_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """All results for one invoice. Returns 404 if none found."""
    if invoice_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")
    try:
        invoice = (
            await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        ).scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        parsed = parse_invoice_xml(invoice.xml_content or "")
        invoice_identifier = _safe_invoice_identifier(parsed.get("invoice_id"), invoice_id)
        result  = await db.execute(
            select(ValidationResultORM).where(ValidationResultORM.invoice_id == invoice_id)
        )
        results = result.scalars().all()
        if not results:
            raise HTTPException(status_code=404, detail=f"No validation results found for invoice {invoice_id}")
        return [
            {
                "id":         r.id,
                "invoice_id": invoice_id,
                "invoice_identifier": invoice_identifier,
                "rule_id":    r.rule_id,
                "rule_text":  r.rule_text,
                "rule_type":  r.rule_type,
                "status":     r.status,
                "message":    _safe_text(r.message),
                "validated_at": r.validated_at.isoformat(),
                "execution_result": "XSLT_EXECUTED",
            }
            for r in results
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to get results")


@app.get("/reports")
async def list_reports(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(FileValidationReport, Invoice)
            .join(Invoice, FileValidationReport.file_id == Invoice.id)
            .order_by(FileValidationReport.created_at.desc())
            .limit(200)
        )
        rows = result.all()
        return [
            {
                "id": report.id,
                "file_id": report.file_id,
                "file_name": invoice.filename or "unknown",
                "file_size": invoice.file_size,
                "passed_rules": report.passed_rules,
                "failed_rules": report.failed_rules,
                "summary_json": json.loads(report.summary_json) if report.summary_json else {},
                "execution_status": report.execution_status,
                "created_at": report.created_at.isoformat(),
            }
            for report, invoice in rows
        ]
    except Exception as e:
        logger.error(f"Failed to list reports: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to list reports")


@app.get("/reports/{invoice_id}/details")
async def report_details(invoice_id: int, db: AsyncSession = Depends(get_db)):
    if invoice_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")
    try:
        invoice = (
            await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        ).scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=404, detail="Validation report not found")

        parsed = parse_invoice_xml(invoice.xml_content or "")
        invoice_identifier = _safe_invoice_identifier(parsed.get("invoice_id"), invoice_id)

        rows = (
            await db.execute(select(ValidationResultORM).where(ValidationResultORM.invoice_id == invoice_id))
        ).scalars().all()
        total = len(rows)
        passed = len([r for r in rows if r.status == "PASS"])
        failed = len([r for r in rows if r.status == "FAIL"])
        errors = len([r for r in rows if r.status == "ERROR"])

        rule_ids = [r.rule_id for r in rows if r.rule_id is not None]
        rules = []
        if rule_ids:
            rules = (
                await db.execute(select(Rule).where(Rule.id.in_(rule_ids)))
            ).scalars().all()
        rule_by_id = {r.id: r for r in rules}

        checklist = []
        xpath_refs: List[str] = []
        xslt_refs: List[str] = []
        python_refs: List[str] = []
        for r in rows:
            if r.rule_id in rule_by_id:
                rr = rule_by_id[r.rule_id]
                if rr.xpath_logic:
                    xpath_refs.append(_safe_text(rr.xpath_logic, 500))
                if rr.xslt_logic:
                    xslt_refs.append(_safe_text(rr.xslt_logic, 500))
                if rr.python_logic:
                    python_refs.append(_safe_text(rr.python_logic, 500))
            checklist.append(
                {
                    "rule_id": r.rule_id,
                    "rule_text": _safe_text(r.rule_text, 200),
                    "rule_type": r.rule_type,
                    "status": r.status,
                    "message": _safe_text(r.message, 300),
                    "execution_result": "XSLT_EXECUTED",
                    "validated_at": r.validated_at.isoformat(),
                }
            )

        # deterministic unique ordering
        xpath_refs = sorted(set(xpath_refs))
        xslt_refs = sorted(set(xslt_refs))
        python_refs = sorted(set(python_refs))

        return {
            "report_id": invoice.id,
            "invoice_id": invoice.id,
            "invoice_identifier": invoice_identifier,
            "uploaded_at": invoice.uploaded_at.isoformat(),
            "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None,
            "execution_status": _safe_text(invoice.upload_status or "unknown", 40).upper(),
            "overall_status": _overall_status(total, passed, failed, errors),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
            },
            "checklist": checklist,
            "references": {
                "xpath": xpath_refs,
                "xslt": xslt_refs,
                "python": python_refs,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report details: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to fetch report details")


@app.delete("/reports/{invoice_id}")
async def delete_report(invoice_id: int, db: AsyncSession = Depends(get_db)):
    if invoice_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")
    try:
        invoice = (
            await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        ).scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=404, detail="Validation report not found")

        report_rows = (
            await db.execute(select(FileValidationReport).where(FileValidationReport.file_id == invoice_id))
        ).scalars().all()
        for report in report_rows:
            await db.delete(report)

        validation_rows = (
            await db.execute(select(ValidationResultORM).where(ValidationResultORM.invoice_id == invoice_id))
        ).scalars().all()
        if not validation_rows and not report_rows:
            raise HTTPException(status_code=404, detail="Validation report already deleted")
        for row in validation_rows:
            await db.delete(row)

        await db.commit()
        return {"message": "Validation report deleted", "id": invoice_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete report failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to delete validation report")


@app.get("/reports/{invoice_id}/pdf")
async def download_report_pdf(invoice_id: int, db: AsyncSession = Depends(get_db)):
    if invoice_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")
    try:
        details = await report_details(invoice_id, db)
        pdf_bytes = _build_beautiful_report_pdf(details)
        safe_name = _PDF_FILENAME_SANITIZER.sub("-", details["invoice_identifier"]).strip("-") or f"INV-{invoice_id}"
        filename = f"{safe_name}-validation-report.pdf"
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics."""
    try:
        total_rules = (await db.execute(select(func.count(Rule.id)))).scalar() or 0
        total_inv   = (await db.execute(select(func.count(Invoice.id)))).scalar() or 0
        total_val   = (await db.execute(select(func.count(ValidationResultORM.id)))).scalar() or 0
        passed      = (await db.execute(
            select(func.count(ValidationResultORM.id)).where(ValidationResultORM.status == "PASS")
        )).scalar() or 0
        failed      = (await db.execute(
            select(func.count(ValidationResultORM.id)).where(ValidationResultORM.status == "FAIL")
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


@app.post("/upload-sample-xml")
async def upload_sample_xml(file: UploadFile = File(...)):
    """
    Accept an XML file upload, extract all tags deterministically.
    Returns known tags (in registry) and unknown tags separately.
    No LLM used. Pure XML parsing.
    """
    if not file.filename.endswith(".xml"):
        raise HTTPException(status_code=422, detail="Only .xml files are accepted.")

    try:
        content = await file.read()
        xml_string = content.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=422, detail="Could not read file. Ensure it is UTF-8 encoded XML.")

    result = extract_xml_tags(xml_string)

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@app.post("/resolve-tag")
async def resolve_tag_endpoint(body: dict):
    """
    When user confirms what an unknown tag means,
    register it in the session. Body: { raw_tag, canonical_field }
    """
    from tag_registry import TAG_REGISTRY, CANONICAL_FIELDS
    raw_tag = body.get("raw_tag", "").strip()
    canonical = body.get("canonical_field", "").strip()

    if not raw_tag:
        raise HTTPException(status_code=422, detail="raw_tag is required.")
    if canonical and canonical not in CANONICAL_FIELDS:
        raise HTTPException(status_code=422, detail=f"'{canonical}' is not a valid canonical field.")

    TAG_REGISTRY[raw_tag] = canonical if canonical else None
    return {"registered": True, "raw_tag": raw_tag, "canonical_field": canonical}
