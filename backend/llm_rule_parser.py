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
OPENROUTER_MODEL   = os.getenv("OPEN_ROUTER_MODEL", "meta-llama/llama-3-8b-instruct")

SYSTEM_PROMPT = """## ROLE
You are a deterministic invoice rule parser for an XML validation engine. Your only job is to convert natural-language business rules into structured JSON rule objects. You must NEVER invent field names, operators, or logic not explicitly defined below.

## SUPPORTED FIELDS (strict allowlist)
# Only these 12 fields are valid. Reject any rule referencing fields outside this list.
tax_amount        — numeric, the tax charged
taxable_amount    — numeric, the base amount before tax
payable_amount    — numeric, the total invoice amount
invoice_id        — string, unique invoice identifier
seller_name       — string, name of the seller
buyer_name        — string, name of the buyer
issue_date        — date (ISO 8601), invoice issue date
currency_code     — string (ISO 4217), e.g. "INR", "USD"
tax_category      — string, tax category code
tax_exemption_reason — string, reason if tax is exempt
buyer_vat         — string, buyer VAT/GST registration number
purchase_order    — string, associated PO number

## FIELD MAPPING (fuzzy input → canonical field)
# Map common user phrasings to the correct canonical field name.
"GST number", "GST id", "buyer GST" → buyer_vat
"invoice date", "issue date", "date of invoice" → issue_date
"invoice number", "invoice id", "invoice no" → invoice_id
"total amount", "total payable", "amount due" → payable_amount
"tax", "GST amount", "tax charged" → tax_amount
"subtotal", "base amount", "taxable" → taxable_amount
"seller", "vendor name" → seller_name
"buyer", "customer name" → buyer_name
"currency", "currency type" → currency_code
"PO number", "purchase order number" → purchase_order

## SUPPORTED RULE TYPES
presence   — field must exist and be non-empty
range      — numeric field must be between min and max (inclusive)
compare    — field compared to a value or another field (gt, lt, gte, lte, eq, neq)
date_rule  — date field constraint (not_future, not_past, after_field, before_field)
equals     — field must exactly equal a constant value
formula    — field must equal a mathematical expression of other fields
percentage — field must equal (other_field * rate / 100) within tolerance

## OUTPUT FORMAT
Always respond with a single valid JSON object. No markdown, no explanation, no extra text.

{
  "rule_type": "<one of the supported types above>",
  "field": "<canonical field name from allowlist>",
  "operator": "<gt | lt | gte | lte | eq | neq — only for compare type>",
  "value": "<constant value if applicable>",
  "min": <number, only for range type>,
  "max": <number, only for range type>,
  "constraint": "<not_future | not_past | after_field | before_field — for date_rule>",
  "reference_field": "<canonical field, for formula/compare/date_rule>",
  "expression": "<math expression string, for formula type>",
  "rate": <number, only for percentage type>,
  "tolerance": <number, optional, default 0.01 for percentage/formula>,
  "description": "<exact user rule text, preserved verbatim>",
  "confidence": <0.0–1.0, your confidence this parse is correct>,
  "warnings": ["<list any ambiguities or assumptions made>"]
}

## PARSING RULES (follow in strict order)

1. Normalize phrasing first — apply field mapping table before any other step.
2. Classify rule type — pick the most specific type that fits.
3. Validate fields — if a field name cannot be mapped to the allowlist, set rule_type to "unsupported" and explain in warnings.
4. Handle derived fields — terms like "tax percentage" or "GST rate" refer to a computed value (tax_amount / taxable_amount * 100), not a stored field. Use rule_type "percentage" with appropriate fields.
5. Never hallucinate fields — if the rule references something unmappable (e.g. "line item total", "subtotal", "discount amount"), set rule_type to "unsupported" and list the unresolvable term in warnings.
6. Preserve ambiguity — if a rule could be interpreted multiple ways, pick the most likely interpretation, set confidence below 0.8, and list alternatives in warnings.
7. Date rules — "cannot be in the future" → constraint: "not_future"; "must be after X" → constraint: "after_field", reference_field: X.
8. Presence rules — "must exist", "must be present", "should not be empty", "must not be null" all map to rule_type "presence".

## EXAMPLES

Input: "Tax percentage must be between 0 and 28"
Output:
{
  "rule_type": "percentage",
  "field": "tax_amount",
  "reference_field": "taxable_amount",
  "min": 0,
  "max": 28,
  "tolerance": 0.01,
  "description": "Tax percentage must be between 0 and 28",
  "confidence": 0.95,
  "warnings": []
}

Input: "Buyer GST number must exist"
Output:
{
  "rule_type": "presence",
  "field": "buyer_vat",
  "description": "Buyer GST number must exist",
  "confidence": 0.99,
  "warnings": []
}

Input: "Invoice date cannot be in the future"
Output:
{
  "rule_type": "date_rule",
  "field": "issue_date",
  "constraint": "not_future",
  "description": "Invoice date cannot be in the future",
  "confidence": 0.99,
  "warnings": []
}

Input: "Total amount must equal subtotal plus tax"
Output:
{
  "rule_type": "formula",
  "field": "payable_amount",
  "expression": "taxable_amount + tax_amount",
  "tolerance": 0.01,
  "description": "Total amount must equal subtotal plus tax",
  "confidence": 0.92,
  "warnings": ["'subtotal' mapped to taxable_amount"]
}

Input: "Invoice currency must be INR when country is India"
Output:
{
  "rule_type": "unsupported",
  "field": "currency_code",
  "description": "Invoice currency must be INR when country is India",
  "confidence": 0.0,
  "warnings": ["Conditional rules based on 'country' are not supported. 'country' is not in the field allowlist. Consider splitting into two rules or adding 'country' as a supported field."]
}

## ERROR BEHAVIOUR
- Never return HTTP 500 for a parseable rule. Return a structured JSON with rule_type "unsupported" and a descriptive warnings array instead.
- A 500 should only occur for malformed JSON, empty input, or internal server errors — not for rules referencing unsupported fields.
- Always return valid JSON. Never return plain text error messages.

## UNKNOWN XML TAG HANDLING

If the rule contains a field name you cannot map to the 12 supported
fields, you must NEVER return a bare "unsupported" with no guidance.

Always return:
{
  "rule_type": "unsupported",
  "field": null,
  "confidence": 0.0,
  "description": "<original rule verbatim>",
  "warnings": [
    "Unrecognized field: '<the exact word the user wrote>'",
    "Closest supported field: '<best match from the 12>'",
    "Suggested rewrite: '<rewritten rule using the closest field>'"
  ]
}

For 'salary', 'price', 'wage', 'cost', 'amount' style words with no
clear invoice meaning → suggest payable_amount or taxable_amount.
For 'date' style words → suggest issue_date.
For 'name' style words → suggest seller_name or buyer_name.
For 'id', 'number', 'no' style words → suggest invoice_id.
Always include a suggested rewrite. Never leave warnings empty on
an unsupported result.

DIRECT TAG MODE
If the rule contains a tag that ends with _direct_tag=true in the
metadata, or if the field name does not match any canonical field
but was explicitly provided by the user from their XML schema,
treat it as a DIRECT XML PATH. Do not remap it to a canonical field.

Generate XSLT that queries it literally using its exact tag name.

Example:
Rule: "seller_ph must be present"
Tag source: user XML (not canonical field)
→
{
"rule_type": "presence",
"field": "seller_ph",
"is_direct_tag": true,
"xpath": "/Invoice/seller_ph",
"description": "seller_ph must be present",
"confidence": 0.95,
"warnings": ["'seller_ph' is a non-standard tag queried directly from user XML"]
}

For direct tags:

rule_type follows normal logic (presence, compare, range etc.)
field = exact tag name as written
is_direct_tag = true
xpath = "/Invoice/<tag_name>"
Never remap or substitute the tag name
Generate XSLT using the exact xpath provided
UNSUPPORTED RULE — REQUIRED WARNING FORMAT
When rule_type is unsupported, warnings must always contain:

The exact unrecognized term
Closest canonical field match
A suggested rewrite
Never return empty warnings on an unsupported result.
Never return HTTP 500 for a rule parsing failure.
Always return valid JSON only — no markdown, no explanation text.
"""


