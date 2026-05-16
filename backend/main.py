"""
main.py - FastAPI application.
Fully integrated with Steve's modules and the new database models.
"""

import json
import os
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

import evaluator
import rule_parser
import models
from database import get_db, init_db

app = FastAPI(title="PS-3 Rule Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await init_db()

# ─── Validation ───────────────────────────────────────────────────────────────

@app.post("/validate", response_model=models.ValidationResultItem)
async def validate_single(body: models.ValidateRequest):
    res = evaluator.evaluate_one(body.rule_text, body.xml_content)
    return res

@app.post("/validate/all-rules", response_model=models.ValidationResponse)
async def validate_all(body: models.ValidateRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(models.Rule)
    result = await db.execute(stmt)
    rules = result.scalars().all()
    
    rule_list = [{"id": r.id, "rule_text": r.rule_text} for r in rules]
    res = evaluator.evaluate_batch(rule_list, body.xml_content)
    return res

# ─── Rules CRUD ───────────────────────────────────────────────────────────────

@app.post("/rules", response_model=models.RuleResponse)
async def create_rule(body: models.RuleCreate, db: AsyncSession = Depends(get_db)):
    parsed = rule_parser.parse_rule(body.rule_text)
    new_rule = models.Rule(
        rule_text=body.rule_text,
        parsed_json=json.dumps(parsed),
        severity=body.severity
    )
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    
    return {
        "id": new_rule.id,
        "rule_text": new_rule.rule_text,
        "rule_type": parsed.get("rule_type"),
        "parsed_json": new_rule.parsed_json,
        "severity": new_rule.severity,
        "created_at": new_rule.created_at.isoformat()
    }

@app.get("/rules", response_model=List[models.RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    stmt = select(models.Rule).order_by(models.Rule.created_at.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()
    
    return [{
        "id": r.id,
        "rule_text": r.rule_text,
        "parsed_json": r.parsed_json,
        "severity": r.severity,
        "created_at": r.created_at.isoformat()
    } for r in rules]

# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/dashboard/stats", response_model=models.DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_rules = (await db.execute(select(func.count(models.Rule.id)))).scalar() or 0
    total_inv = (await db.execute(select(func.count(models.Invoice.id)))).scalar() or 0
    
    return {
        "total_rules": total_rules,
        "total_invoices": total_inv,
        "total_validations": 0,
        "passed": 0,
        "failed": 0
    }

@app.get("/health", response_model=models.HealthResponse)
async def health():
    return {"status": "ok", "database": "connected", "version": "1.0.0"}
