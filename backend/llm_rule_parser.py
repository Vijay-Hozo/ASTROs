"""
llm_rule_parser.py — LLM extracts structured variables from English rule.
Primary:  Groq (llama-3.1-70b-versatile) — fast, free
Fallback: OpenRouter — reliable fallback
"""

import json
import os
import re
import requests
from dotenv import load_dotenv
from xslt_templates import build_xslt

load_dotenv()

GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY", "")
GROQ_MODEL         = "llama-3.3-70b-versatile"
OPENROUTER_MODEL   = os.getenv("OPEN_ROUTER_MODEL", "anthropic/claude-3.5-sonnet")

SYSTEM_PROMPT = """You are a rule parser for an invoice validation system.
Your ONLY job is to extract structured information from a plain English validation rule.
You must respond with ONLY a valid JSON object — no explanation, no markdown, no backticks.

The JSON must follow this exact schema:
{
  "rule_type": one of ["required_field","amount_calculation","date_validation","numeric_comparison","currency_consistency","tax_category_validation","conditional_required_field","duplicate_field_check"],
  "field": the XML field name being validated (snake_case),
  "operation": the operation to perform,
  "base_field": (for amount_calculation only),
  "add_field": (for sum operation only),
  "value": numeric value or list of allowed values,
  "condition_field": (for conditional_required_field only),
  "condition_value": (for conditional_required_field only),
  "required_field": (for conditional_required_field only),
  "message": short error message if rule fails
}

Field name mapping:
- "tax amount" → "tax_amount"
- "taxable amount" → "taxable_amount"
- "payable amount" or "total amount" → "payable_amount"
- "invoice id" or "invoice number" → "invoice_id"
- "seller name" → "seller_name"
- "buyer name" → "buyer_name"
- "issue date" → "issue_date"
- "currency code" or "currency" → "currency_code"
- "tax category" → "tax_category"
- "tax exemption reason" → "tax_exemption_reason"
- "buyer vat number" → "buyer_vat"

Operations:
- required_field: "not_empty"
- amount_calculation: "percentage" or "sum"
- date_validation: "not_future" or "valid_date"
- numeric_comparison: "gt","gte","lt","lte","gte_zero"
- currency_consistency: "in" or "matches_invoice_currency"
- tax_category_validation: "in"
- conditional_required_field: "conditional_required"
- duplicate_field_check: "unique"

Examples:
Input: "Tax amount must be exactly 18% of taxable amount"
Output: {"rule_type":"amount_calculation","field":"tax_amount","operation":"percentage","base_field":"taxable_amount","value":18,"message":"Tax amount mismatch"}

Input: "Seller name is required"
Output: {"rule_type":"required_field","field":"seller_name","operation":"not_empty","message":"Seller name is missing"}

Input: "If tax category is E, tax exemption reason is required"
Output: {"rule_type":"conditional_required_field","field":"tax_exemption_reason","condition_field":"tax_category","condition_value":"E","required_field":"tax_exemption_reason","operation":"conditional_required","message":"Tax exemption reason required when tax category is E"}

Respond ONLY with valid JSON. Nothing else."""


def _clean_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")
    parsed = json.loads(raw)
    
    # Hallucination protection / Strict Schema Validation
    allowed_fields = {
        "tax_amount", "taxable_amount", "payable_amount", "invoice_id", 
        "seller_name", "buyer_name", "issue_date", "currency_code", 
        "tax_category", "tax_exemption_reason", "buyer_vat"
    }
    allowed_rules = {
        "required_field", "amount_calculation", "date_validation", 
        "numeric_comparison", "currency_consistency", "tax_category_validation", 
        "conditional_required_field", "duplicate_field_check"
    }
    
    if "rule_type" not in parsed or parsed["rule_type"] not in allowed_rules:
        raise ValueError(f"Invalid or missing rule_type: {parsed.get('rule_type')}")
        
    if "field" not in parsed or parsed["field"] not in allowed_fields:
        raise ValueError(f"Invalid or hallucinated field: {parsed.get('field')}")
        
    return parsed


def _call_groq(rule_text: str) -> dict:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type":  "application/json",
        },
        json={
            "model":           GROQ_MODEL,
            "messages":        [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": rule_text},
            ],
            "temperature":     0,
            "max_tokens":      500,
            "response_format": {"type": "json_object"},
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Groq {response.status_code}: {response.text[:200]}")
    raw = response.json()["choices"][0]["message"]["content"].strip()
    return _clean_json(raw)


def _call_openrouter(rule_text: str) -> dict:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type":  "application/json",
        },
        json={
            "model":           OPENROUTER_MODEL,
            "messages":        [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": rule_text},
            ],
            "temperature":     0,
            "max_tokens":      500,
            "response_format": {"type": "json_object"},
        },
        timeout=15,
    )
    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter {response.status_code}: {response.text[:200]}")
    raw = response.json()["choices"][0]["message"]["content"].strip()
    return _clean_json(raw)


def parse_rule_with_llm(rule_text: str) -> dict:
    """Groq first → OpenRouter fallback."""
    groq_err = None
    try:
        structured = _call_groq(rule_text)
        structured["_provider"] = "groq"
        print(f"[parser] groq [OK]  {rule_text[:60]}")
        return structured
    except Exception as e:
        groq_err = e
        print(f"[parser] groq [FAIL]  {e} - falling back to openrouter")

    try:
        structured = _call_openrouter(rule_text)
        structured["_provider"] = "openrouter"
        print(f"[parser] openrouter [OK]  {rule_text[:60]}")
        return structured
    except Exception as openrouter_err:
        raise RuntimeError(
            f"Both providers failed.\nGroq: {groq_err}\nOpenRouter: {openrouter_err}"
        )


def parse_rule(rule_text: str) -> dict:
    structured = parse_rule_with_llm(rule_text)
    structured["rule_text"] = rule_text
    return structured


def parse_rule_and_build_xslt(rule_text: str) -> dict:
    structured = parse_rule(rule_text)
    xslt_str   = build_xslt(structured)
    return {"structured": structured, "xslt": xslt_str}


if __name__ == "__main__":
    tests = [
        "Tax amount must be exactly 18% of taxable amount",
        "Seller name is required",
        "Issue date cannot be in the future",
        "Currency code must be one of USD, EUR, GBP, INR, or AED",
        "If tax category is E, tax exemption reason is required",
    ]
    print("=" * 60)
    print("LLM RULE PARSER — Groq primary / OpenRouter fallback")
    print("=" * 60)
    passed = 0
    for rule_text in tests:
        try:
            result = parse_rule_and_build_xslt(rule_text)
            s = result["structured"]
            print(f"[OK] [{s.get('_provider'):>9}] type={s.get('rule_type')} field={s.get('field')}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] FAILED: {e}")
    print(f"\n{passed}/{len(tests)} passed")