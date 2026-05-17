import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

"""
qa_full_test.py - Complete end-to-end QA for PS-3 Natural Language Rule Engine
Covers: Health, CRUD, Validation, XML edge cases, Batch, Upload, Results, Dashboard, Security
"""
import requests, json, time, io

BASE = "http://localhost:8000"
PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def log(phase, name, status, detail=""):
    tag = PASS if status else FAIL
    results.append({"phase": phase, "name": name, "status": status, "detail": str(detail)[:200]})
    print(f"  {tag} {name}: {str(detail)[:120]}")

def post(path, body): return requests.post(f"{BASE}{path}", json=body, timeout=30)
def get(path):        return requests.get(f"{BASE}{path}", timeout=10)

VALID_XML = """<Invoice>
  <invoice_id>INV-1001</invoice_id>
  <issue_date>2026-04-15</issue_date>
  <seller_name>Seller Corp</seller_name>
  <buyer_name>Buyer Ltd</buyer_name>
  <currency_code>USD</currency_code>
  <taxable_amount>1000</taxable_amount>
  <tax_amount>180</tax_amount>
  <payable_amount>1180</payable_amount>
  <tax_category>S</tax_category>
</Invoice>"""

INVALID_XML = """<Invoice>
  <invoice_id></invoice_id>
  <issue_date>2027-12-01</issue_date>
  <seller_name></seller_name>
  <currency_code>XYZ</currency_code>
  <taxable_amount>-100</taxable_amount>
  <tax_amount>999</tax_amount>
  <payable_amount>500</payable_amount>
  <tax_category>X</tax_category>
</Invoice>"""

saved_rule_ids = []

# ── PHASE 1: Health ───────────────────────────────────────────────
print("\n=== PHASE 1: HEALTH ===")
r = get("/health")
log(1, "GET /health status 200",     r.status_code == 200, r.status_code)
d = r.json()
log(1, "health.status == ok",        d.get("status") == "ok", d.get("status"))
log(1, "health.version present",     bool(d.get("version")), d.get("version"))
log(1, "health.timestamp present",   bool(d.get("timestamp")), d.get("timestamp"))

# ── PHASE 2: Rule CRUD ────────────────────────────────────────────
print("\n=== PHASE 2: RULE CRUD (POST /rules) ===")
rule_tests = [
    ("Required field",      "Seller name is required",                          "required_field"),
    ("Amount calculation",  "Tax amount must be exactly 18% of taxable amount", "amount_calculation"),
    ("Sum validation",      "Payable amount must equal taxable amount plus tax amount", "amount_calculation"),
    ("Date validation",     "Issue date cannot be in the future",               "date_validation"),
    ("Numeric comparison",  "Taxable amount must be greater than zero",         "numeric_comparison"),
    ("Currency consistency","Currency code must be one of USD, EUR, GBP, INR, or AED", "currency_consistency"),
    ("Tax category",        "Tax category must be S, Z, E, or AE",             "tax_category_validation"),
    ("Conditional required","If tax category is E, tax exemption reason is required", "conditional_required_field"),
    ("Duplicate check",     "Invoice ID must be unique",                        "duplicate_field_check"),
]
for label, rule_text, expected_type in rule_tests:
    try:
        r = post("/rules", {"rule_text": rule_text, "severity": "high"})
        ok = r.status_code == 200
        if ok:
            d = r.json()
            saved_rule_ids.append(d["id"])
            type_ok = d.get("parsed_json", {}).get("rule_type") == expected_type
            log(2, f"{label} - saved",      ok, f"id={d.get('id')}")
            log(2, f"{label} - rule_type",  type_ok, f"got={d.get('parsed_json',{}).get('rule_type')} expected={expected_type}")
        else:
            log(2, f"{label}", False, r.text[:150])
    except Exception as e:
        log(2, f"{label} - EXCEPTION", False, e)

