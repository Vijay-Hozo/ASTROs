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
    """Field must exist and not be empty/None."""
    field     = rule.get("field")
    rule_type = rule.get("rule_type")
    value     = _get(invoice, field)

    if value is None or str(value).strip() == "":
        return _fail(rule_type, field, f"Required field '{field}' is missing or empty")
    return _pass(rule_type, field, f"'{field}' is present")


def _check_amount_calculation(rule: dict, invoice: dict) -> dict:
    """
    Supports:
      - percentage: field == base_field * (value / 100)
      - sum:        field == base_field + add_field
    Tolerance: 0.02 (2 paise / cents rounding)
    """
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
    """
    Supports:
      - not_future: issue_date must not be after today
      - valid_date: issue_date must be parseable
    """
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
    """
    Supports: gt, gte, lt, lte, gte_zero, lte_zero
    """
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
    """
    Supports:
      - in:                    currency_code must be in allowed list
      - matches_invoice_currency: line item currencies match invoice
    """
    field     = rule.get("field")
    rule_type = rule.get("rule_type")
    operation = rule.get("operation")

    if operation == "in":
        allowed  = rule.get("value", [])
        currency = _get(invoice, "currency_code")
        if currency is None:
            return _fail(rule_type, field, "Currency code is missing")
        if currency.upper() not in [c.upper() for c in allowed]:
            return _fail(rule_type, field,
                f"Currency '{currency}' not in allowed list: {allowed}")
        return _pass(rule_type, field, f"Currency '{currency}' is valid")

    elif operation == "matches_invoice_currency":
        invoice_currency = _get(invoice, "currency_code")
        line_items       = invoice.get("line_items", [])
        mismatches       = [
            item.get("currency") for item in line_items
            if item.get("currency") and
               item.get("currency", "").upper() != (invoice_currency or "").upper()
        ]
        if mismatches:
            return _fail(rule_type, field,
                f"Line item currencies {mismatches} don't match invoice currency '{invoice_currency}'")
        return _pass(rule_type, field, "All line item currencies match invoice currency")

    return _fail(rule_type, field, f"Unknown currency operation: {operation}")


def _check_tax_category(rule: dict, invoice: dict) -> dict:
    """Tax category must be in allowed list."""
    field     = rule.get("field")
    rule_type = rule.get("rule_type")
    allowed   = rule.get("value", [])

    tax_cat = _get(invoice, "tax_category")
    if tax_cat is None:
        return _fail(rule_type, field, "Tax category is missing")
    if tax_cat.upper() not in [c.upper() for c in allowed]:
        return _fail(rule_type, field,
            f"Tax category '{tax_cat}' is invalid — allowed: {allowed}")
    return _pass(rule_type, field, f"Tax category '{tax_cat}' is valid")


def _check_conditional_required(rule: dict, invoice: dict) -> dict:
    """If condition_field == condition_value, then required_field must be present."""
    rule_type     = rule.get("rule_type")
    cond_field    = rule.get("condition_field")
    cond_value    = rule.get("condition_value", "")
    req_field     = rule.get("required_field")

    actual_cond = _get(invoice, cond_field)
    if actual_cond is None:
        return _pass(rule_type, req_field,
            f"Condition field '{cond_field}' not present — rule skipped")

    if str(actual_cond).upper() == str(cond_value).upper():
        req_val = _get(invoice, req_field)
        if req_val is None or str(req_val).strip() == "":
            return _fail(rule_type, req_field,
                f"'{req_field}' is required when '{cond_field}' is '{cond_value}' — but it is missing")
        return _pass(rule_type, req_field,
            f"'{req_field}' is present as required when '{cond_field}' = '{cond_value}'")

    return _pass(rule_type, req_field,
        f"Condition not met ('{cond_field}' = '{actual_cond}') — rule skipped")


