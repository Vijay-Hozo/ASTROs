"""
PS-3: Natural Language Rule Engine for XML Invoice Validation
Dataset Generator — generates all required files
"""

import os
import json
import random
import xml.etree.ElementTree as ET
from xml.dom import minidom

random.seed(42)

# ─── Output folders ───────────────────────────────────────────────────────────
os.makedirs("xml_invoices_train", exist_ok=True)
os.makedirs("xml_invoices_test", exist_ok=True)

# ─── Config ───────────────────────────────────────────────────────────────────
CURRENCIES = ["USD", "EUR", "GBP", "INR", "AED"]
TAX_CATEGORIES = ["S", "Z", "E", "AE"]
SELLERS = [f"Seller_{i}" for i in range(1, 21)]
BUYERS  = [f"Buyer_{i}"  for i in range(1, 31)]

# ─── 1. English Rules ──────────────────────────────────────────────────────────

RULE_TEMPLATES = [
    # amount_calculation
    {
        "rule_type": "amount_calculation",
        "templates": [
            ("Tax amount must be exactly {rate}% of taxable amount",
             {"field": "tax_amount", "base_field": "taxable_amount", "operation": "percentage", "value": "{rate}"}),
            ("Payable amount must equal taxable amount plus tax amount",
             {"field": "payable_amount", "base_field": "taxable_amount", "add_field": "tax_amount", "operation": "sum"}),
        ],
        "params": [{"rate": r} for r in [5, 9, 12, 18, 20, 28]],
    },
    # required_field
    {
        "rule_type": "required_field",
        "templates": [
            ("{field_label} is required",
             {"field": "{field}", "operation": "not_empty"}),
            ("Invoice must contain a {field_label}",
             {"field": "{field}", "operation": "not_empty"}),
        ],
        "params": [
            {"field": "invoice_id",    "field_label": "invoice ID"},
            {"field": "seller_name",   "field_label": "seller name"},
            {"field": "buyer_name",    "field_label": "buyer name"},
            {"field": "issue_date",    "field_label": "issue date"},
            {"field": "currency_code", "field_label": "currency code"},
            {"field": "tax_amount",    "field_label": "tax amount"},
            {"field": "payable_amount","field_label": "payable amount"},
        ],
    },
    # date_validation
    {
        "rule_type": "date_validation",
        "templates": [
            ("Issue date cannot be in the future",
             {"field": "issue_date", "operation": "not_future"}),
            ("Issue date must be a valid calendar date",
             {"field": "issue_date", "operation": "valid_date"}),
        ],
        "params": [{}],
    },
    # numeric_comparison
    {
        "rule_type": "numeric_comparison",
        "templates": [
            ("{field_label} must be greater than zero",
             {"field": "{field}", "operation": "gt", "value": 0}),
            ("{field_label} must not be negative",
             {"field": "{field}", "operation": "gte", "value": 0}),
            ("{field_label} must be less than 1000000",
             {"field": "{field}", "operation": "lt", "value": 1000000}),
        ],
        "params": [
            {"field": "taxable_amount",  "field_label": "Taxable amount"},
            {"field": "tax_amount",      "field_label": "Tax amount"},
            {"field": "payable_amount",  "field_label": "Payable amount"},
        ],
    },
    # currency_consistency
    {
        "rule_type": "currency_consistency",
        "templates": [
            ("Currency code must be one of USD, EUR, GBP, INR, or AED",
             {"field": "currency_code", "operation": "in", "value": ["USD","EUR","GBP","INR","AED"]}),
            ("All line items must use the same currency as the invoice",
             {"field": "line_item_currency", "operation": "matches_invoice_currency"}),
        ],
        "params": [{}],
    },
    # tax_category_validation
    {
        "rule_type": "tax_category_validation",
        "templates": [
            ("Tax category must be S, Z, E, or AE",
             {"field": "tax_category", "operation": "in", "value": ["S","Z","E","AE"]}),
        ],
        "params": [{}],
    },
    # conditional_required_field
    {
        "rule_type": "conditional_required_field",
        "templates": [
            ("If tax category is E, tax exemption reason is required",
             {"condition_field": "tax_category", "condition_value": "E",
              "required_field": "tax_exemption_reason", "operation": "conditional_required"}),
            ("If tax category is AE, buyer VAT number is required",
             {"condition_field": "tax_category", "condition_value": "AE",
              "required_field": "buyer_vat", "operation": "conditional_required"}),
        ],
        "params": [{}],
    },
    # duplicate_field_check
    {
        "rule_type": "duplicate_field_check",
        "templates": [
            ("Invoice ID must be unique",
             {"field": "invoice_id", "operation": "unique"}),
        ],
        "params": [{}],
    },
]


