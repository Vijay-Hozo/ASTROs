"""
Rule Parser — converts plain English rules into structured rule objects.
Strategy: regex pattern matching, one handler per rule type.
No LLM. Pure deterministic logic.
"""

import re
from typing import Optional

# ─── Field alias map ──────────────────────────────────────────────────────────
# Maps natural language phrases → XML field names

FIELD_ALIASES = {
    "tax amount":            "tax_amount",
    "taxable amount":        "taxable_amount",
    "payable amount":        "payable_amount",
    "total amount":          "payable_amount",
    "invoice id":            "invoice_id",
    "invoice number":        "invoice_id",
    "seller name":           "seller_name",
    "buyer name":            "buyer_name",
    "issue date":            "issue_date",
    "invoice date":          "issue_date",
    "currency code":         "currency_code",
    "currency":              "currency_code",
    "tax category":          "tax_category",
    "tax exemption reason":  "tax_exemption_reason",
    "exemption reason":      "tax_exemption_reason",
    "buyer vat":             "buyer_vat",
    "buyer vat number":      "buyer_vat",
    "seller vat":            "seller_vat",
    "line item currency":    "line_item_currency",
}

VALID_CURRENCIES = ["USD", "EUR", "GBP", "INR", "AED"]
VALID_TAX_CATS   = ["S", "Z", "E", "AE"]


def resolve_field(text: str) -> Optional[str]:
    """Map a natural language field phrase to its XML field name."""
    text = text.strip().lower()
    return FIELD_ALIASES.get(text)


# ─── Pattern handlers — one per rule type ─────────────────────────────────────

def try_amount_calculation(text: str) -> Optional[dict]:
    """
    Patterns:
      'X must be exactly N% of Y'
      'X must equal Y plus Z'
      'X must equal Y + Z'
    """
    # percentage pattern
    m = re.search(
        r"([\w\s]+?)\s+must be (?:exactly\s+)?(\d+(?:\.\d+)?)\s*%\s+of\s+([\w\s]+)",
        text, re.IGNORECASE
    )
    if m:
        field     = resolve_field(m.group(1).strip())
        value     = float(m.group(2))
        base      = resolve_field(m.group(3).strip())
        if field and base:
            return {
                "rule_type": "amount_calculation",
                "field":      field,
                "operation":  "percentage",
                "base_field": base,
                "value":      value,
            }

    # sum pattern — 'X must equal Y plus Z'
    m = re.search(
        r"([\w\s]+?)\s+must (?:equal|be)\s+([\w\s]+?)\s+(?:plus|\+)\s+([\w\s]+)",
        text, re.IGNORECASE
    )
    if m:
        field  = resolve_field(m.group(1).strip())
        base1  = resolve_field(m.group(2).strip())
        base2  = resolve_field(m.group(3).strip())
        if field and base1 and base2:
            return {
                "rule_type":   "amount_calculation",
                "field":        field,
                "operation":    "sum",
                "base_field":   base1,
                "add_field":    base2,
            }

    return None


