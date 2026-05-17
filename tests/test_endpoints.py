import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

import requests
import time

BASE_URL = "http://localhost:8000"

def run_tests():
    print("TEST 1 - Health check")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print("Status:", r.status_code)
        print("Response:", r.json())
    except Exception as e:
        print("Error:", e)
        return

    print("\nTEST 2 - Save a rule")
    try:
        r = requests.post(f"{BASE_URL}/rules", json={"rule_text": "Seller name is required", "severity": "high"})
        print("Status:", r.status_code)
        print("Response:", r.json())
    except Exception as e:
        print("Error:", e)

    print("\nTEST 3 - Validate one rule against XML")
    xml_data = "<Invoice><invoice_id>INV-001</invoice_id><seller_name>ABC Corp</seller_name><taxable_amount>10000</taxable_amount><tax_amount>1800</tax_amount><payable_amount>11800</payable_amount><currency_code>USD</currency_code><tax_category>S</tax_category><issue_date>2026-04-01</issue_date></Invoice>"
    try:
        r = requests.post(f"{BASE_URL}/validate", json={"rule_text": "Tax amount must be exactly 18% of taxable amount", "xml_content": xml_data})
        print("Status:", r.status_code)
        print("Response:", r.json())
    except Exception as e:
        print("Error:", e)

    print("\nTEST 6 - Dashboard stats")
    try:
        r = requests.get(f"{BASE_URL}/dashboard/stats")
        print("Status:", r.status_code)
        print("Response:", r.json())
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    time.sleep(2) # Give server time to boot
    run_tests()
