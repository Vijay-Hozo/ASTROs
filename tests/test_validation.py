import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from main import _validate_rule_text
from fastapi import HTTPException

print("Testing _validate_rule_text function from main.py:")

# Test 1: Oversized rule
print("\n1. Oversized rule (>500 chars):")
try:
    large_rule = "A" * 501
    _validate_rule_text(large_rule)
    print("  FAILED - accepted oversized rule")
except HTTPException as e:
    print(f"  PASSED - rejected: {e.detail}")

# Test 2: SQL injection
print("\n2. SQL injection payload:")
try:
    sql_inject = "test'; DROP TABLE rules; --"
    _validate_rule_text(sql_inject)
    print("  FAILED - accepted SQL injection")
except HTTPException as e:
    print(f"  PASSED - rejected: {e.detail}")

# Test 3: Suspicious tokens
print("\n3. Other suspicious tokens:")
try:
    suspicious = "select * from users"
    _validate_rule_text(suspicious)
    print("  FAILED - accepted suspicious content")
except HTTPException as e:
    print(f"  PASSED - rejected: {e.detail}")

# Test 4: Valid rule
print("\n4. Valid rule:")
try:
    valid = "Tax amount must be greater than zero"
    _validate_rule_text(valid)
    print(f"  PASSED - accepted valid rule")
except HTTPException as e:
    print(f"  FAILED - rejected valid rule: {e.detail}")
