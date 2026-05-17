"""
evaluator.py — Integration layer.
Uses llm_rule_parser → xslt_templates → xslt_executor pipeline.
"""

import json
from typing import Optional, List
from llm_rule_parser import parse_rule, parse_rule_and_build_xslt
from xslt_executor import execute_xslt, execute_all_rules
from xml_reader import parse_invoice_xml


def evaluate_one(rule_text: str, xml_content: str, rule_id: Optional[int] = None) -> dict:
    """
    Single rule + single XML → PASS/FAIL result.
    """
    # Check XML is valid first
    invoice = parse_invoice_xml(xml_content)
    if "_parse_error" in invoice:
        return {
            "rule_id":   rule_id,
            "rule_text": rule_text,
            "rule_type": None,
            "status":    "ERROR",
            "message":   f"XML parse error: {invoice['_parse_error']}",
            "field":     None,
        }

    # LLM parse → build XSLT → execute
    result   = parse_rule_and_build_xslt(rule_text)
    structured = result["structured"]
    xslt_str   = result["xslt"]

    res = execute_xslt(xslt_str, xml_content, rule_text)

    return {
        "rule_id":   rule_id,
        "rule_text": rule_text,
        "rule_type": structured.get("rule_type"),
        "status":    res.get("status"),
        "message":   res.get("message"),
        "field":     res.get("field"),
    }


def evaluate_batch(rules: List[dict], xml_content: str) -> dict:
    """
    Multiple rules (each with prebuilt xslt) against one XML.
    Each rule dict must have: { id, rule_text, parsed_json (JSON string with xslt key) }
    """
    invoice = parse_invoice_xml(xml_content)
    if "_parse_error" in invoice:
        return {
            "invoice_id": "unknown",
            "summary": {"total": 0, "passed": 0, "failed": 0},
            "results": [],
            "error": f"XML parse error: {invoice['_parse_error']}",
        }

    # Build rule list for xslt_executor
    rule_list = []
    for r in rules:
        parsed_json = r.get("parsed_json", "{}")
        if isinstance(parsed_json, str):
            try:
                parsed = json.loads(parsed_json)
            except Exception:
                parsed = {}
        else:
            parsed = parsed_json

        xslt = parsed.get("xslt")
        if not xslt:
            # No stored XSLT — build it now
            try:
                from xslt_templates import build_xslt
                xslt = build_xslt(parsed)
            except Exception:
                xslt = ""

        rule_list.append({
            "rule_id":    r.get("id"),
            "rule_text":  r.get("rule_text", ""),
            "xslt":       xslt,
            "structured": parsed,
        })

    out = execute_all_rules(rule_list, xml_content)

    # Normalise result keys for API response
    results = []
    for r in out["results"]:
        results.append({
            "rule_id":   r.get("rule_id"),
            "rule_text": r.get("rule_text", ""),
            "rule_type": r.get("rule_type"),
            "status":    r.get("status"),
            "message":   r.get("message"),
            "field":     r.get("field"),
        })

    return {
        "invoice_id": out.get("invoice_id", "unknown"),
        "summary":    out.get("summary"),
        "results":    results,
    }