def expand_rules(templates_config):
    rules = []
    rule_id = 1
    for group in templates_config:
        for tmpl_text, tmpl_mapping in group["templates"]:
            for param in group["params"]:
                text = tmpl_text.format(**param)
                mapping = {}
                for k, v in tmpl_mapping.items():
                    mapping[k] = str(v).format(**param) if isinstance(v, str) else v
                rules.append({
                    "rule_id": f"R{rule_id:03d}",
                    "rule_text": text,
                    "severity": random.choice(["error", "warning"]),
                    "rule_type": group["rule_type"],
                    "expected_error_message": f"Validation failed: {text.lower()}",
                    "structured": mapping,
                })
                rule_id += 1
    return rules


all_rules = expand_rules(RULE_TEMPLATES)
random.shuffle(all_rules)

train_rules = all_rules[:100]
test_rules  = all_rules[100:130] if len(all_rules) >= 130 else all_rules[100:]

# Pad to minimums if needed
while len(train_rules) < 100:
    r = random.choice(train_rules).copy()
    r["rule_id"] = f"R{len(train_rules)+200:03d}"
    train_rules.append(r)
while len(test_rules) < 30:
    r = random.choice(train_rules).copy()
    r["rule_id"] = f"R{len(test_rules)+300:03d}"
    test_rules.append(r)


def write_rules_txt(rules, path):
    with open(path, "w") as f:
        for r in rules:
            f.write(f"rule_id: {r['rule_id']}\n")
            f.write(f"rule_text: {r['rule_text']}\n")
            f.write(f"severity: {r['severity']}\n")
            f.write(f"rule_type: {r['rule_type']}\n")
            f.write(f"expected_error_message: {r['expected_error_message']}\n")
            f.write("\n")

write_rules_txt(train_rules, "rules_train.txt")
write_rules_txt(test_rules,  "rules_test.txt")
print(f"rules_train.txt → {len(train_rules)} rules")
print(f"rules_test.txt  → {len(test_rules)} rules")


# ─── 2. rule_mappings_train.json ───────────────────────────────────────────────

rule_mappings = []
for r in train_rules:
    entry = {
        "rule_id":   r["rule_id"],
        "rule_text": r["rule_text"],
        "rule_type": r["rule_type"],
        "severity":  r["severity"],
        "expected_error_message": r["expected_error_message"],
        "structured_rule": r["structured"],
    }
    rule_mappings.append(entry)

with open("rule_mappings_train.json", "w") as f:
    json.dump(rule_mappings, f, indent=2)
print(f"rule_mappings_train.json → {len(rule_mappings)} mappings")


# ─── 3. XML Invoice Generator ─────────────────────────────────────────────────

seen_ids = set()