def _check_duplicate(rule: dict, invoice: dict, all_invoice_ids: list = []) -> dict:
    """Invoice ID must be unique across all loaded invoices."""
    field     = rule.get("field")
    rule_type = rule.get("rule_type")

    value = _get(invoice, field)
    if value is None:
        return _fail(rule_type, field, f"'{field}' is missing — cannot check uniqueness")

    occurrences = all_invoice_ids.count(str(value))
    if occurrences > 1:
        return _fail(rule_type, field,
            f"'{field}' = '{value}' appears {occurrences} times — must be unique")
    return _pass(rule_type, field, f"'{field}' = '{value}' is unique")


def _check_unknown(rule: dict, invoice: dict) -> dict:
    return _result("SKIP", "unknown", None,
        f"Rule type not recognised: {rule.get('raw_text', 'N/A')}")


# ─── Batch executor ───────────────────────────────────────────────────────────

def execute_all_rules(rules: list, invoice: dict, all_invoice_ids: list = []) -> dict:
    """
    Run all rules against one invoice.
    Returns summary + per-rule results.
    """
    results = []
    for rule in rules:
        res = execute_rule(rule, invoice, all_invoice_ids)
        res["rule_id"]   = rule.get("rule_id")
        res["rule_text"] = rule.get("rule_text", "")
        results.append(res)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    return {
        "invoice_id": invoice.get("invoice_id", "unknown"),
        "summary": {
            "total":  len(results),
            "passed": passed,
            "failed": failed,
        },
        "results": results,
    }


# ─── Self test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from rule_parser import parse_rule
    from xml_reader  import parse_invoice_xml

    valid_xml = """
    <Invoice>
      <invoice_id>INV-0001</invoice_id>
      <issue_date>2026-04-15</issue_date>
      <seller_name>Seller Corp</seller_name>
      <buyer_name>Buyer Ltd</buyer_name>
      <currency_code>USD</currency_code>
      <taxable_amount>10000.00</taxable_amount>
      <tax_amount>1800.00</tax_amount>
      <payable_amount>11800.00</payable_amount>
      <tax_category>S</tax_category>
      <line_items>
        <item>
          <description>Laptop</description>
          <quantity>2</quantity>
          <unit_price>5000</unit_price>
          <line_total>10000</line_total>
        </item>
      </line_items>
    </Invoice>
    """

    invalid_xml = """
    <Invoice>
      <invoice_id></invoice_id>
      <issue_date>2027-12-01</issue_date>
      <seller_name></seller_name>
      <currency_code>XYZ</currency_code>
      <taxable_amount>5000.00</taxable_amount>
      <tax_amount>2500.00</tax_amount>
      <payable_amount>8000.00</payable_amount>
      <tax_category>E</tax_category>
    </Invoice>
    """

    test_rules = [
        "Tax amount must be exactly 18% of taxable amount",
        "Payable amount must equal taxable amount plus tax amount",
        "Seller name is required",
        "Invoice ID must be unique",
        "Issue date cannot be in the future",
        "Currency code must be one of USD, EUR, GBP, INR, or AED",
        "Tax category must be S, Z, E, or AE",
        "If tax category is E, tax exemption reason is required",
        "Taxable amount must be greater than zero",
    ]

    parsed_rules = [parse_rule(r) for r in test_rules]
    for i, r in enumerate(parsed_rules):
        r["rule_id"]   = f"R{i+1:03d}"
        r["rule_text"] = test_rules[i]

    print("=" * 60)
    print("EXECUTOR — VALID INVOICE")
    print("=" * 60)
    invoice_valid = parse_invoice_xml(valid_xml)
    out = execute_all_rules(parsed_rules, invoice_valid, ["INV-0001"])
    print(f"Summary: {out['summary']}")
    for r in out["results"]:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} [{r['rule_type']:<30}] {r['message']}")

    print("\n" + "=" * 60)
    print("EXECUTOR — INVALID INVOICE")
    print("=" * 60)
    invoice_invalid = parse_invoice_xml(invalid_xml)
    out2 = execute_all_rules(parsed_rules, invoice_invalid, ["INV-0001"])
    print(f"Summary: {out2['summary']}")
    for r in out2["results"]:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} [{r['rule_type']:<30}] {r['message']}")