"""
evaluator.py - Integration layer between main.py and Steve's executor.
Updated to call Steve's standalone functions.
"""

from typing import List, Optional, Tuple
import rule_parser
import xml_reader
import executor

def evaluate_one(rule_text: str, xml_content: str, rule_id: Optional[int] = None) -> dict:
    """Validate a single rule text against a single XML string."""
    # 1. Parse rule
    parsed = rule_parser.parse_rule(rule_text)
    
    # 2. Extract fields
    invoice_data = xml_reader.parse_invoice_xml(xml_content)
    if "_parse_error" in invoice_data:
        return {
            "rule_id": rule_id,
            "rule_text": rule_text,
            "status": "ERROR",
            "message": f"XML Parse Error: {invoice_data['_parse_error']}",
            "rule_type": parsed.get("rule_type")
        }

    # 3. Execute
    # Note: Steve's executor returns a dict: {status, rule_type, field, message}
    result = executor.execute_rule(parsed, invoice_data)
    
    # 4. Format for API
    return {
        "rule_id": rule_id,
        "rule_text": rule_text,
        "rule_type": result.get("rule_type"),
        "status": result.get("status"),
        "message": result.get("message"),
        "field": result.get("field")
    }

def evaluate_batch(rules: List[dict], xml_content: str) -> dict:
    """Evaluate multiple rules against one XML."""
    invoice_data = xml_reader.parse_invoice_xml(xml_content)
    
    results = []
    passed = 0
    failed = 0
    
    for r in rules:
        rule_text = r.get("rule_text")
        rule_id = r.get("id")
        
        parsed = rule_parser.parse_rule(rule_text)
        res = executor.execute_rule(parsed, invoice_data)
        
        item = {
            "rule_id": rule_id,
            "rule_text": rule_text,
            "rule_type": res.get("rule_type"),
            "status": res.get("status"),
            "message": res.get("message"),
            "field": res.get("field")
        }
        results.append(item)
        if res.get("status") == "PASS": passed += 1
        elif res.get("status") == "FAIL": failed += 1

    return {
        "invoice_id": str(invoice_data.get("invoice_id", "unknown")),
        "summary": {"total": len(results), "passed": passed, "failed": failed},
        "results": results
    }
