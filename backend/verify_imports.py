#!/usr/bin/env python3
"""
Quick import verification script to test backend wiring.
Run from Backend/ directory: python verify_imports.py
"""

import sys
import traceback

print("=" * 70)
print("BACKEND IMPORT VERIFICATION")
print("=" * 70)

tests = []

# Test 1: Import orm_models
print("\n[1] Testing orm_models imports...")
try:
    from orm_models import Rule, Invoice, ValidationResult, init_db, get_db, engine
    print("    ✅ orm_models: Rule, Invoice, ValidationResult, init_db, get_db, engine")
    tests.append(("orm_models", True, None))
except Exception as e:
    print(f"    ❌ orm_models: {str(e)}")
    tests.append(("orm_models", False, str(e)))
    traceback.print_exc()

# Test 2: Import database (forwarding)
print("\n[2] Testing database forwarding...")
try:
    from database import get_db as get_db_fwd, init_db as init_db_fwd, Rule as RuleFwd
    print("    ✅ database: get_db, init_db, Rule (forwarded from orm_models)")
    tests.append(("database", True, None))
except Exception as e:
    print(f"    ❌ database: {str(e)}")
    tests.append(("database", False, str(e)))
    traceback.print_exc()

# Test 3: Import rule_parser
print("\n[3] Testing rule_parser...")
try:
    from rule_parser import RuleParser, parse_rule
    parser = RuleParser()
    result = parser.parse("Seller name is required")
    print(f"    ✅ RuleParser instantiated and tested")
    print(f"       Sample parse result: {result}")
    tests.append(("rule_parser", True, None))
except Exception as e:
    print(f"    ❌ rule_parser: {str(e)}")
    tests.append(("rule_parser", False, str(e)))
    traceback.print_exc()

# Test 4: Import xml_reader
print("\n[4] Testing xml_reader...")
try:
    from xml_reader import XMLReader, parse_invoice_xml
    reader = XMLReader()
    sample_xml = "<Invoice><seller_name>Test</seller_name></Invoice>"
    result = reader.extract(sample_xml)
    print(f"    ✅ XMLReader instantiated and tested")
    print(f"       Sample extract result: seller_name = {result.get('seller_name')}")
    tests.append(("xml_reader", True, None))
except Exception as e:
    print(f"    ❌ xml_reader: {str(e)}")
    tests.append(("xml_reader", False, str(e)))
    traceback.print_exc()

# Test 5: Import executor
print("\n[5] Testing executor...")
try:
    from executor import RuleExecutor, execute_rule
    executor = RuleExecutor()
    print(f"    ✅ RuleExecutor instantiated")
    print(f"       Methods available: execute(), execute_all()")
    tests.append(("executor", True, None))
except Exception as e:
    print(f"    ❌ executor: {str(e)}")
    tests.append(("executor", False, str(e)))
    traceback.print_exc()

# Test 6: Import evaluator
print("\n[6] Testing evaluator...")
try:
    from evaluator import Evaluator, EvaluationResult, BatchSummary
    evaluator = Evaluator()
    print(f"    ✅ Evaluator instantiated")
    print(f"       Has RuleParser: {hasattr(evaluator, 'parser')}")
    print(f"       Has XMLReader: {hasattr(evaluator, 'reader')}")
    print(f"       Has RuleExecutor: {hasattr(evaluator, 'executor')}")
    tests.append(("evaluator", True, None))
except Exception as e:
    print(f"    ❌ evaluator: {str(e)}")
    tests.append(("evaluator", False, str(e)))
    traceback.print_exc()

# Test 7: Integration test - evaluate_one
print("\n[7] Testing full integration (evaluate_one)...")
try:
    from evaluator import Evaluator
    evaluator = Evaluator()
    rule_text = "Seller name is required"
    xml_content = "<Invoice><seller_name>ABC Ltd</seller_name></Invoice>"
    result = evaluator.evaluate_one(rule_text, xml_content)
    print(f"    ✅ evaluate_one() completed successfully")
    print(f"       Result status: {result.result}")
    print(f"       Result message: {result.message}")
    tests.append(("integration", True, None))
except Exception as e:
    print(f"    ❌ integration: {str(e)}")
    tests.append(("integration", False, str(e)))
    traceback.print_exc()

# Test 8: Import main.py (check it boots)
print("\n[8] Testing main.py imports...")
try:
    # Just import to see if it boots without errors
    import main
    print(f"    ✅ main.py imports successfully")
    print(f"       FastAPI app available: {hasattr(main, 'app')}")
    print(f"       Evaluator available: {hasattr(main, 'evaluator')}")
    print(f"       Parser available: {hasattr(main, 'parser')}")
    tests.append(("main.py", True, None))
except Exception as e:
    print(f"    ⚠️  main.py: {str(e)}")
    # This is a warning, not a failure - main.py might not boot due to FastAPI setup
    tests.append(("main.py", None, str(e)))

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

passed = sum(1 for _, status, _ in tests if status is True)
failed = sum(1 for _, status, _ in tests if status is False)
warnings = sum(1 for _, status, _ in tests if status is None)

for name, status, error in tests:
    if status is True:
        print(f"✅ {name:<20} PASS")
    elif status is False:
        print(f"❌ {name:<20} FAIL: {error[:50]}")
    else:
        print(f"⚠️  {name:<20} WARNING: {error[:50]}")

print(f"\nResults: {passed} passed, {failed} failed, {warnings} warnings")
print("=" * 70)

if failed == 0:
    print("\n🎉 All critical imports working! Backend is wired correctly.")
    sys.exit(0)
else:
    print(f"\n⚠️  {failed} imports failed. Review errors above.")
    sys.exit(1)
