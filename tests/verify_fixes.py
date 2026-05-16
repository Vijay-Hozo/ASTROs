import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

"""
verify_fixes.py - Targeted regression tests for all 5 fixes applied.
"""
import requests, io

BASE = "http://localhost:8000"
results = []

def check(name, condition, detail=""):
    tag = "[PASS]" if condition else "[FAIL]"
    results.append((name, condition, str(detail)[:150]))
    print(f"  {tag} {name}: {str(detail)[:120]}")

def post(path, body=None): return requests.post(f"{BASE}{path}", json=body, timeout=30)
def get(path):             return requests.get(f"{BASE}{path}", timeout=10)

FUTURE_XML = """<Invoice>
  <invoice_id>INV-FUTURE</invoice_id>
  <issue_date>2028-01-01</issue_date>
  <seller_name>Test Corp</seller_name>
  <currency_code>USD</currency_code>
  <taxable_amount>1000</taxable_amount>
  <tax_amount>180</tax_amount>
  <payable_amount>1180</payable_amount>
  <tax_category>S</tax_category>
</Invoice>"""

PAST_XML = """<Invoice>
  <invoice_id>INV-PAST</invoice_id>
  <issue_date>2024-01-01</issue_date>
  <seller_name>Test Corp</seller_name>
  <currency_code>USD</currency_code>
  <taxable_amount>1000</taxable_amount>
  <tax_amount>180</tax_amount>
  <payable_amount>1180</payable_amount>
  <tax_category>S</tax_category>
</Invoice>"""

DATE_RULE = "Issue date cannot be in the future"

# ── FIX 1: Date validation ─────────────────────────────────────────
print("\n=== FIX 1: DATE VALIDATION ===")
r = post("/validate", {"rule_text": DATE_RULE, "xml_content": FUTURE_XML})
check("Future date (2028) -> FAIL",  r.status_code == 200 and r.json().get("status") == "FAIL",
      f"status={r.json().get('status')} msg={r.json().get('message','')[:60]}")

r = post("/validate", {"rule_text": DATE_RULE, "xml_content": PAST_XML})
check("Past date (2024) -> PASS",    r.status_code == 200 and r.json().get("status") == "PASS",
      f"status={r.json().get('status')} msg={r.json().get('message','')[:60]}")

# ── FIX 2: XML error handling ──────────────────────────────────────
print("\n=== FIX 2: XML ERROR HANDLING ===")
r = post("/validate", {"rule_text": "Seller name is required", "xml_content": "plain text"})
check("Plain text XML -> 400",       r.status_code == 400, f"status={r.status_code} body={r.text[:80]}")

r = post("/validate", {"rule_text": "Seller name is required", "xml_content": "<Invoice><unclosed>"})
check("Malformed XML -> 400",        r.status_code == 400, f"status={r.status_code}")

r = post("/validate", {"rule_text": "Seller name is required", "xml_content": "<Invoice/>"})
check("Minimal valid XML -> 200",    r.status_code == 200, f"status={r.status_code}")

# ── FIX 3: Rule sanity validation ──────────────────────────────────
print("\n=== FIX 3: RULE SANITY VALIDATION ===")
r = post("/rules", {"rule_text": "' OR 1=1 --", "severity": "low"})
check("SQL injection -> 400",        r.status_code == 400, f"status={r.status_code} body={r.text[:80]}")

r = post("/rules", {"rule_text": "hi", "severity": "low"})
check("Too short -> 400 or 422 (schema rejects)",  r.status_code in (400, 422), f"status={r.status_code}")

r = post("/rules", {"rule_text": "x" * 2001, "severity": "low"})
check("Too long (2001 chars) -> 400", r.status_code == 400, f"status={r.status_code}")

r = post("/validate", {"rule_text": "' OR 1=1 --", "xml_content": "<Invoice/>"})
check("SQL in /validate -> 400",     r.status_code == 400, f"status={r.status_code}")

r = post("/rules", {"rule_text": "Seller name is required", "severity": "high"})
check("Valid rule still works -> 200", r.status_code == 200, f"status={r.status_code}")

# ── FIX 4: Results 404 ─────────────────────────────────────────────
print("\n=== FIX 4: RESULTS 404 ===")
r = get("/results/999999")
check("GET /results/999999 -> 404",  r.status_code == 404, f"status={r.status_code} body={r.text[:80]}")

r = get("/results/99999")
check("GET /results/99999 -> 404",   r.status_code == 404, f"status={r.status_code}")

# ── SUMMARY ────────────────────────────────────────────────────────
print("\n" + "="*50)
total  = len(results)
passed = sum(1 for _, ok, _ in results if ok)
print(f"Fixes verified: {passed}/{total} passed")
if passed < total:
    print("\nFailed:")
    for name, ok, detail in results:
        if not ok:
            print(f"  [FAIL] {name} | {detail}")
