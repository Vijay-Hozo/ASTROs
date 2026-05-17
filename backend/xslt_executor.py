"""
xslt_executor.py — runs a generated XSLT string against an XML invoice string.
Uses lxml with defusedxml safeguards. Returns structured PASS/FAIL result.
"""

from datetime import date
from lxml import etree
try:
    from defusedxml import lxml as defused_lxml
except ImportError:
    defused_lxml = None


def execute_xslt(xslt_str: str, xml_str: str, rule_text: str = "") -> dict:
    """
    Runs XSLT against XML invoice.
    Injects today's date as `current_date` param for date validation rules.
    
    Uses defusedxml safeguards where available to prevent XXE attacks.
    Returns: { status, field, message, rule_text }
    """
    try:
        xslt_doc  = etree.fromstring(xslt_str.encode())
        transform = etree.XSLT(xslt_doc)
    except etree.XMLSyntaxError as e:
        return {
            "status":    "ERROR",
            "field":     None,
            "message":   f"Invalid XSLT generated: {str(e)[:80]}",
            "rule_text": rule_text,
        }
    except Exception as e:
        return {
            "status":    "ERROR",
            "field":     None,
            "message":   f"XSLT compilation failed: {str(e)[:80]}",
            "rule_text": rule_text,
        }

    try:
        # Use standard lxml parser without resolving entities to prevent XXE
        parser = etree.XMLParser(resolve_entities=False)
        xml_doc = etree.fromstring(xml_str.encode(), parser=parser)
    except etree.XMLSyntaxError as e:
        return {
            "status":    "ERROR",
            "field":     None,
            "message":   f"Invalid XML invoice: {str(e)[:80]}",
            "rule_text": rule_text,
        }
    except Exception as e:
        return {
            "status":    "ERROR",
            "field":     None,
            "message":   f"XML parsing failed: {str(e)[:80]}",
            "rule_text": rule_text,
        }

    # Inject today's ISO date so XSLT 1.0 date comparisons work correctly.
    today = date.today().isoformat()
    try:
        result_tree = transform(xml_doc, current_date=f"'{today}'")
    except Exception as e:
        return {
            "status":    "ERROR",
            "field":     None,
            "message":   f"XSLT execution failed: {str(e)[:80]}",
            "rule_text": rule_text,
        }

    result_root = result_tree.getroot()

    if result_root is None:
        return {
            "status":    "ERROR",
            "field":     None,
            "message":   "XSLT produced no output",
            "rule_text": rule_text,
        }

    # Extract status, message, field from result XML
    def get_text(tag: str) -> str:
        el = result_root.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    status  = get_text("status")
    message = get_text("message")
    field   = get_text("field")

    return {
        "status":    status,   # PASS / FAIL / SKIP / ERROR
        "field":     field or None,
        "message":   message,
        "rule_text": rule_text,
    }


def execute_workspace_xslt(xslt_str: str, xml_str: str, xslt_name: str = "") -> dict:
    """
    Run one combined workspace XSLT against an XML invoice and return all rule results.
    """
    try:
        xslt_doc = etree.fromstring(xslt_str.encode())
        transform = etree.XSLT(xslt_doc)
    except etree.XMLSyntaxError as e:
        return {
            "invoice_id": "unknown",
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
            "results": [],
            "error": f"Invalid XSLT generated: {str(e)[:80]}",
            "xslt_name": xslt_name,
        }
    except Exception as e:
        return {
            "invoice_id": "unknown",
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
            "results": [],
            "error": f"XSLT compilation failed: {str(e)[:80]}",
            "xslt_name": xslt_name,
        }

    try:
        parser = etree.XMLParser(resolve_entities=False)
        xml_doc = etree.fromstring(xml_str.encode(), parser=parser)
    except etree.XMLSyntaxError as e:
        return {
            "invoice_id": "unknown",
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
            "results": [],
            "error": f"Invalid XML invoice: {str(e)[:80]}",
            "xslt_name": xslt_name,
        }
    except Exception as e:
        return {
            "invoice_id": "unknown",
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
            "results": [],
            "error": f"XML parsing failed: {str(e)[:80]}",
            "xslt_name": xslt_name,
        }

    today = date.today().isoformat()
    try:
        result_tree = transform(xml_doc, current_date=f"'{today}'")
    except Exception as e:
        return {
            "invoice_id": "unknown",
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
            "results": [],
            "error": f"XSLT execution failed: {str(e)[:80]}",
            "xslt_name": xslt_name,
        }

    result_root = result_tree.getroot()
    if result_root is None:
        return {
            "invoice_id": "unknown",
            "summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0},
            "results": [],
            "error": "XSLT produced no output",
            "xslt_name": xslt_name,
        }

    def text_or_none(node, tag: str):
        el = node.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    rule_results = result_root.findall(".//rule_result")
    results = []
    for rule_node in rule_results:
        status = text_or_none(rule_node, "status")
        message = text_or_none(rule_node, "message")
        field = text_or_none(rule_node, "field")
        rule_type = rule_node.get("rule_type")
        label = rule_type or xslt_name or "workspace rule"
        if field and field not in label:
            label = f"{label}:{field}"
        results.append(
            {
                "status": status or "ERROR",
                "field": field or None,
                "message": message,
                "rule_text": label,
                "rule_type": rule_type,
                "rule_id": rule_node.get("order"),
            }
        )

    if not results:
        status = text_or_none(result_root, "status")
        message = text_or_none(result_root, "message")
        field = text_or_none(result_root, "field")
        results.append(
            {
                "status": status or "ERROR",
                "field": field or None,
                "message": message,
                "rule_text": xslt_name or "workspace rule",
                "rule_type": None,
                "rule_id": None,
            }
        )

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    try:
        inv_id_el = xml_doc.find("invoice_id")
        invoice_id = inv_id_el.text.strip() if inv_id_el is not None and inv_id_el.text else "unknown"
    except Exception:
        invoice_id = "unknown"

    return {
        "invoice_id": invoice_id,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
        },
        "results": results,
        "xslt_name": xslt_name,
    }


