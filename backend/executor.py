"""
Executor — runs a structured rule object against a parsed invoice dict.
Input:  structured rule (from rule_parser) + invoice dict (from xml_reader)
Output: { status: PASS/FAIL, message: str }
No LLM. Pure deterministic logic.
"""

from datetime import datetime
from typing import Optional


def execute_rule(rule: dict, invoice: dict, all_invoice_ids: list = []) -> dict:
    """
    Main entry point.
    Dispatches to the correct handler based on rule_type.
    Returns: { status, rule_type, field, message }
    """
    rule_type = rule.get("rule_type")

    handlers = {
        "required_field":           _check_required_field,
        "amount_calculation":       _check_amount_calculation,
        "date_validation":          _check_date_validation,
        "numeric_comparison":       _check_numeric_comparison,
        "currency_consistency":     _check_currency_consistency,
        "tax_category_validation":  _check_tax_category,
        "conditional_required_field": _check_conditional_required,
        "duplicate_field_check":    _check_duplicate,
        "unknown":                  _check_unknown,
    }

    handler = handlers.get(rule_type, _check_unknown)

    try:
        if rule_type == "duplicate_field_check":
            return handler(rule, invoice, all_invoice_ids)
        return handler(rule, invoice)
    except Exception as e:
        return _result("ERROR", rule_type, rule.get("field"), f"Executor error: {str(e)}")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _result(status: str, rule_type: str, field: Optional[str], message: str) -> dict:
    return {
        "status":    status,
        "rule_type": rule_type,
        "field":     field,
        "message":   message,
    }

def _pass(rule_type, field, message="Validation passed"):
    return _result("PASS", rule_type, field, message)

def _fail(rule_type, field, message):
    return _result("FAIL", rule_type, field, message)

def _get(invoice: dict, field: str):
    return invoice.get(field)


# ─── Handlers ─────────────────────────────────────────────────────────────────

def _check_required_field(rule: dict, invoice: dict) -> dict:
    field     = rule.get("field")
    rule_type = rule.get("rule_type")
    value     = _get(invoice, field)

    if value is None or str(value).strip() == "":
        return _fail(rule_type, field, f"Required field '{field}' is missing or empty")
    return _pass(rule_type, field, f"'{field}' is present")


def _check_amount_calculation(rule: dict, invoice: dict) -> dict:
    field     = rule.get("field")
    rule_type = rule.get("rule_type")
    operation = rule.get("operation")
    TOLERANCE = 0.02

    actual = _get(invoice, field)
    if actual is None:
        return _fail(rule_type, field, f"Field '{field}' is missing — cannot validate amount")

    if operation == "percentage":
        base_field = rule.get("base_field")
        rate       = rule.get("value")
        base_val   = _get(invoice, base_field)

        if base_val is None:
            return _fail(rule_type, field, f"Base field '{base_field}' missing")

        expected = round(float(base_val) * float(rate) / 100, 2)
        actual_f = round(float(actual), 2)

        if abs(actual_f - expected) > TOLERANCE:
            return _fail(rule_type, field,
                f"'{field}' mismatch — expected {expected} ({rate}% of {base_val}), found {actual_f}")
        return _pass(rule_type, field, f"'{field}' correctly calculated as {rate}% of '{base_field}'")

    elif operation == "sum":
        base_field = rule.get("base_field")
        add_field  = rule.get("add_field")
        base_val   = _get(invoice, base_field)
        add_val    = _get(invoice, add_field)

        if base_val is None or add_val is None:
            return _fail(rule_type, field, f"Cannot compute sum — '{base_field}' or '{add_field}' missing")

        expected = round(float(base_val) + float(add_val), 2)
        actual_f = round(float(actual), 2)

        if abs(actual_f - expected) > TOLERANCE:
            return _fail(rule_type, field,
                f"'{field}' mismatch — expected {expected} ({base_field} + {add_field}), found {actual_f}")
        return _pass(rule_type, field, f"'{field}' correctly equals '{base_field}' + '{add_field}'")

    return _fail(rule_type, field, f"Unknown amount operation: {operation}")


def _check_date_validation(rule: dict, invoice: dict) -> dict:
    field     = rule.get("field")
    rule_type = rule.get("rule_type")
    operation = rule.get("operation")

    raw_date  = _get(invoice, "issue_date_raw")
    parsed    = _get(invoice, "issue_date")

    if raw_date is None:
        return _fail(rule_type, field, "Issue date is missing")

    if operation == "valid_date":
        if parsed is None:
            return _fail(rule_type, field, f"Issue date '{raw_date}' is not a valid calendar date")
        return _pass(rule_type, field, f"Issue date '{raw_date}' is valid")

    elif operation == "not_future":
        if parsed is None:
            return _fail(rule_type, field, f"Issue date '{raw_date}' could not be parsed")
        if parsed > datetime.now():
            return _fail(rule_type, field,
                f"Issue date '{raw_date}' is in the future — invoices cannot be post-dated")
        return _pass(rule_type, field, f"Issue date '{raw_date}' is not in the future")

    return _fail(rule_type, field, f"Unknown date operation: {operation}")