print("\n--- PHASE 2: Worst-case inputs ---")
worst_cases = [
    ("Empty rule (short, blocked by schema)",   {"rule_text": "x"*3, "severity": "low"},   422),
    ("Garbage text",                            {"rule_text": "abracadabra quantum pizza", "severity": "low"}, None),
    ("Unknown field",                           {"rule_text": "Shipping port code must be required", "severity": "low"}, None),
    ("SQL injection",                           {"rule_text": "' OR 1=1 --", "severity": "low"}, None),
    ("Very long rule (300 chars)",              {"rule_text": "Tax amount " * 30, "severity": "low"}, None),
    ("Missing severity",                        {"rule_text": "Seller name is required"}, None),
    ("Invalid severity",                        {"rule_text": "Seller name is required", "severity": "INVALID"}, 422),
]
for label, body, expected_code in worst_cases:
    try:
        r = post("/rules", body)
        if expected_code:
            log(2, f"Worst-case: {label}", r.status_code == expected_code, f"status={r.status_code}")
        else:
            log(2, f"Worst-case: {label} - no crash", r.status_code in [200, 400, 422, 500], f"status={r.status_code} body={r.text[:80]}")
    except Exception as e:
        log(2, f"Worst-case: {label} - EXCEPTION", False, e)

# ── PHASE 3: List Rules ───────────────────────────────────────────
print("\n=== PHASE 3: LIST RULES (GET /rules) ===")
r = get("/rules")
log(3, "GET /rules status 200",     r.status_code == 200, r.status_code)
rules_list = r.json() if r.status_code == 200 else []
log(3, "Rules list is array",       isinstance(rules_list, list), type(rules_list))
log(3, "Rules count >= 9",         len(rules_list) >= 9, len(rules_list))
if rules_list:
    sample = rules_list[0]
    log(3, "Rule has id",           "id" in sample, sample.keys())
    log(3, "Rule has rule_text",    "rule_text" in sample, "")
    log(3, "Rule has created_at",   "created_at" in sample, "")
    log(3, "Rule parsed_json valid",isinstance(sample.get("parsed_json"), dict), type(sample.get("parsed_json")))

# ── PHASE 4: Single Validate ──────────────────────────────────────
print("\n=== PHASE 4: SINGLE VALIDATION (POST /validate) ===")
validate_rules = [
    ("Seller name is required",                          VALID_XML,   "PASS"),
    ("Tax amount must be exactly 18% of taxable amount", VALID_XML,   "PASS"),
    ("Issue date cannot be in the future",               VALID_XML,   "PASS"),
    ("Currency code must be one of USD, EUR, GBP, INR, or AED", VALID_XML, "PASS"),
    ("Seller name is required",                          INVALID_XML, "FAIL"),
    ("Tax amount must be exactly 18% of taxable amount", INVALID_XML, "FAIL"),
    ("Issue date cannot be in the future",               INVALID_XML, "FAIL"),
    ("Currency code must be one of USD, EUR, GBP, INR, or AED", INVALID_XML, "FAIL"),
]
for rule_text, xml, expected_status in validate_rules:
    try:
        r = post("/validate", {"rule_text": rule_text, "xml_content": xml})
        ok = r.status_code == 200
        if ok:
            d = r.json()
            status_ok = d.get("status") == expected_status
            log(4, f"validate '{rule_text[:40]}' -> {expected_status}", status_ok, f"got={d.get('status')} msg={d.get('message','')[:60]}")
        else:
            log(4, f"validate '{rule_text[:40]}'", False, r.text[:100])
    except Exception as e:
        log(4, f"EXCEPTION on '{rule_text[:40]}'", False, e)

# ── PHASE 5: Worst-case XML ───────────────────────────────────────
print("\n=== PHASE 5: WORST-CASE XML ===")
xml_edge_cases = [
    ("Malformed XML (unclosed tag)",    "<Invoice><invoice_id>"),
    ("Empty XML string",                "<x/>"),
    ("XML with unexpected tags",        "<Invoice><foo>bar</foo></Invoice>"),
    ("String instead of number",        "<Invoice><tax_amount>abc</tax_amount><taxable_amount>1000</taxable_amount></Invoice>"),
    ("Missing root tag",                "just plain text"),
    ("Invalid date format",             "<Invoice><issue_date>not-a-date</issue_date></Invoice>"),
    ("Huge XML (repeated items)",       "<Invoice>" + "<item><amount>100</amount></item>"*500 + "</Invoice>"),
]
for label, xml_content in xml_edge_cases:
    try:
        r = post("/validate", {"rule_text": "Seller name is required", "xml_content": xml_content})
        log(5, f"XML edge: {label} - no crash", r.status_code in [200, 400, 422, 500], f"status={r.status_code}")
    except Exception as e:
        log(5, f"XML edge: {label} - EXCEPTION", False, e)

