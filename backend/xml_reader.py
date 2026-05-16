"""
XML Reader — parses an invoice XML file or string into a clean Python dict.
The executor will consume this dict to run rules against.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional


def parse_invoice_xml(source: str) -> dict:
    """
    Accepts either:
      - A file path string ending in .xml
      - A raw XML string

    Returns a clean dict with all invoice fields.
    Missing fields return None — executor handles None safely.
    """
    try:
        if source.strip().startswith("<"):
            root = ET.fromstring(source)
        else:
            tree = ET.parse(source)
            root = tree.getroot()
    except ET.ParseError as e:
        return {"_parse_error": str(e)}

    def get(tag: str) -> Optional[str]:
        el = root.find(tag)
        if el is None:
            return None
        text = el.text
        if text is None:
            return None
        return text.strip()

    def get_float(tag: str) -> Optional[float]:
        val = get(tag)
        if val is None:
            return None
        try:
            return float(val)
        except ValueError:
            return None

    def get_date(tag: str) -> Optional[datetime]:
        val = get(tag)
        if val is None:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        return None  # unparseable date

    # ── Line items ────────────────────────────────────────────────────────────
    line_items = []
    line_items_el = root.find("line_items")
    if line_items_el is not None:
        for item in line_items_el.findall("item"):
            def item_get(tag):
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else None
            def item_float(tag):
                v = item_get(tag)
                try:
                    return float(v) if v else None
                except ValueError:
                    return None

            line_items.append({
                "description": item_get("description"),
                "quantity":    item_float("quantity"),
                "unit_price":  item_float("unit_price"),
                "line_total":  item_float("line_total"),
                "currency":    item_get("currency") or get("currency_code"),
            })

    invoice = {
        # Identity
        "invoice_id":            get("invoice_id"),
        "invoice_number":        get("invoice_id"),        # alias

        # Parties
        "seller_name":           get("seller_name"),
        "buyer_name":            get("buyer_name"),
        "seller_vat":            get("seller_vat"),
        "buyer_vat":             get("buyer_vat"),

        # Dates
        "issue_date_raw":        get("issue_date"),
        "issue_date":            get_date("issue_date"),

        # Currency & amounts
        "currency_code":         get("currency_code"),
        "taxable_amount":        get_float("taxable_amount"),
        "tax_amount":            get_float("tax_amount"),
        "payable_amount":        get_float("payable_amount"),

        # Tax
        "tax_category":          get("tax_category"),
        "tax_exemption_reason":  get("tax_exemption_reason"),

        # Line items
        "line_items":            line_items,
        "line_item_currency":    line_items[0]["currency"] if line_items else None,
    }

    return invoice


# ── Helpers for executor ───────────────────────────────────────────────────────

def get_field(invoice: dict, field: str):
    """Safe field getter — returns None if field missing."""
    return invoice.get(field)


def get_all_line_item_currencies(invoice: dict) -> list:
    """Returns list of currencies from all line items."""
    return [
        item["currency"]
        for item in invoice.get("line_items", [])
        if item.get("currency")
    ]


# ── Self test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_xml = """
    <Invoice>
      <invoice_id>INV-0001</invoice_id>
      <issue_date>2026-04-15</issue_date>
      <seller_name>Seller_1</seller_name>
      <buyer_name>Buyer_5</buyer_name>
      <currency_code>USD</currency_code>
      <taxable_amount>10000.00</taxable_amount>
      <tax_amount>1800.00</tax_amount>
      <payable_amount>11800.00</payable_amount>
      <tax_category>S</tax_category>
      <line_items>
        <item>
          <description>Item 1</description>
          <quantity>2</quantity>
          <unit_price>5000.00</unit_price>
          <line_total>10000.00</line_total>
        </item>
      </line_items>
    </Invoice>
    """

    sample_invalid = """
    <Invoice>
      <invoice_id></invoice_id>
      <issue_date>2027-08-01</issue_date>
      <seller_name></seller_name>
      <buyer_name>Buyer_9</buyer_name>
      <currency_code>XYZ</currency_code>
      <taxable_amount>5000.00</taxable_amount>
      <tax_amount>2500.00</tax_amount>
      <payable_amount>7500.00</payable_amount>
      <tax_category>E</tax_category>
    </Invoice>
    """

    print("=" * 55)
    print("XML READER — SELF TEST")
    print("=" * 55)

    print("\n[1] Valid invoice:")
    result = parse_invoice_xml(sample_xml)
    for k, v in result.items():
        if k != "line_items":
            print(f"  {k:<25} {v}")
    print(f"  {'line_items':<25} {result['line_items']}")

    print("\n[2] Invalid invoice (missing fields, future date, bad currency):")
    result2 = parse_invoice_xml(sample_invalid)
    for k, v in result2.items():
        if k != "line_items":
            flag = " ⚠" if v is None or v == "" else ""
            print(f"  {k:<25} {v}{flag}")

    print("\n✅ XML Reader ready — returns clean dict for executor")