def _check_numeric_comparison(rule: dict, invoice: dict) -> dict:
    field     = rule.get("field")
    rule_type = rule.get("rule_type")
    operation = rule.get("operation")
    threshold = float(rule.get("value", 0))

    value = _get(invoice, field)
    if value is None:
        return _fail(rule_type, field, f"Field '{field}' is missing — cannot compare")

    try:
        val = float(value)
    except (ValueError, TypeError):
        return _fail(rule_type, field, f"Field '{field}' is not a number: {value}")

    checks = {
        "gt":       (val > threshold,  f"must be greater than {threshold}"),
        "gte":      (val >= threshold, f"must be >= {threshold}"),
        "lt":       (val < threshold,  f"must be less than {threshold}"),
        "lte":      (val <= threshold, f"must be <= {threshold}"),
        "gte_zero": (val >= 0,         "must not be negative"),
        "lte_zero": (val <= 0,         "must be zero or less"),
    }

    if operation not in checks:
        return _fail(rule_type, field, f"Unknown numeric operation: {operation}")

    passed, desc = checks[operation]
    if not passed:
        return _fail(rule_type, field, f"'{field}' = {val} — {desc}")
    return _pass(rule_type, field, f"'{field}' = {val} passes numeric check")


def _check_currency_consistency(rule: dict, invoice: dict) -> dict:
    field     = rule.get("field")
    rule_type = rule.get("rule_type")
    operation = rule.get("operation")

    if operation == "in":
        allowed  = rule.get("value", [])
        currency = _get(invoice, "currency_code")
        if currency is None: return _fail(rule_type, field, "Currency code is missing")
        if currency.upper() not in [c.upper() for c in allowed]:
            return _fail(rule_type, field, f"Currency '{currency}' not in allowed list: {allowed}")
        return _pass(rule_type, field, f"Currency '{currency}' is valid")

    elif operation == "matches_invoice_currency":
        invoice_currency = _get(invoice, "currency_code")
        line_items       = invoice.get("line_items", [])
        mismatches       = [item.get("currency") for item in line_items if item.get("currency") and item.get("currency", "").upper() != (invoice_currency or "").upper()]
        if mismatches: return _fail(rule_type, field, f"Line item currencies mismatch")
        return _pass(rule_type, field, "All line item currencies match")
    return _fail(rule_type, field, f"Unknown currency operation")


def _check_tax_category(rule: dict, invoice: dict) -> dict:
    field, rule_type, allowed = rule.get("field"), rule.get("rule_type"), rule.get("value", [])
    tax_cat = _get(invoice, "tax_category")
    if tax_cat is None: return _fail(rule_type, field, "Tax category is missing")
    if tax_cat.upper() not in [c.upper() for c in allowed]: return _fail(rule_type, field, f"Tax category '{tax_cat}' invalid")
    return _pass(rule_type, field, f"Tax category valid")


def _check_conditional_required(rule: dict, invoice: dict) -> dict:
    rule_type, cf, cv, rf = rule.get("rule_type"), rule.get("condition_field"), rule.get("condition_value", ""), rule.get("required_field")
    actual_cond = _get(invoice, cf)
    if actual_cond is None: return _pass(rule_type, rf, "Condition field missing")
    if str(actual_cond).upper() == str(cv).upper():
        if not _get(invoice, rf): return _fail(rule_type, rf, f"'{rf}' required when '{cf}' is '{cv}'")
        return _pass(rule_type, rf, f"'{rf}' present as required")
    return _pass(rule_type, rf, "Condition not met")


def _check_duplicate(rule: dict, invoice: dict, all_invoice_ids: list = []) -> dict:
    field, rule_type, value = rule.get("field"), rule.get("rule_type"), _get(invoice, rule.get("field"))
    if value is None: return _fail(rule_type, field, "Missing field for uniqueness check")
    if all_invoice_ids.count(str(value)) > 1: return _fail(rule_type, field, f"Duplicate found: {value}")
    return _pass(rule_type, field, "Unique")

def _check_unknown(rule: dict, invoice: dict) -> dict:
    return _result("SKIP", "unknown", None, "Unknown rule type")