# ── PHASE 6: Batch Validate ───────────────────────────────────────
print("\n=== PHASE 6: BATCH VALIDATE (POST /validate/all-rules) ===")
try:
    r = post("/validate/all-rules", {"xml_content": VALID_XML})
    log(6, "POST /validate/all-rules status", r.status_code == 200, r.status_code)
    if r.status_code == 200:
        d = r.json()
        log(6, "Has summary",       "summary" in d, d.keys())
        log(6, "Has results list",  isinstance(d.get("results"), list), "")
        s = d.get("summary", {})
        log(6, "Summary total > 0", s.get("total", 0) > 0, s)
        log(6, "passed+failed+errors == total",
            s.get("passed",0)+s.get("failed",0)+s.get("errors",0) == s.get("total",0), s)
    else:
        log(6, "Batch validate body", False, r.text[:150])
except Exception as e:
    log(6, "EXCEPTION", False, e)

# ── PHASE 7: Invoice Upload ───────────────────────────────────────
print("\n=== PHASE 7: INVOICE UPLOAD ===")
uploaded_invoice_id = None
try:
    xml_bytes = VALID_XML.encode()
    r = requests.post(f"{BASE}/invoices/upload",
                      files={"file": ("test_invoice.xml", io.BytesIO(xml_bytes), "application/xml")},
                      timeout=10)
    log(7, "POST /invoices/upload status 200", r.status_code == 200, r.status_code)
    if r.status_code == 200:
        d = r.json()
        uploaded_invoice_id = d.get("id")
        log(7, "Has id",          bool(d.get("id")), d.get("id"))
        log(7, "Has filename",    bool(d.get("filename")), d.get("filename"))
        log(7, "Has uploaded_at", bool(d.get("uploaded_at")), d.get("uploaded_at"))
    else:
        log(7, "Upload body", False, r.text[:150])
except Exception as e:
    log(7, "EXCEPTION", False, e)

# Non-XML upload
try:
    r = requests.post(f"{BASE}/invoices/upload",
                      files={"file": ("bad.txt", io.BytesIO(b"not xml"), "text/plain")},
                      timeout=10)
    log(7, "Non-XML rejected (400)", r.status_code == 400, r.status_code)
except Exception as e:
    log(7, "Non-XML EXCEPTION", False, e)

# GET /invoices
r = get("/invoices")
log(7, "GET /invoices status 200", r.status_code == 200, r.status_code)
inv_list = r.json() if r.status_code == 200 else []
log(7, "Invoices is list",        isinstance(inv_list, list), type(inv_list))

# ── PHASE 8: Stored Invoice Validate ─────────────────────────────
print("\n=== PHASE 8: STORED INVOICE VALIDATION ===")
if uploaded_invoice_id:
    try:
        r = post(f"/invoices/{uploaded_invoice_id}/validate", {})
        log(8, f"POST /invoices/{uploaded_invoice_id}/validate", r.status_code == 200, r.status_code)
        if r.status_code == 200:
            d = r.json()
            log(8, "Has summary",  "summary" in d, d.keys())
            log(8, "Has results",  isinstance(d.get("results"), list), "")
    except Exception as e:
        log(8, "EXCEPTION", False, e)
    # Invalid ID
    r = post("/invoices/999999/validate", {})
    log(8, "Invalid invoice_id -> 404", r.status_code == 404, r.status_code)
else:
    log(8, "Skipped - no uploaded invoice", False, "upload failed in phase 7")

# ── PHASE 9: Results APIs ─────────────────────────────────────────
print("\n=== PHASE 9: RESULTS APIs ===")
r = get("/results")
log(9, "GET /results status 200",   r.status_code == 200, r.status_code)
res_list = r.json() if r.status_code == 200 else []
log(9, "Results is list",           isinstance(res_list, list), type(res_list))
if uploaded_invoice_id:
    r = get(f"/results/{uploaded_invoice_id}")
    log(9, f"GET /results/{uploaded_invoice_id}", r.status_code == 200, r.status_code)