def make_invoice_xml(invoice_id, make_invalid=False):
    """Generate a realistic invoice XML. make_invalid injects random errors."""
    taxable = round(random.uniform(500, 50000), 2)
    tax_rate = random.choice([0.05, 0.09, 0.12, 0.18, 0.20, 0.28])
    tax_amount = round(taxable * tax_rate, 2)
    payable = round(taxable + tax_amount, 2)
    currency = random.choice(CURRENCIES)
    tax_cat = random.choice(TAX_CATEGORIES)
    issue_date = f"2026-{random.randint(1,4):02d}-{random.randint(1,28):02d}"

    errors = []

    if make_invalid:
        error_type = random.choice([
            "tax_mismatch", "payable_mismatch", "missing_invoice_id",
            "future_date", "missing_seller", "invalid_currency",
            "invalid_tax_category", "missing_exemption"
        ])
        errors.append(error_type)

        if error_type == "tax_mismatch":
            tax_amount = round(tax_amount * random.choice([1.5, 0.5, 2.0]), 2)
            payable = round(taxable + tax_amount, 2)
        elif error_type == "payable_mismatch":
            payable = round(payable + random.uniform(100, 500), 2)
        elif error_type == "missing_invoice_id":
            invoice_id = ""
        elif error_type == "future_date":
            issue_date = f"2027-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        elif error_type == "missing_seller":
            pass  # handled below
        elif error_type == "invalid_currency":
            currency = "XYZ"
        elif error_type == "invalid_tax_category":
            tax_cat = "X"
        elif error_type == "missing_exemption":
            tax_cat = "E"  # will be missing exemption reason

    # Build XML
    inv = ET.Element("Invoice")
    ET.SubElement(inv, "invoice_id").text = invoice_id
    ET.SubElement(inv, "issue_date").text = issue_date
    seller = "" if (make_invalid and "missing_seller" in errors) else random.choice(SELLERS)
    ET.SubElement(inv, "seller_name").text = seller
    ET.SubElement(inv, "buyer_name").text = random.choice(BUYERS)
    ET.SubElement(inv, "currency_code").text = currency
    ET.SubElement(inv, "taxable_amount").text = str(taxable)
    ET.SubElement(inv, "tax_amount").text = str(tax_amount)
    ET.SubElement(inv, "payable_amount").text = str(payable)
    ET.SubElement(inv, "tax_category").text = tax_cat

    # Add exemption reason only if NOT the missing_exemption error
    if tax_cat == "E" and "missing_exemption" not in errors:
        ET.SubElement(inv, "tax_exemption_reason").text = "VATEX-EU-AE"

    # Line items
    line_items_el = ET.SubElement(inv, "line_items")
    n_items = random.randint(1, 5)
    for i in range(n_items):
        item_el = ET.SubElement(line_items_el, "item")
        qty   = random.randint(1, 10)
        price = round(random.uniform(50, 5000), 2)
        ET.SubElement(item_el, "description").text = f"Item {i+1}"
        ET.SubElement(item_el, "quantity").text = str(qty)
        ET.SubElement(item_el, "unit_price").text = str(price)
        ET.SubElement(item_el, "line_total").text = str(round(qty * price, 2))

    xml_str = minidom.parseString(ET.tostring(inv)).toprettyxml(indent="  ")
    xml_str = "\n".join(xml_str.split("\n")[1:])  # remove <?xml?> declaration line
    return xml_str, errors


def generate_xml_set(folder, count, invalid_rate=0.4):
    labels = []
    for i in range(count):
        inv_id = f"INV-{i+1:04d}"
        make_invalid = random.random() < invalid_rate
        xml_str, errors = make_invoice_xml(inv_id, make_invalid)
        fname = f"{folder}/{inv_id}.xml"
        with open(fname, "w") as f:
            f.write(xml_str)
        labels.append({
            "invoice_id": inv_id,
            "is_valid": len(errors) == 0,
            "errors": errors,
        })
    return labels


train_labels_raw = generate_xml_set("xml_invoices_train", 300, invalid_rate=0.4)
test_labels_raw  = generate_xml_set("xml_invoices_test",  100, invalid_rate=0.4)
print(f"xml_invoices_train/ → 300 XML files")
print(f"xml_invoices_test/  → 100 XML files")


# ─── 4. validation_labels_train.json ──────────────────────────────────────────

def build_validation_labels(invoice_labels, rules):
    """
    Cross invoice errors with rules to produce per-invoice per-rule results.
    """
    ERROR_TO_RULE_TYPE = {
        "tax_mismatch":        "amount_calculation",
        "payable_mismatch":    "amount_calculation",
        "missing_invoice_id":  "required_field",
        "future_date":         "date_validation",
        "missing_seller":      "required_field",
        "invalid_currency":    "currency_consistency",
        "invalid_tax_category":"tax_category_validation",
        "missing_exemption":   "conditional_required_field",
    }

    results = []
    for inv in invoice_labels:
        failing_types = {ERROR_TO_RULE_TYPE[e] for e in inv["errors"] if e in ERROR_TO_RULE_TYPE}
        for rule in rules:
            fails = rule["rule_type"] in failing_types
            results.append({
                "invoice_id": inv["invoice_id"],
                "rule_id":    rule["rule_id"],
                "result":     "FAIL" if fails else "PASS",
                "error_type": inv["errors"][0] if fails and inv["errors"] else None,
            })
    return results


validation_labels = build_validation_labels(train_labels_raw, train_rules)
with open("validation_labels_train.json", "w") as f:
    json.dump(validation_labels, f, indent=2)
print(f"validation_labels_train.json → {len(validation_labels)} records")


# ─── Summary ──────────────────────────────────────────────────────────────────
print("\n✅ Dataset generation complete:")
print(f"   rules_train.txt              → {len(train_rules)} rules")
print(f"   rules_test.txt               → {len(test_rules)} rules")
print(f"   rule_mappings_train.json     → {len(rule_mappings)} entries")
print(f"   xml_invoices_train/          → 300 XML files")
print(f"   xml_invoices_test/           → 100 XML files")
print(f"   validation_labels_train.json → {len(validation_labels)} records")
