import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
from lxml import etree
from tag_registry import resolve_tag, register_resolved_tag, CANONICAL_FIELDS
from main import extract_field_tokens, generate_skip_xslt
from xslt_templates import build_xslt

def run_tests():
    print("=" * 80)
    print("TESTING XML TAG REGISTRY & NORMALIZATION SYSTEM (FIX 1-5)")
    print("=" * 80)

    # 1. Test Registry Mappings
    print("\n[TEST 1] Registry resolve_tag & register_resolved_tag")
    
    # 1.1 Direct canonical matches
    canon, conf, warns = resolve_tag("tax_amount")
    assert canon == "tax_amount", f"Expected tax_amount, got {canon}"
    assert conf == 1.0, f"Expected 1.0 confidence, got {conf}"
    print("  [PASS] Direct canonical match")

    # 1.2 Case-insensitive matches
    canon, conf, warns = resolve_tag("TAX_AMOUNT")
    assert canon == "tax_amount", f"Expected tax_amount, got {canon}"
    assert conf == 0.9, f"Expected 0.9, got {conf}"
    print("  [PASS] Case-insensitive match")

    # 1.3 Synonym matches
    canon, conf, warns = resolve_tag("taxable_amt")
    assert canon == "taxable_amount", f"Expected taxable_amount, got {canon}"
    assert conf == 1.0, f"Expected 1.0, got {conf}"
    print("  [PASS] Synonym mapping match")

    # 1.4 Levenshtein distance fallback
    canon, conf, warns = resolve_tag("taxableamount")
    assert canon == "taxable_amount", f"Expected taxable_amount, got {canon}"
    assert conf == 0.8, f"Expected 0.8, got {conf}"
    print("  [PASS] Levenshtein distance fallback match")

    # 1.5 Dynamic custom mapping registration
    register_resolved_tag("salary", "payable_amount")
    canon, conf, warns = resolve_tag("salary")
    assert canon == "payable_amount", f"Expected payable_amount, got {canon}"
    assert conf == 1.0, f"Expected 1.0, got {conf}"
    print("  [PASS] Dynamic custom mapping registration")

    # 2. Test Rule Extraction & Tokens
    print("\n[TEST 2] Token extraction & boundary validation")
    rule = "TotalTax must be greater than taxable_amount"
    tokens = extract_field_tokens(rule)
    assert "TotalTax" in tokens, f"Expected TotalTax in {tokens}"
    assert "taxable_amount" in tokens, f"Expected taxable_amount in {tokens}"
    print("  [PASS] Token extraction is fully correct")

    # 3. Test Skipped XSLT Structure
    print("\n[TEST 3] Rich skipped/unsupported XSLT generation & validation")
    unsupported_rule = {
        "rule_type": "unsupported",
        "warnings": [
            "Unrecognized field: 'salary'",
            "Closest supported field: 'payable_amount'",
            "Suggested rewrite: 'payable_amount must be greater than 0'"
        ]
    }
    
    xslt_content = build_xslt(unsupported_rule)
    print("Generated XSLT output:")
    print("-" * 50)
    print(xslt_content.strip())
    print("-" * 50)

    # Compile the XSLT using lxml to ensure it is 100% valid XML and XSLT syntax
    try:
        parser = etree.XMLParser()
        xslt_tree = etree.XML(xslt_content.encode("utf-8"), parser=parser)
        transform = etree.XSLT(xslt_tree)
        print("  [PASS] XSLT compiles successfully with no syntax errors")
    except Exception as e:
        print(f"  [FAIL] XSLT compilation error: {e}")
        return False

    # Execute XSLT validation against a mock invoice to test runtime compliance
    mock_invoice = etree.XML("<Invoice><salary>1000</salary></Invoice>")
    try:
        result_tree = transform(mock_invoice)
        result_str = str(result_tree)
        print("Executed validation result:")
        print(result_str.strip())
        
        # Verify status is UNSUPPORTED and message/suggestion are populated
        assert "<status>UNSUPPORTED</status>" in result_str, "Expected status UNSUPPORTED"
        assert "<action>SKIP</action>" in result_str, "Expected action SKIP"
        assert "Unrecognized field: 'salary'" in result_str, "Expected message content"
        assert "Suggested rewrite:" in result_str, "Expected suggestion content"
        print("  [PASS] XSLT executes correctly and returns expected skip structure")
    except Exception as e:
        print(f"  [FAIL] XSLT execution failed: {e}")
        return False

    print("\n" + "=" * 80)
    print("ALL NEW SYSTEM TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