def execute_all_rules(rules: list, xml_str: str) -> dict:
    """
    Run all rules (each with prebuilt XSLT) against one XML invoice.
    Each rule must have: { rule_id, rule_text, xslt, structured }

    Returns summary + per-rule results.
    """
    results = []

    for rule in rules:
        xslt_str  = rule.get("xslt", "")
        rule_text = rule.get("rule_text", "")
        rule_id   = rule.get("rule_id")
        rule_type = rule.get("structured", {}).get("rule_type")

        res = execute_xslt(xslt_str, xml_str, rule_text)
        res["rule_id"]   = rule_id
        res["rule_type"] = rule_type
        results.append(res)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    # Extract invoice_id from XML
    try:
        root       = etree.fromstring(xml_str.encode())
        inv_id_el  = root.find("invoice_id")
        invoice_id = inv_id_el.text.strip() if inv_id_el is not None else "unknown"
    except Exception:
        invoice_id = "unknown"

    return {
        "invoice_id": invoice_id,
        "summary": {
            "total":  len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
        },
        "results": results,
    }


# ─── Self test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from xslt_templates import build_xslt

    # Manually build rules without LLM for self test
    test_rules_structured = [
        {
            "rule_id":  "R001",
            "rule_text": "Tax amount must be exactly 18% of taxable amount",
            "structured": {
                "rule_type":  "amount_calculation",
                "field":      "tax_amount",
                "operation":  "percentage",
                "base_field": "taxable_amount",
                "value":      18,
                "message":    "Tax amount mismatch",
            },
        },
        {
            "rule_id":  "R002",
            "rule_text": "Seller name is required",
            "structured": {
                "rule_type": "required_field",
                "field":     "seller_name",
                "operation": "not_empty",
                "message":   "Seller name is missing",
            },
        },
        {
            "rule_id":  "R003",
            "rule_text": "Issue date cannot be in the future",
            "structured": {
                "rule_type": "date_validation",
                "field":     "issue_date",
                "operation": "not_future",
                "message":   "Issue date is in the future",
            },
        },
        {
            "rule_id":  "R004",
            "rule_text": "Currency code must be one of USD, EUR, GBP, INR, or AED",
            "structured": {
                "rule_type": "currency_consistency",
                "field":     "currency_code",
                "operation": "in",
                "value":     ["USD", "EUR", "GBP", "INR", "AED"],
                "message":   "Currency not in allowed list",
            },
        },
        {
            "rule_id":  "R005",
            "rule_text": "If tax category is E, tax exemption reason is required",
            "structured": {
                "rule_type":       "conditional_required_field",
                "field":           "tax_exemption_reason",
                "condition_field": "tax_category",
                "condition_value": "E",
                "required_field":  "tax_exemption_reason",
                "operation":       "conditional_required",
                "message":         "Tax exemption reason required when tax category is E",
            },
        },
    ]

    # Build XSLT for each
    for r in test_rules_structured:
        r["xslt"] = build_xslt(r["structured"])

    valid_xml = """<Invoice>
      <invoice_id>INV-0001</invoice_id>
      <issue_date>2026-04-15</issue_date>
      <seller_name>Seller Corp</seller_name>
      <buyer_name>Buyer Ltd</buyer_name>
      <currency_code>USD</currency_code>
      <taxable_amount>10000.00</taxable_amount>
      <tax_amount>1800.00</tax_amount>
      <payable_amount>11800.00</payable_amount>
      <tax_category>S</tax_category>
    </Invoice>"""

    invalid_xml = """<Invoice>
      <invoice_id></invoice_id>
      <issue_date>2027-12-01</issue_date>
      <seller_name></seller_name>
      <currency_code>XYZ</currency_code>
      <taxable_amount>5000.00</taxable_amount>
      <tax_amount>2500.00</tax_amount>
      <payable_amount>8000.00</payable_amount>
      <tax_category>E</tax_category>
    </Invoice>"""

    print("=" * 60)
    print("XSLT EXECUTOR — VALID INVOICE")
    print("=" * 60)
    out = execute_all_rules(test_rules_structured, valid_xml)
    print(f"Summary: {out['summary']}")
    for r in out["results"]:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} [{r['rule_type']:<30}] {r['message']}")

    print("\n" + "=" * 60)
    print("XSLT EXECUTOR — INVALID INVOICE")
    print("=" * 60)
    out2 = execute_all_rules(test_rules_structured, invalid_xml)
    print(f"Summary: {out2['summary']}")
    for r in out2["results"]:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} [{r['rule_type']:<30}] {r['message']}")
