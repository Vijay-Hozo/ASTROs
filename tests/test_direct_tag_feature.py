import sys
import os
import io
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from fastapi import UploadFile
from main import upload_sample_xml, resolve_tag_endpoint
from xml_reader import extract_xml_tags
from xslt_templates import build_xslt, generate_direct_tag_xslt
from tag_registry import resolve_tag, register_resolved_tag

def run_feature_tests():
    print("=" * 80)
    print("TESTING DIRECT TAGS & DYNAMIC XML EXTRACTOR FEATURE (STEPS 1-9)")
    print("=" * 80)

    # 1. Test Step 1: XML tag extractor
    print("\n[TEST 1] Testing xml_reader.extract_xml_tags")
    sample_xml = """<Invoice>
        <invoice_id>INV-999</invoice_id>
        <issue_date>2026-05-17</issue_date>
        <payable_amount>5000.00</payable_amount>
        <freight_charges>150.00</freight_charges>
        <seller_ph>+919876543210</seller_ph>
    </Invoice>"""

    extracted = extract_xml_tags(sample_xml)
    assert extracted["total"] == 5, f"Expected 5 tags, got {extracted['total']}"
    
    # Check known vs unknown
    known_tags = {t["tag"] for t in extracted["known_tags"]}
    unknown_tags = {t["tag"] for t in extracted["unknown_tags"]}
    
    assert "invoice_id" in known_tags, "invoice_id should be in known tags"
    assert "payable_amount" in known_tags, "payable_amount should be in known tags"
    assert "seller_ph" in unknown_tags, "seller_ph should be in unknown tags"
    assert "freight_charges" in unknown_tags, "freight_charges should be in unknown tags"
    
    # Check type inference
    freight_info = next(t for t in extracted["tags"] if t["tag"] == "freight_charges")
    assert freight_info["inferred_type"] == "numeric", f"Expected numeric, got {freight_info['inferred_type']}"
    assert freight_info["xpath"] == "/Invoice/freight_charges"
    print("  [PASS] Deterministic XML tag extraction & type inference")

    # 2. Test Step 2: Upload and Resolve endpoints directly
    print("\n[TEST 2] Testing upload_sample_xml and resolve_tag_endpoint")
    
    # Mock UploadFile
    mock_file = UploadFile(
        filename="sample.xml",
        file=io.BytesIO(sample_xml.encode("utf-8"))
    )
    
    data = asyncio.run(upload_sample_xml(mock_file))
    assert data["total"] == 5
    assert len(data["known_tags"]) == 3
    assert len(data["unknown_tags"]) == 2
    print("  [PASS] upload_sample_xml endpoint parsed file successfully")

    # Resolve an unknown tag
    resolve_payload = {
        "raw_tag": "seller_ph",
        "canonical_field": "purchase_order"
    }
    resolve_res = asyncio.run(resolve_tag_endpoint(resolve_payload))
    assert resolve_res["registered"] is True
    
    # Verify the registry learned it
    from tag_registry import TAG_REGISTRY
    assert TAG_REGISTRY["seller_ph"] == "purchase_order"
    print("  [PASS] resolve_tag_endpoint registered mapping successfully")

    # Revert resolve mapping to clean state
    TAG_REGISTRY["seller_ph"] = None

    # 3. Test Step 9: evaluator.py direct tag routing & Step 4: XSLT generation
    print("\n[TEST 3] Testing generate_direct_tag_xslt & build_xslt routing")
    
    # Test presence check
    presence_rule = {
        "rule_type": "presence",
        "field": "freight_charges",
        "is_direct_tag": True,
        "xpath": "/Invoice/freight_charges"
    }
    
    xslt_presence = build_xslt(presence_rule)
    assert "<status>FAIL</status>" in xslt_presence
    assert "<message>freight_charges must be present</message>" in xslt_presence
    print("  [PASS] Presence XSLT for direct tag generated successfully")

    # Test compare check
    compare_rule = {
        "rule_type": "compare",
        "field": "freight_charges",
        "is_direct_tag": True,
        "xpath": "/Invoice/freight_charges",
        "operator": "gt",
        "value": 100
    }
    
    xslt_compare = build_xslt(compare_rule)
    assert "<status>FAIL</status>" in xslt_compare
    assert "freight_charges must be gt 100" in xslt_compare
    print("  [PASS] Comparison XSLT for direct tag generated successfully")

    # 4. Compile and Run using lxml or standard tools if possible
    print("\n[TEST 4] Compiling and Executing generated XSLT")
    try:
        from lxml import etree
        # Valid case: freight_charges = 150 > 100
        invoice_element = etree.XML(sample_xml.encode('utf-8'))
        
        xslt_tree = etree.XML(xslt_compare.encode('utf-8'))
        transform = etree.XSLT(xslt_tree)
        result = transform(invoice_element)
        result_str = str(result)
        
        assert "<status>PASS</status>" in result_str, f"Expected PASS, got: {result_str}"
        print("  [PASS] XSLT validated direct XML tag correctly (PASS status)")
        
        # Invalid case: freight_charges = 50 < 100
        bad_xml = """<Invoice>
            <freight_charges>50.00</freight_charges>
        </Invoice>"""
        bad_element = etree.XML(bad_xml.encode('utf-8'))
        result_bad = transform(bad_element)
        result_bad_str = str(result_bad)
        
        assert "<status>FAIL</status>" in result_bad_str
        assert "freight_charges must be gt 100" in result_bad_str
        print("  [PASS] XSLT validated direct XML tag correctly (FAIL status)")
    except ImportError:
        print("  [SKIP] lxml not installed in environment, skipping compilation test")

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED SUCCESSFULLY! DIRECT TAG FEATURE IS STABLE & ROBUST.")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = run_feature_tests()
    sys.exit(0 if success else 1)
