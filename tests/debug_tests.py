import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

﻿from schemas import SaveRuleRequest, BatchEvaluateRequest

# Test 1: Check size limit
print("Testing XML size limit:")
try:
    large_xml = "<test>" + "x" * 1_000_001 + "</test>"
    req = BatchEvaluateRequest(xml_content=large_xml)
    print(f"  Size check FAILED - accepted {len(large_xml)} bytes")
except Exception as e:
    print(f"  Size check PASSED - rejected: {type(e).__name__}")

# Test 2: Check ReDoS payload
print("\nTesting ReDoS/backtracking payload:")
try:
    malicious = "(" * 100 + "test" + ")" * 100
    print(f"  Input length: {len(malicious)}")
    req = SaveRuleRequest(rule_text=malicious, severity="high")
    print(f"  ReDoS test FAILED - accepted suspicious payload")
except Exception as e:
    print(f"  ReDoS test PASSED - rejected: {type(e).__name__}")

# Test 3: Check SQL injection
print("\nTesting SQL injection payload:")
try:
    sql_inject = "test'; DROP TABLE rules; --"
    req = SaveRuleRequest(rule_text=sql_inject, severity="high")
    print(f"  SQL injection test FAILED - accepted SQL payload")
except Exception as e:
    print(f"  SQL injection test PASSED - rejected: {type(e).__name__}")