def try_required_field(text: str) -> Optional[dict]:
    """
    Patterns:
      'X is required'
      'Invoice must contain a X'
      'X must not be empty'
      'X must be present'
    """
    patterns = [
        r"([\w\s]+?)\s+is required",
        r"invoice must contain (?:a |an )?([\w\s]+)",
        r"([\w\s]+?)\s+must not be empty",
        r"([\w\s]+?)\s+must be present",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            field = resolve_field(m.group(1).strip())
            if field:
                return {
                    "rule_type": "required_field",
                    "field":      field,
                    "operation":  "not_empty",
                }
    return None


def try_date_validation(text: str) -> Optional[dict]:
    """
    Patterns:
      'issue date cannot be in the future'
      'issue date must be a valid calendar date'
      'issue date must not be a future date'
    """
    text_l = text.lower()
    if "date" in text_l:
        if "future" in text_l or "cannot be in the future" in text_l:
            return {
                "rule_type": "date_validation",
                "field":      "issue_date",
                "operation":  "not_future",
            }
        if "valid" in text_l and ("calendar" in text_l or "date" in text_l):
            return {
                "rule_type": "date_validation",
                "field":      "issue_date",
                "operation":  "valid_date",
            }
    return None


def try_numeric_comparison(text: str) -> Optional[dict]:
    """
    Patterns:
      'X must be greater than N'
      'X must be less than N'
      'X must not be negative'
      'X must be greater than or equal to N'
    """
    ops_map = {
        r"must be greater than or equal to\s+(\d+(?:\.\d+)?)": "gte",
        r"must be less than or equal to\s+(\d+(?:\.\d+)?)":    "lte",
        r"must be greater than\s+(\d+(?:\.\d+)?)":             "gt",
        r"must be less than\s+(\d+(?:\.\d+)?)":                "lt",
        r"must be greater than\s+zero":                         "gte_zero",
        r"must be less than\s+zero":                            "lte_zero",
        r"must not be negative":                                "gte_zero",
    }

    for pat, op in ops_map.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            # extract field from start of sentence
            field_match = re.match(r"([\w\s]+?)\s+must", text, re.IGNORECASE)
            if field_match:
                field = resolve_field(field_match.group(1).strip())
                if field:
                    result = {
                        "rule_type": "numeric_comparison",
                        "field":      field,
                        "operation":  op,
                    }
                    if op in ("gte_zero", "lte_zero"):
                        result["value"] = 0.0
                    elif hasattr(m, "group") and m.lastindex and m.lastindex >= 1:
                        try:
                            result["value"] = float(m.group(1))
                        except (IndexError, TypeError):
                            result["value"] = 0.0
                    return result
    return None


def try_currency_consistency(text: str) -> Optional[dict]:
    """
    Patterns:
      'Currency code must be one of USD, EUR, GBP...'
      'All line items must use the same currency as the invoice'
    """
    text_l = text.lower()

    if "line item" in text_l and "same currency" in text_l:
        return {
            "rule_type": "currency_consistency",
            "field":      "line_item_currency",
            "operation":  "matches_invoice_currency",
        }

    m = re.search(r"currency.*?must be (?:one of\s+)?([A-Z, ]+)", text, re.IGNORECASE)
    if m:
        raw = m.group(1)
        currencies = [c.strip() for c in re.split(r"[,\s]+|or\s+", raw) if c.strip()]
        currencies = [c for c in currencies if c.upper() in VALID_CURRENCIES]
        if currencies:
            return {
                "rule_type": "currency_consistency",
                "field":      "currency_code",
                "operation":  "in",
                "value":      currencies,
            }
    return None


def try_tax_category_validation(text: str) -> Optional[dict]:
    """
    Patterns:
      'Tax category must be S, Z, E, or AE'
      'Tax category must be one of S, Z, E, AE'
    """
    text_l = text.lower()
    if "tax category" in text_l and "must be" in text_l:
        found = re.findall(r"\b(S|Z|E|AE)\b", text)
        cats = list(dict.fromkeys(found))  # dedupe, preserve order
        if cats:
            return {
                "rule_type": "tax_category_validation",
                "field":      "tax_category",
                "operation":  "in",
                "value":      cats,
            }
    return None


def try_conditional_required(text: str) -> Optional[dict]:
    """
    Patterns:
      'If tax category is E, tax exemption reason is required'
      'If X is Y, Z is required'
    """
    m = re.search(
        r"if\s+([\w\s]+?)\s+is\s+([\w]+),\s*([\w\s]+?)\s+is required",
        text, re.IGNORECASE
    )
    if m:
        cond_field = resolve_field(m.group(1).strip())
        cond_value = m.group(2).strip()
        req_field  = resolve_field(m.group(3).strip())
        if cond_field and req_field:
            return {
                "rule_type":       "conditional_required_field",
                "condition_field":  cond_field,
                "condition_value":  cond_value,
                "required_field":   req_field,
                "operation":        "conditional_required",
            }
    return None


def try_duplicate_check(text: str) -> Optional[dict]:
    """
    Patterns:
      'Invoice ID must be unique'
      'X must not be duplicated'
    """
    text_l = text.lower()
    if "unique" in text_l or "must not be duplicated" in text_l:
        field_match = re.match(r"([\w\s]+?)\s+must", text, re.IGNORECASE)
        if field_match:
            field = resolve_field(field_match.group(1).strip())
            if field:
                return {
                    "rule_type": "duplicate_field_check",
                    "field":      field,
                    "operation":  "unique",
                }
    return None


# ─── Main parser ──────────────────────────────────────────────────────────────

HANDLERS = [
    try_amount_calculation,
    try_required_field,
    try_date_validation,
    try_numeric_comparison,
    try_currency_consistency,
    try_tax_category_validation,
    try_conditional_required,
    try_duplicate_check,
]


def parse_rule(rule_text: str) -> dict:
    """
    Try each handler in order. Return the first match.
    Falls back to an 'unknown' object if nothing matches.
    """
    for handler in HANDLERS:
        result = handler(rule_text)
        if result:
            return result

    # Fallback — unknown rule
    return {
        "rule_type": "unknown",
        "raw_text":   rule_text,
        "operation":  None,
    }


# ─── Batch parse from rules file ─────────────────────────────────────────────

def parse_rules_file(path: str) -> list[dict]:
    """Read rules_train.txt or rules_test.txt and parse all rules."""
    rules = []
    current = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                if current:
                    parsed = parse_rule(current.get("rule_text", ""))
                    parsed["rule_id"]  = current.get("rule_id")
                    parsed["severity"] = current.get("severity")
                    parsed["expected_error_message"] = current.get("expected_error_message")
                    rules.append(parsed)
                    current = {}
                continue
            if ": " in line:
                key, val = line.split(": ", 1)
                current[key.strip()] = val.strip()
    # catch last rule if file doesn't end with blank line
    if current:
        parsed = parse_rule(current.get("rule_text", ""))
        parsed["rule_id"]  = current.get("rule_id")
        parsed["severity"] = current.get("severity")
        parsed["expected_error_message"] = current.get("expected_error_message")
        rules.append(parsed)
    return rules


# ─── Quick self-test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_sentences = [
        "Tax amount must be exactly 18% of taxable amount",
        "Payable amount must equal taxable amount plus tax amount",
        "Seller name is required",
        "Invoice must contain an invoice ID",
        "Issue date cannot be in the future",
        "Issue date must be a valid calendar date",
        "Taxable amount must be greater than zero",
        "Tax amount must not be negative",
        "Currency code must be one of USD, EUR, GBP, INR, or AED",
        "All line items must use the same currency as the invoice",
        "Tax category must be S, Z, E, or AE",
        "If tax category is E, tax exemption reason is required",
        "If tax category is AE, buyer VAT number is required",
        "Invoice ID must be unique",
    ]

    print("=" * 60)
    print("RULE PARSER — SELF TEST")
    print("=" * 60)
    passed = 0
    for sentence in test_sentences:
        result = parse_rule(sentence)
        status = "✅" if result["rule_type"] != "unknown" else "❌ UNKNOWN"
        print(f"\n{status}")
        print(f"  INPUT : {sentence}")
        print(f"  OUTPUT: {result}")
        if result["rule_type"] != "unknown":
            passed += 1

    print(f"\n{'='*60}")
    print(f"Result: {passed}/{len(test_sentences)} rules parsed successfully")
    print(f"{'='*60}")
