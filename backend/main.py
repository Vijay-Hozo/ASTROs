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
import zipfile
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
    Sample,
    XsltSampleLink,
    ActiveWorkspace,
    XsltFile,
)
from schemas import (
    ValidateRequest,
    ValidateWorkspaceRequest,
    UpdateWorkspaceRequest,
    SaveRuleRequest,
    ParseRuleRequest,
    BatchEvaluateRequest,
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

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", os.getenv("SUPABASE_URL", "https://yppdggvilalihoeccznc.supabase.co")).strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlwcGRnZ3ZpbGFsaWhvZWNjem5jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg5ODkzNjcsImV4cCI6MjA5NDU2NTM2N30.u_jiDzvWDts_TZrKGyxvD70nUyBe9iL5ClqeQX3t5RI"))).strip()

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ─── Logging ──────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

async def ensure_defaults():
    try:
        # ── CHECK SAMPLE ──────────────────────────
        sample_res = supabase.table("samples").select("id, filename, status").limit(1).execute()

        if not sample_res.data:
            default_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice>
  <invoice_id>DEFAULT-001</invoice_id>
  <issue_date>2026-01-01</issue_date>
  <seller_name>Default Seller</seller_name>
  <buyer_name>Default Buyer</buyer_name>
  <currency_code>INR</currency_code>
  <taxable_amount>0.00</taxable_amount>
  <tax_amount>0.00</tax_amount>
  <payable_amount>0.00</payable_amount>
  <tax_category>S</tax_category>
  <buyer_vat>00DEFAULT0000A1Z1</buyer_vat>
  <purchase_order>PO-DEFAULT-0001</purchase_order>
  <line_items/>
</Invoice>"""

            sample_insert = supabase.table("samples").insert({
                "filename": "default.xml",
                "xml_content": default_xml,
                "status": "default",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "extracted_tags": [
                    "invoice_id", "issue_date", "seller_name", "buyer_name",
                    "currency_code", "taxable_amount", "tax_amount",
                    "payable_amount", "tax_category", "buyer_vat",
                    "purchase_order", "line_items"
                ]
            }).execute()
            sample_id = sample_insert.data[0]["id"]
        else:
            sample_id = sample_res.data[0]["id"]

        # ── CHECK XSLT FILE ───────────────────────
        xslt_res = supabase.table("xslt_files").select("id, filename, status").limit(1).execute()

        if not xslt_res.data:
            default_xslt = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <!-- Default India Rules XSLT -->
    <!-- Rules will be appended here -->
  </xsl:template>
</xsl:stylesheet>"""

            import uuid
            xslt_insert = supabase.table("xslt_files").insert({
                "id": str(uuid.uuid4()),
                "filename": "india_rules.xslt",
                "description": "Default India validation rules",
                "xslt_content": default_xslt,
                "rules_count": 0,
                "status": "default",
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            xslt_id = xslt_insert.data[0]["id"]
        else:
            xslt_id = xslt_res.data[0]["id"]

        # ── LINK SAMPLE + XSLT ────────────────────
        link_res = supabase.table("xslt_sample_links").select("id").eq("sample_id", sample_id).eq("xslt_id", xslt_id).limit(1).execute()

        if not link_res.data:
            supabase.table("xslt_sample_links").insert({
                "sample_id": sample_id,
                "xslt_id": xslt_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()

        # ── SET ACTIVE WORKSPACE ──────────────────
        workspace_res = supabase.table("active_workspace").select("id").limit(1).execute()

        if not workspace_res.data:
            supabase.table("active_workspace").insert({
                "sample_id": sample_id,
                "xslt_id": xslt_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
    except Exception as e:
        logger.error(f"ensure_defaults failed: {e}")
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
    builder.draw_rect(40, 685, 515, 85, 0.96, 0.97, 0.99, stroke=True)
    
    builder.draw_text("Invoice ID:", 55, 750, bold=True)
    builder.draw_text(details['invoice_identifier'], 130, 750)

    builder.draw_text("XSLT File:", 55, 735, bold=True)
    builder.draw_text(details.get('xslt_filename') or "N/A", 130, 735)

    builder.draw_text("Generated At:", 55, 720, bold=True)
    gen_time = details.get('processed_at') or details.get('uploaded_at') or datetime.now(timezone.utc).isoformat()
    builder.draw_text(gen_time, 130, 720)

    builder.draw_text("Checks Run:", 55, 705, bold=True)
    summary_str = f"Total: {details['summary']['total']}  |  Passed: {details['summary']['passed']}  |  Failed: {details['summary']['failed']}  |  Errors: {details['summary']['errors']}"
    builder.draw_text(summary_str, 130, 705)

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


# ─── Exception Handlers ───────────────────────────────────────────────────────

@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError):
    logger.warning(f"Request timeout: {request.url.path}")
    return JSONResponse(
        status_code=504,
        content={"detail": "Request timeout"},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)[:100]}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},  # Don't leak details
    )


@app.on_event("startup")
async def on_startup():
    await init_db()
    await ensure_defaults()


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
            xslt_id=body.xslt_id,
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
        try:
            ws_data = await get_active_workspace()
            new_invoice.xslt_filename = ws_data.get("xslt_filename")
        except Exception as e:
            logger.warning(f"Failed to attach xslt_filename to inline invoice: {e}")
        
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
        try:
            ws_data = await get_active_workspace()
            invoice.xslt_filename = ws_data.get("xslt_filename")
        except Exception as e:
            logger.warning(f"Failed to attach xslt_filename to invoice: {e}")


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
                    "xslt_filename": inv.xslt_filename,
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
            "xslt_filename": invoice.xslt_filename,
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
            # Idempotent delete — already gone, not an error
            return {"message": "already deleted", "id": invoice_id}

        # Manually delete related reports
        report_rows = (
            await db.execute(select(FileValidationReport).where(FileValidationReport.file_id == invoice_id))
        ).scalars().all()
        for report in report_rows:
            await db.delete(report)

        # Manually delete related validation results
        validation_rows = (
            await db.execute(select(ValidationResultORM).where(ValidationResultORM.invoice_id == invoice_id))
        ).scalars().all()
        for row in validation_rows:
            await db.delete(row)

        # Delete the invoice itself
        await db.delete(invoice)
        await db.commit()
        return {"message": "deleted", "id": invoice_id}
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


def _generate_single_pdf(details: dict) -> bytes:
    output = BytesIO()
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed on server")

    doc = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("INVOICE VALIDATION REPORT", styles['Title']))
    elements.append(Spacer(1, 12))

    xslt_filename = details.get('xslt_filename') or 'N/A'
    elements.append(Paragraph(f"<b>XSLT File:</b> {xslt_filename}", styles['Normal']))
    elements.append(Paragraph(f"<b>Invoice ID:</b> {details['invoice_identifier']}", styles['Normal']))
    
    gen_time = details.get('processed_at') or details.get('uploaded_at') or datetime.now(timezone.utc).isoformat()
    elements.append(Paragraph(f"<b>Generated At:</b> {gen_time}", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [["Rule Name", "Status", "Message"]]
    for item in details["checklist"]:
        data.append([
            item.get("rule_text") or "",
            item.get("status") or "FAIL",
            item.get("message") or ""
        ])

    table_data = []
    for i, row in enumerate(data):
        if i == 0:
            table_data.append(row)
        else:
            table_data.append([
                Paragraph(row[0], styles['Normal']),
                row[1],
                Paragraph(row[2], styles['Normal'])
            ])

    t = Table(table_data, colWidths=[230, 60, 230])
    t_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ])

    for i, item in enumerate(details["checklist"]):
        row_idx = i + 1
        if item.get("status") == "PASS":
            t_style.add('TEXTCOLOR', (1, row_idx), (1, row_idx), colors.HexColor("#2e7d32"))
            t_style.add('FONTNAME', (1, row_idx), (1, row_idx), 'Helvetica-Bold')
        else:
            t_style.add('TEXTCOLOR', (1, row_idx), (1, row_idx), colors.HexColor("#c62828"))
            t_style.add('FONTNAME', (1, row_idx), (1, row_idx), 'Helvetica-Bold')

    t.setStyle(t_style)
    elements.append(t)
    doc.build(elements)
    return output.getvalue()


@app.get("/api/results/{invoice_id}/pdf")
async def download_reportlab_pdf(invoice_id: int, db: AsyncSession = Depends(get_db)):
    """Generate PDF using reportlab with XSLT filename and PASS/FAIL table."""
    if invoice_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid invoice ID")
    try:
        details = await report_details(invoice_id, db)
        pdf_bytes = _generate_single_pdf(details)
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
        logger.error(f"ReportLab PDF generation failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")


@app.get("/api/results/export-zip")
async def download_all_results_zip(db: AsyncSession = Depends(get_db)):
    """Group all validated invoice results PDFs into a single ZIP and download."""
    try:
        invoices = (
            await db.execute(select(Invoice).order_by(Invoice.processed_at.desc(), Invoice.uploaded_at.desc()).limit(200))
        ).scalars().all()

        if not invoices:
            raise HTTPException(status_code=404, detail="No validated invoices found to export")

        zip_buffer = BytesIO()
        seen_names = set()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for inv in invoices:
                try:
                    details = await report_details(inv.id, db)
                    pdf_bytes = _generate_single_pdf(details)
                    safe_name = _PDF_FILENAME_SANITIZER.sub("-", details["invoice_identifier"]).strip("-") or f"INV-{inv.id}"
                    base_pdf_name = f"{safe_name}-validation-report.pdf"
                    pdf_name = base_pdf_name
                    counter = 1
                    while pdf_name in seen_names:
                        pdf_name = f"{safe_name}-validation-report({counter}).pdf"
                        counter += 1
                    seen_names.add(pdf_name)
                    zf.writestr(pdf_name, pdf_bytes)
                except Exception as ex:
                    logger.warning(f"Skipping PDF for invoice {inv.id} in ZIP export: {ex}")

        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="validated-invoice-results.zip"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ZIP export failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to generate ZIP export")


# ─── Sample Management ────────────────────────────────────────────────────────

@app.post("/api/sample-upload")
async def upload_sample(file: UploadFile = File(...)):
    """Upload a sample XML file, extract tags, store in Supabase."""
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

        # Extract tags
        tags_result = extract_xml_tags(xml_str)
        tags_list = tags_result.get("known_tags", []) + tags_result.get("unknown_tags", [])

        # Store in Supabase directly
        sample_insert = supabase.table("samples").insert({
            "filename": file.filename,
            "xml_content": xml_str,
            "extracted_tags": tags_list,
            "status": "active"
        }).execute()
        new_sample_id = sample_insert.data[0]["id"]

        # Also update active workspace to point to this new sample!
        try:
            ws_res = supabase.table("active_workspace").select("id").limit(1).execute()
            if ws_res.data:
                supabase.table("active_workspace").update({"sample_id": new_sample_id}).eq("id", ws_res.data[0]["id"]).execute()
            else:
                supabase.table("active_workspace").insert({"sample_id": new_sample_id}).execute()
        except Exception as e:
            logger.warning(f"Failed to update active workspace sample_id: {e}")

        return {
            "sample_id": new_sample_id,
            "filename": file.filename,
            "tags": tags_list,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sample upload failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Sample upload failed")


@app.get("/api/sample/current")
async def get_current_sample():
    """Get the most recently created sample from Supabase."""
    try:
        res = supabase.table("samples").select("id, filename, extracted_tags, status").order("created_at", desc=True).limit(1).execute()
        if not res.data:
            return {"sample_id": None, "filename": None, "extracted_tags": []}
        
        sample = res.data[0]
        return {
            "sample_id": sample["id"],
            "filename": sample["filename"],
            "extracted_tags": sample.get("extracted_tags") or [],
        }
    except Exception as e:
        logger.error(f"Failed to get current sample: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to get current sample")


@app.get("/api/workspace/active")
async def get_active_workspace():
    try:
        workspace = supabase.table("active_workspace").select("sample_id, xslt_id").limit(1).execute()

        if not workspace.data:
            await ensure_defaults()
            workspace = supabase.table("active_workspace").select("sample_id, xslt_id").limit(1).execute()

        if not workspace.data:
            # Return empty workspace if nothing is set
            return {
                "sample_id": None,
                "sample_filename": None,
                "xslt_id": None,
                "xslt_filename": None,
                "extracted_tags": [],
                "status": "empty"
            }

        row = workspace.data[0]
        
        # Safely fetch sample if ID exists
        sample = None
        if row.get("sample_id"):
            try:
                sample_result = supabase.table("samples").select("id, filename, extracted_tags, status").eq("id", row["sample_id"]).execute()
                sample = sample_result.data[0] if sample_result.data else None
            except Exception as e:
                logger.warning(f"Failed to fetch sample {row.get('sample_id')}: {e}")
        
        # Safely fetch xslt if ID exists
        xslt = None
        if row.get("xslt_id"):
            try:
                xslt_result = supabase.table("xslt_files").select("id, filename, status").eq("id", row["xslt_id"]).execute()
                xslt = xslt_result.data[0] if xslt_result.data else None
            except Exception as e:
                logger.warning(f"Failed to fetch xslt {row.get('xslt_id')}: {e}")

        return {
            "sample_id": sample["id"] if sample else None,
            "sample_filename": sample["filename"] if sample else None,
            "xslt_id": xslt["id"] if xslt else None,
            "xslt_filename": xslt["filename"] if xslt else None,
            "extracted_tags": (sample.get("extracted_tags") or []) if sample else [],
            "status": sample.get("status") if sample else "empty"
        }
    except Exception as e:
        logger.error(f"Failed to get active workspace: {str(e)[:100]}")
        # Return empty workspace instead of throwing error
        return {
            "sample_id": None,
            "sample_filename": None,
            "xslt_id": None,
            "xslt_filename": None,
            "extracted_tags": [],
            "status": "error"
        }


@app.put("/api/workspace/active")
async def update_active_workspace(body: UpdateWorkspaceRequest):
    try:
        ws_res = supabase.table("active_workspace").select("id").limit(1).execute()
        if not ws_res.data:
            await ensure_defaults()
            ws_res = supabase.table("active_workspace").select("id").limit(1).execute()
        
        ws_id = ws_res.data[0]["id"]
        update_data = {}

        if body.sample_id is not None:
            update_data["sample_id"] = body.sample_id
            # STATUS UPDATES ON REAL SELECTION
            try:
                supabase.table("samples").update({ "status": "active" }).eq("id", body.sample_id).execute()
            except Exception as e:
                logger.warning(f"Supabase sample status update failed: {e}")

        if body.xslt_id is not None:
            update_data["xslt_id"] = body.xslt_id
            # Ensure xslt_file exists in Supabase xslt_files table
            try:
                xslt_check = supabase.table("xslt_files").select("id").eq("id", body.xslt_id).execute()
                if not xslt_check.data and body.xslt_filename:
                    supabase.table("xslt_files").insert({
                        "id": body.xslt_id,
                        "filename": body.xslt_filename,
                        "status": "active",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }).execute()
                else:
                    # STATUS UPDATES ON REAL SELECTION
                    supabase.table("xslt_files").update({ "status": "active" }).eq("id", body.xslt_id).execute()
            except Exception as e:
                logger.warning(f"Supabase xslt_files check/update failed: {e}")

        if update_data:
            supabase.table("active_workspace").update(update_data).eq("id", ws_id).execute()

        return await get_active_workspace()
    except Exception as e:
        logger.error(f"Failed to update active workspace: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to update active workspace")


@app.get("/api/samples")
async def list_samples():
    """List all uploaded sample XMLs from Supabase."""
    try:
        res = supabase.table("samples").select("id, filename, created_at, status").order("created_at", desc=True).execute()
        return [
            {
                "id": s["id"],
                "filename": s["filename"],
                "created_at": s.get("created_at") or datetime.utcnow().isoformat(),
                "status": s.get("status") or "default"
            }
            for s in res.data
        ]
    except Exception as e:
        logger.error(f"Failed to list samples: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to list samples")


@app.post("/api/link")
async def link_sample_to_xslt(body: dict):
    """Link a sample XML to an XSLT file in Supabase."""
    try:
        sample_id = body.get("sample_id")
        xslt_file_id = body.get("xslt_id")

        if not sample_id or not xslt_file_id:
            raise HTTPException(status_code=400, detail="sample_id and xslt_id required")

        # Delete any existing link for this sample OR this XSLT file
        try:
            existing = supabase.table("xslt_sample_links").select("id").eq("sample_id", sample_id).execute()
            for link in existing.data:
                supabase.table("xslt_sample_links").delete().eq("id", link["id"]).execute()
                
            existing_xslt = supabase.table("xslt_sample_links").select("id").eq("xslt_id", xslt_file_id).execute()
            for link in existing_xslt.data:
                supabase.table("xslt_sample_links").delete().eq("id", link["id"]).execute()
        except Exception as e:
            logger.warning(f"Supabase link cleanup warning: {e}")

        # Create new link
        supabase.table("xslt_sample_links").insert({
            "sample_id": sample_id,
            "xslt_id": str(xslt_file_id),
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Also update active workspace
        try:
            ws_res = supabase.table("active_workspace").select("id").limit(1).execute()
            if ws_res.data:
                supabase.table("active_workspace").update({
                    "sample_id": sample_id,
                    "xslt_id": str(xslt_file_id)
                }).eq("id", ws_res.data[0]["id"]).execute()
        except Exception as e:
            logger.warning(f"Active workspace sync warning: {e}")

        return {
            "message": "Sample linked to XSLT",
            "sample_id": sample_id,
            "xslt_id": xslt_file_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Link failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to link sample to XSLT")







@app.get("/api/results/{id}/tags")
async def get_result_tags(id: int, db: AsyncSession = Depends(get_db)):
    """Extract XML tags from the validated invoice content associated with a validation result ID."""
    try:
        # Get ValidationResult by ID to fetch the associated invoice_id
        val_result = (
            await db.execute(select(ValidationResultORM).where(ValidationResultORM.id == id))
        ).scalars().first()
        if not val_result:
            raise HTTPException(status_code=404, detail="Validation result not found")
        
        invoice_id = val_result.invoice_id
        invoice = (
            await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        ).scalars().first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        tags_result = extract_xml_tags(invoice.xml_content or "")
        tags_list = [t["tag"] for t in tags_result.get("tags", [])]
        return {"tags": list(sorted(set(tags_list)))}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get result tags: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to get result tags")


@app.get("/api/results/{id}/rules")
async def get_result_rules(id: int, db: AsyncSession = Depends(get_db)):
    """Return all rules and their validation statuses evaluated during the same validation run as result ID."""
    try:
        # Get ValidationResult by ID to find the validation run (invoice_id)
        val_result = (
            await db.execute(select(ValidationResultORM).where(ValidationResultORM.id == id))
        ).scalars().first()
        if not val_result:
            raise HTTPException(status_code=404, detail="Validation result not found")
        
        invoice_id = val_result.invoice_id
        results = (
            await db.execute(
                select(ValidationResultORM).where(ValidationResultORM.invoice_id == invoice_id)
            )
        ).scalars().all()
        
        rules_list = []
        for r in results:
            rules_list.append({
                "rule_name": r.rule_text,
                "status": "PASS" if r.status == "PASS" else "FAIL"
            })
        return {"rules": rules_list}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get result rules: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to get result rules")


@app.get("/api/xslt-files/{id:path}/details")
async def get_xslt_details(id: str, db: AsyncSession = Depends(get_db)):
    """Return XSLT filename, linked sample XML filename, list of all rules, XSLT previews, and related logic under this XSLT file."""
    try:
        # Get XSLT file entry
        xslt = (
            await db.execute(select(XsltFile).where(XsltFile.id == id))
        ).scalars().first()
        xslt_filename = xslt.filename if xslt else id
        
        # Get linked sample file name
        sample_filename = "N/A"
        link = (
            await db.execute(select(XsltSampleLink).where(XsltSampleLink.xslt_file_id == id))
        ).scalars().first()
        if link:
            sample = (
                await db.execute(select(Sample).where(Sample.id == link.sample_id))
            ).scalars().first()
            if sample:
                sample_filename = sample.filename
                
        # Get all rules created under this XSLT
        rules_result = (
            await db.execute(select(Rule).where(Rule.xslt_id == id, Rule.is_active == True).order_by(Rule.created_at.asc()))
        ).scalars().all()
        
        rules_list = []
        xslt_previews = []
        related_logic = []

        for r in rules_result:
            rules_list.append({
                "rule_name": r.rule_text,
                "severity": r.severity,
                "field": r.field,
                "operation": r.operation
            })
            if r.xslt_logic:
                xslt_previews.append(f"<!-- Rule: {r.rule_text} -->\n{r.xslt_logic}")
            related_logic.append({
                "rule_id": r.id,
                "rule_text": r.rule_text,
                "xslt_logic": r.xslt_logic,
                "xpath_logic": r.xpath_logic,
                "python_logic": r.python_logic,
                "severity": r.severity,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        
        return {
            "xslt_filename": xslt_filename,
            "sample_filename": sample_filename,
            "rules": rules_list,
            "xslt_previews": xslt_previews,
            "related_logic": related_logic,
        }
    except Exception as e:
        logger.error(f"Failed to get XSLT details: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to get XSLT details")


@app.get("/api/xslt-files/{id:path}/download-package")
async def download_xslt_package(id: str, db: AsyncSession = Depends(get_db)):
    """Package and download everything related to an XSLT rule sheet as a structured ZIP."""
    try:
        xslt = (
            await db.execute(select(XsltFile).where(XsltFile.id == id))
        ).scalars().first()
        xslt_filename = xslt.filename if xslt else id
        safe_name = xslt_filename.replace(".xslt", "").replace(" ", "-")


        rules_result = (
            await db.execute(select(Rule).where(Rule.xslt_id == id, Rule.is_active == True).order_by(Rule.created_at.asc()))
        ).scalars().all()

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Main rules summary JSON
            summary = {
                "xslt_filename": xslt_filename,
                "xslt_id": id,
                "exported_at": datetime.utcnow().isoformat(),
                "total_rules": len(rules_result),
                "rules": [
                    {
                        "rule_id": r.id,
                        "rule_text": r.rule_text,
                        "severity": r.severity,
                        "xslt_logic": r.xslt_logic,
                        "xpath_logic": r.xpath_logic,
                        "python_logic": r.python_logic,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in rules_result
                ]
            }
            zf.writestr(f"{safe_name}-metadata.json", json.dumps(summary, indent=2))

            # 2. Individual XSLT rule blocks and combined logic
            combined_xslt_blocks = []
            rules_dir = "rules_logic/"
            for idx, r in enumerate(rules_result):
                rule_num = idx + 1
                if r.xslt_logic:
                    zf.writestr(f"{rules_dir}rule_{rule_num}_xslt.xml", r.xslt_logic)
                    combined_xslt_blocks.append(f"<!-- Rule {rule_num}: {r.rule_text} -->\n{r.xslt_logic}")
                if r.xpath_logic:
                    zf.writestr(f"{rules_dir}rule_{rule_num}_xpath.txt", r.xpath_logic)
                if r.python_logic:
                    zf.writestr(f"{rules_dir}rule_{rule_num}_python.py", r.python_logic)

            combined_xslt = f'<?xml version="1.0" encoding="UTF-8"?>\n<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">\n  <xsl:template match="/">\n    <validation_results>\n' + "\n".join(combined_xslt_blocks) + '\n    </validation_results>\n  </xsl:template>\n</xsl:stylesheet>'
            zf.writestr(f"{safe_name}-combined.xslt", combined_xslt)

        zip_buffer.seek(0)
        filename = f"{safe_name}-rule-sheet-package.zip"
        return StreamingResponse(
            zip_buffer, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Package download failed: {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to generate download package")


def _build_beautiful_xslt_pdf_lowlevel(filename: str, rules: list, xslt_content: str, xslt_previews: list) -> bytes:
    builder = LowLevelPDFBuilder()
    builder.new_page()

    # Title Banner
    builder.draw_rect(40, 780, 515, 30, 0.08, 0.15, 0.35)
    builder.draw_text("XSLT RULE SHEET & TEMPLATE PREVIEW", 50, 790, size=12, bold=True, color=(1, 1, 1))

    # Metadata Box
    builder.draw_rect(40, 705, 515, 65, 0.96, 0.97, 0.99, stroke=True)
    builder.draw_text("XSLT Filename:", 55, 745, bold=True, color=(0.2, 0.2, 0.2))
    builder.draw_text(_safe_text(filename, 60), 150, 745, color=(0.1, 0.1, 0.1))

    builder.draw_text("Total Rules:", 55, 730, bold=True, color=(0.2, 0.2, 0.2))
    builder.draw_text(str(len(rules)), 150, 730, color=(0.1, 0.1, 0.1))

    builder.draw_text("Exported At:", 55, 715, bold=True, color=(0.2, 0.2, 0.2))
    builder.draw_text(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'), 150, 715, color=(0.1, 0.1, 0.1))

    y = 680
    builder.draw_text("ASSOCIATED RULES SUMMARY", 40, y, size=10, bold=True, color=(0.1, 0.15, 0.3))
    builder.draw_line(40, y - 4, 555, y - 4, r=0.7, g=0.7, b=0.7)
    y -= 20

    if not rules:
        builder.draw_text("No active rules associated with this XSLT file.", 40, y, size=9, color=(0.4, 0.4, 0.4))
        y -= 25
    else:
        for idx, r_obj in enumerate(rules):
            if isinstance(r_obj, dict):
                r_text = r_obj.get("rule_name", "") or r_obj.get("rule_text", "")
                sev = r_obj.get("severity", "High") or "High"
                field_op = f"{r_obj.get('field') or 'N/A'} / {r_obj.get('operation') or 'N/A'}"
            else:
                r_text = str(r_obj)
                sev = "High"
                field_op = "N/A / N/A"

            lines = builder.wrap_text(r_text, 320, size=9)
            block_height = len(lines) * 12 + 12

            if y - block_height < 50:
                builder.new_page()
                y = 780

            builder.draw_rect(40, y - block_height, 515, block_height, 0.98, 0.98, 0.99, stroke=True)
            builder.draw_text(f"#{idx + 1}", 48, y - 14, size=9, bold=True, color=(0.3, 0.4, 0.8))

            for l_idx, line in enumerate(lines):
                builder.draw_text(line, 75, y - 14 - (l_idx * 12), size=9, color=(0.15, 0.15, 0.15))

            builder.draw_text(f"Sev: {str(sev).upper()}", 410, y - 14, size=8, bold=True, color=(0.6, 0.2, 0.2))
            builder.draw_text(builder.wrap_text(field_op, 130, size=8)[0], 410, y - 26, size=8, color=(0.4, 0.4, 0.4))

            y -= block_height + 8

    y -= 15
    if y - 40 < 50:
        builder.new_page()
        y = 780

    builder.draw_text("COMBINED XSLT TEMPLATE PREVIEW", 40, y, size=10, bold=True, color=(0.1, 0.15, 0.3))
    builder.draw_line(40, y - 4, 555, y - 4, r=0.7, g=0.7, b=0.7)
    y -= 20

    code_text = ""
    if xslt_previews:
        code_text = "\n\n".join(xslt_previews)
    elif xslt_content:
        code_text = xslt_content
    else:
        code_text = "<!-- No XSLT content available -->"

    code_lines = []
    for raw_line in code_text.splitlines():
        wrapped = builder.wrap_text(raw_line, 500, size=7)
        code_lines.extend(wrapped)

    for line in code_lines:
        if y < 50:
            builder.new_page()
            y = 780
        builder.draw_text(line, 45, y, size=7, color=(0.1, 0.25, 0.2))
        y -= 10

    return builder.build()


def _build_beautiful_xslt_pdf_reportlab(filename: str, rules: list, xslt_content: str, xslt_previews: list) -> bytes:
    output = BytesIO()
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors

    doc = SimpleDocTemplate(output, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []

    # Title & Header
    elements.append(Paragraph("XSLT RULE SHEET & TEMPLATE PREVIEW", styles['Title']))
    elements.append(Spacer(1, 15))

    elements.append(Paragraph(f"<b>XSLT Filename:</b> {_safe_text(filename)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Total Rules:</b> {len(rules)}", styles['Normal']))
    elements.append(Paragraph(f"<b>Exported At:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Rules Summary Table
    elements.append(Paragraph("<b>ASSOCIATED RULES SUMMARY</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))

    if rules:
        table_data = [["#", "Rule Description", "Severity", "Field / Operation"]]
        for idx, r_obj in enumerate(rules):
            if isinstance(r_obj, dict):
                r_text = r_obj.get("rule_name", "") or r_obj.get("rule_text", "")
                sev = r_obj.get("severity", "High") or "High"
                field_op = f"{r_obj.get('field') or 'N/A'} / {r_obj.get('operation') or 'N/A'}"
            else:
                r_text = str(r_obj)
                sev = "High"
                field_op = "N/A / N/A"

            table_data.append([
                str(idx + 1),
                Paragraph(_safe_text(r_text, 300), styles['Normal']),
                str(sev).upper(),
                Paragraph(_safe_text(field_op, 100), styles['Normal'])
            ])

        t = Table(table_data, colWidths=[30, 260, 70, 180])
        t_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
        ])
        t.setStyle(t_style)
        elements.append(t)
    else:
        elements.append(Paragraph("<i>No active rules associated with this XSLT file.</i>", styles['Normal']))

    elements.append(Spacer(1, 25))

    # Combined XSLT Preview
    elements.append(Paragraph("<b>COMBINED XSLT TEMPLATE PREVIEW</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))

    code_text = ""
    if xslt_previews:
        code_text = "\n\n".join(xslt_previews)
    elif xslt_content:
        code_text = xslt_content
    else:
        code_text = "<!-- No XSLT content available -->"

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=1,
        borderPadding=10,
        spaceBefore=5,
        spaceAfter=15
    )

    formatted_code = code_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>").replace(" ", "&#160;")
    elements.append(Paragraph(formatted_code, code_style))

    doc.build(elements)
    return output.getvalue()


@app.get("/api/xslt-files/{id:path}/pdf")
async def download_xslt_pdf(id: str, db: AsyncSession = Depends(get_db)):
    """Generate and download a beautifully organized PDF containing the XSLT Rule Sheet summary, rules list, and complete XSLT template preview."""
    try:
        xslt = (
            await db.execute(select(XsltFile).where(XsltFile.id == id))
        ).scalars().first()
        xslt_filename = xslt.filename if xslt else id
        safe_name = xslt_filename.replace(".xslt", "").replace(" ", "-")

        rules_result = (
            await db.execute(select(Rule).where(Rule.xslt_id == id, Rule.is_active == True).order_by(Rule.created_at.asc()))
        ).scalars().all()

        rules_list = [{"rule_name": r.rule_text, "severity": r.severity, "field": r.field, "operation": r.operation} for r in rules_result]
        xslt_previews = [f"<!-- Rule {idx+1}: {r.rule_text} -->\n{r.xslt_logic}" for idx, r in enumerate(rules_result) if r.xslt_logic]

        try:
            pdf_bytes = _build_beautiful_xslt_pdf_reportlab(xslt_filename, rules_list, "", xslt_previews)
        except ImportError:
            logger.warning("reportlab not installed, falling back to LowLevelPDFBuilder for XSLT PDF")
            pdf_bytes = _build_beautiful_xslt_pdf_lowlevel(xslt_filename, rules_list, "", xslt_previews)

        pdf_filename = f"{safe_name}-rule-sheet-preview.pdf"
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"XSLT PDF generation failed (GET): {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to generate XSLT preview PDF")


@app.post("/api/xslt-files/{id:path}/pdf")
async def download_xslt_pdf_post(id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Generate and download a beautifully organized PDF from frontend-provided rules and XSLT content."""
    try:
        filename = body.get("filename") or id
        rules = body.get("rules") or []
        xslt_content = body.get("xslt_content") or ""
        xslt_previews = body.get("xslt_previews") or []

        safe_name = filename.replace(".xslt", "").replace(" ", "-")

        try:
            pdf_bytes = _build_beautiful_xslt_pdf_reportlab(filename, rules, xslt_content, xslt_previews)
        except ImportError:
            logger.warning("reportlab not installed, falling back to LowLevelPDFBuilder for XSLT PDF")
            pdf_bytes = _build_beautiful_xslt_pdf_lowlevel(filename, rules, xslt_content, xslt_previews)

        pdf_filename = f"{safe_name}-rule-sheet-preview.pdf"
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"XSLT PDF generation failed (POST): {str(e)[:100]}")
        raise HTTPException(status_code=500, detail="Failed to generate XSLT preview PDF")





# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics."""
    try:
        # Sequential queries with explicit await and safe default counts
        total_rules = (await db.execute(select(func.count(Rule.id)))).scalar() or 0
        total_inv   = (await db.execute(select(func.count(Invoice.id)))).scalar() or 0
        total_val   = (await db.execute(select(func.count(ValidationResultORM.id)))).scalar() or 0
        passed      = (await db.execute(
            select(func.count(ValidationResultORM.id)).where(ValidationResultORM.status == "PASS")
        )).scalar() or 0
        failed      = (await db.execute(
            select(func.count(ValidationResultORM.id)).where(ValidationResultORM.status == "FAIL")
        )).scalar() or 0
        
        # Query total_xslt_files from XsltFile table safely
        total_xslt  = (await db.execute(select(func.count(XsltFile.id)))).scalar() or 0

        # Guard every division to prevent ZeroDivisionError
        pass_rate = round((passed / total_val * 100), 1) if total_val > 0 else 0.0
        fail_rate = round((failed / total_val * 100), 1) if total_val > 0 else 0.0

        return {
            "total_rules":       total_rules,
            "total_invoices":    total_inv,
            "total_validations": total_val,
            "total_passed":      passed,
            "total_failed":      failed,
            "pass_rate":         pass_rate,
            "total_xslt_files":  total_xslt,
            "fail_rate":         fail_rate,
        }
    except Exception as e:
        # Server-side logging of the traceback/error
        logger.error(f"Database error in dashboard_stats: {str(e)}", exc_info=True)
        # Always return a valid JSON response with zeroed stats on any database error instead of raising 500
        return {
            "total_rules":       0,
            "total_invoices":    0,
            "total_validations": 0,
            "total_passed":      0,
            "total_failed":      0,
            "pass_rate":         0.0,
            "total_xslt_files":  0,
            "fail_rate":         0.0,
        }


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