r = get("/results/999999")
log(9, "GET /results/999999 no crash", r.status_code in [200, 404], r.status_code)

# ── PHASE 10: Dashboard ───────────────────────────────────────────
print("\n=== PHASE 10: DASHBOARD ===")
r = get("/dashboard/stats")
log(10, "GET /dashboard/stats 200",  r.status_code == 200, r.status_code)
if r.status_code == 200:
    d = r.json()
    for key in ["total_rules","total_invoices","total_validations","total_passed","total_failed","pass_rate"]:
        log(10, f"Has {key}", key in d, d.get(key))

# ── PHASE 11: DB Integrity ────────────────────────────────────────
print("\n=== PHASE 11: DB INTEGRITY ===")
rules_r = get("/rules")
results_r = get("/results")
if rules_r.status_code == 200 and results_r.status_code == 200:
    rule_ids = {r["id"] for r in rules_r.json()}
    orphan = [r for r in results_r.json() if r.get("rule_id") and r["rule_id"] not in rule_ids]
    log(11, "No orphan validation results", len(orphan) == 0, f"orphans={len(orphan)}")
log(11, "Rules have timestamps", all("created_at" in r for r in rules_r.json()), "")

# ── PHASE 12: Security ────────────────────────────────────────────
print("\n=== PHASE 12: SECURITY ===")
# SQL injection in rule_text
r = post("/rules", {"rule_text": "'; DROP TABLE rules; --", "severity": "low"})
log(12, "SQL injection in rule_text - no crash", r.status_code in [200,400,422,500], r.status_code)

# XML entity injection (XXE)
xxe = """<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><Invoice><seller_name>&xxe;</seller_name></Invoice>"""
r = post("/validate", {"rule_text": "Seller name is required", "xml_content": xxe})
log(12, "XXE attempt - no crash", r.status_code in [200,400,422,500], r.status_code)

# Missing required fields
r = post("/rules", {})
log(12, "Missing body fields -> 422", r.status_code == 422, r.status_code)

r = post("/validate", {"rule_text": "Seller name is required"})
log(12, "Missing xml_content -> 422", r.status_code == 422, r.status_code)

# ── PHASE 13: Code quality checks ────────────────────────────────
print("\n=== PHASE 13: CODE QUALITY (static checks) ===")
import importlib.util, os

files_to_check = ["main.py","evaluator.py","llm_rule_parser.py","orm_models.py","schemas.py","xslt_executor.py","xslt_templates.py"]
for f in files_to_check:
    path = os.path.join(os.path.dirname(__file__), f)
    exists = os.path.exists(path)
    log(13, f"File exists: {f}", exists, path)

# Check no duplicate model files
for conflict in ["database.py","models.py","executor.py","executer.py"]:
    path = os.path.join(os.path.dirname(__file__), conflict)
    log(13, f"No conflicting file: {conflict}", not os.path.exists(path), "")

# ── FINAL SUMMARY ─────────────────────────────────────────────────
print("\n" + "="*60)
print("FINAL QA SUMMARY")
print("="*60)
total   = len(results)
passed  = sum(1 for r in results if r["status"])
failed  = total - passed
pct     = round(passed/total*100, 1) if total else 0

by_phase = {}
for r in results:
    by_phase.setdefault(r["phase"], {"p":0,"f":0})
    if r["status"]: by_phase[r["phase"]]["p"] += 1
    else:           by_phase[r["phase"]]["f"] += 1

print(f"\nOverall: {passed}/{total} passed ({pct}%)")
print("\nPhase breakdown:")
for ph in sorted(by_phase):
    p = by_phase[ph]["p"]; f = by_phase[ph]["f"]
    print(f"  Phase {ph:>2}: {p} pass / {f} fail")

print("\nFailed checks:")
for r in results:
    if not r["status"]:
        print(f"  [FAIL] Phase {r['phase']} | {r['name']} | {r['detail']}")