def _clean_json(raw: str, original_rule_text: str = "") -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")
    
    try:
        parsed = json.loads(raw)
    except Exception as e:
        return {
            "rule_type": "unsupported",
            "field": None,
            "description": original_rule_text,
            "confidence": 0.0,
            "warnings": [f"Malformed JSON returned by LLM: {str(e)}"]
        }

    # Strict allowlist
    allowed_fields = {
        "tax_amount", "taxable_amount", "payable_amount", "invoice_id", 
        "seller_name", "buyer_name", "issue_date", "currency_code", 
        "tax_category", "tax_exemption_reason", "buyer_vat", "purchase_order"
    }
    
    # Ensure warnings is a list
    if "warnings" not in parsed or not isinstance(parsed["warnings"], list):
        parsed["warnings"] = []

    # Check for unsupported fields
    field = parsed.get("field")
    if parsed.get("is_direct_tag") is not True:
        if field and field not in allowed_fields:
            parsed["warnings"].append(f"Field '{field}' is not in the allowed list and is unsupported")
            parsed["rule_type"] = "unsupported"
            parsed["field"] = None

    orig_type = parsed.get("rule_type", "unsupported")

    # Populate both legacy and new schema fields to keep E2E tests and DB 100% happy!
    if orig_type in ["presence", "required_field"]:
        parsed["rule_type"] = "required_field"
        parsed["operation"] = "not_empty"
        
    elif orig_type in ["percentage", "amount_calculation"]:
        parsed["rule_type"] = "amount_calculation"
        parsed["operation"] = "percentage"
        parsed["base_field"] = parsed.get("reference_field") or "taxable_amount"
        parsed["value"] = parsed.get("rate") or parsed.get("value") or 0
        
    elif orig_type == "formula":
        parsed["rule_type"] = "amount_calculation"
        expr = parsed.get("expression", "")
        if "+" in expr:
            parts = [p.strip() for p in expr.split("+")]
            parsed["operation"] = "sum"
            parsed["base_field"] = parts[0]
            parsed["add_field"] = parts[1] if len(parts) > 1 else ""
        else:
            parsed["operation"] = "percentage"
            
    elif orig_type in ["date_rule", "date_validation"]:
        parsed["rule_type"] = "date_validation"
        constraint = parsed.get("constraint") or parsed.get("operation") or ""
        if "future" in constraint:
            parsed["operation"] = "not_future"
        else:
            parsed["operation"] = "valid_date"
            
    elif orig_type in ["compare", "numeric_comparison"]:
        if parsed.get("field") == "currency_code":
            parsed["rule_type"] = "currency_consistency"
            parsed["operation"] = "in"
            val = parsed.get("value")
            parsed["value"] = [val] if isinstance(val, str) else (val or [])
        else:
            parsed["rule_type"] = "numeric_comparison"
            parsed["operation"] = parsed.get("operator") or parsed.get("operation") or "gt"
            
    elif orig_type == "equals":
        if parsed.get("field") == "currency_code":
            parsed["rule_type"] = "currency_consistency"
            parsed["operation"] = "in"
            val = parsed.get("value")
            parsed["value"] = [val] if isinstance(val, str) else (val or [])
        elif parsed.get("field") == "tax_category":
            parsed["rule_type"] = "tax_category_validation"
            parsed["operation"] = "in"
            val = parsed.get("value")
            parsed["value"] = [val] if isinstance(val, str) else (val or [])
        else:
            parsed["rule_type"] = "numeric_comparison"
            parsed["operation"] = "gte"
            
    elif orig_type == "currency_consistency":
        parsed["rule_type"] = "currency_consistency"
        parsed["operation"] = "in"
        
    elif orig_type == "conditional_required_field":
        parsed["rule_type"] = "conditional_required_field"
        parsed["operation"] = "conditional_required"
        
    elif orig_type == "duplicate_field_check":
        parsed["rule_type"] = "duplicate_field_check"
        parsed["operation"] = "unique"

    # Strict rule type validation
    allowed_rules = {
        "required_field", "amount_calculation", "date_validation", 
        "numeric_comparison", "currency_consistency", "tax_category_validation", 
        "conditional_required_field", "duplicate_field_check", "unsupported"
    }
    
    if parsed.get("rule_type") not in allowed_rules:
        parsed["rule_type"] = "unsupported"

    # Preserve all new schema fields
    if "operator" not in parsed:
        parsed["operator"] = parsed.get("operation")
    if "constraint" not in parsed:
        parsed["constraint"] = "not_future" if parsed.get("operation") == "not_future" else None
    if "rate" not in parsed:
        parsed["rate"] = parsed.get("value") if parsed.get("operation") == "percentage" else None
    if "reference_field" not in parsed:
        parsed["reference_field"] = parsed.get("base_field")

    if not parsed.get("description"):
        parsed["description"] = original_rule_text
        
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
    return _clean_json(raw, rule_text)


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
    return _clean_json(raw, rule_text)


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