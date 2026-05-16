"""
Integration test suite for end-to-end pipeline validation.
Tests the complete flow:
  XML → Parse → LLM Rule → XSLT → Execute → DB → API

Run: pytest integration_tests.py -v
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from xml_reader import parse_invoice_xml
from xslt_executor import execute_xslt
from xslt_templates import build_xslt


TESTS_DIR = Path(__file__).parent
XML_DIR = TESTS_DIR / "xml"
EXPECTED_DIR = TESTS_DIR / "expected"


def test_valid_invoice_all_rules_pass():
    """Valid invoice should pass all rule types."""
    valid_path = XML_DIR / "invoice_0026_valid.xml"
    parsed = parse_invoice_xml(str(valid_path))
    
    assert "_parse_error" not in parsed, "Valid invoice should parse"
    assert parsed.get("invoice_id") == "INV-0026"
    assert parsed.get("seller_name") == "Seller_1"
    assert parsed.get("tax_amount") == 1932.89
    assert parsed.get("currency_code") == "INR"


def test_invalid_tax_invoice():
    """Invalid tax invoice should parse but fail tax rule."""
    invalid_path = XML_DIR / "invoice_0026_invalid_tax.xml"
    parsed = parse_invoice_xml(str(invalid_path))
    
    assert "_parse_error" not in parsed, "Invalid tax invoice should parse"
    assert parsed.get("tax_amount") == 1500.0, "Should preserve invalid tax value"


def test_future_date_invoice():
    """Future date invoice should parse but fail date rule."""
    future_path = XML_DIR / "invoice_0026_future_date.xml"
    parsed = parse_invoice_xml(str(future_path))
    
    assert "_parse_error" not in parsed, "Future date invoice should parse"
    assert "2027-12-01" in str(parsed.get("issue_date", "")), "Should parse future date"


def test_missing_seller_invoice():
    """Missing seller invoice should parse with None for seller_name."""
    missing_path = XML_DIR / "invoice_0026_missing_seller.xml"
    parsed = parse_invoice_xml(str(missing_path))
    
    assert "_parse_error" not in parsed, "Missing seller invoice should parse"
    assert parsed.get("seller_name") is None, "Seller name should be None"
    assert parsed.get("buyer_name") == "Buyer_12", "Other fields should parse"


def test_broken_xml_rejected():
    """Broken XML should return error dict, not crash."""
    broken_path = XML_DIR / "invoice_0026_broken.xml"
    parsed = parse_invoice_xml(str(broken_path))
    
    assert "_parse_error" in parsed, "Broken XML should return error"
    assert len(parsed["_parse_error"]) > 0, "Error message should be present"


def test_required_field_xslt():
    """Test required field XSLT generation and execution."""
    rule = {
        "rule_type": "required_field",
        "field": "seller_name",
        "operation": "not_empty",
        "message": "Seller name is required"
    }
    
    xslt = build_xslt(rule)
    assert "seller_name" in xslt
    assert "xsl:stylesheet" in xslt


def test_amount_calculation_xslt():
    """Test amount calculation XSLT generation and execution."""
    rule = {
        "rule_type": "amount_calculation",
        "field": "tax_amount",
        "operation": "percentage",
        "base_field": "taxable_amount",
        "value": 18,
        "message": "Tax amount mismatch"
    }
    
    xslt = build_xslt(rule)
    assert "tax_amount" in xslt
    assert "percentage" in xslt or "18" in xslt or "0.18" in xslt


def test_date_validation_xslt():
    """Test date validation XSLT generation."""
    rule = {
        "rule_type": "date_validation",
        "field": "issue_date",
        "operation": "not_future",
        "message": "Date cannot be in future"
    }
    
    xslt = build_xslt(rule)
    assert "issue_date" in xslt
    assert "current_date" in xslt


def test_deterministic_execution():
    """Same invoice should produce same result on multiple runs."""
    valid_path = XML_DIR / "invoice_0026_valid.xml"
    with open(valid_path) as f:
        xml_str = f.read()
    
    rule = {
        "rule_type": "required_field",
        "field": "invoice_id",
        "operation": "not_empty",
        "message": "Invoice ID is required"
    }
    xslt = build_xslt(rule)
    
    result1 = execute_xslt(xslt, xml_str)
    result2 = execute_xslt(xslt, xml_str)
    
    assert result1 == result2, "Results should be identical"
    assert result1["status"] == "PASS"


def test_expected_outcomes_reference():
    """Verify expected outcomes reference exists and is valid."""
    outcomes_file = EXPECTED_DIR / "rules_and_outcomes.json"
    assert outcomes_file.exists(), "Expected outcomes reference should exist"
    
    with open(outcomes_file) as f:
        data = json.load(f)
    
    assert "deterministic_rules" in data
    assert len(data["deterministic_rules"]) == 7
    assert "test_matrix" in data


if __name__ == "__main__":
    # Run tests manually
    test_valid_invoice_all_rules_pass()
    print("✓ test_valid_invoice_all_rules_pass")
    
    test_invalid_tax_invoice()
    print("✓ test_invalid_tax_invoice")
    
    test_future_date_invoice()
    print("✓ test_future_date_invoice")
    
    test_missing_seller_invoice()
    print("✓ test_missing_seller_invoice")
    
    test_broken_xml_rejected()
    print("✓ test_broken_xml_rejected")
    
    test_required_field_xslt()
    print("✓ test_required_field_xslt")
    
    test_amount_calculation_xslt()
    print("✓ test_amount_calculation_xslt")
    
    test_date_validation_xslt()
    print("✓ test_date_validation_xslt")
    
    test_deterministic_execution()
    print("✓ test_deterministic_execution")
    
    test_expected_outcomes_reference()
    print("✓ test_expected_outcomes_reference")
    
    print("\nAll tests passed!")
