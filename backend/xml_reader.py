"""
XML Reader — parses an invoice XML file or string into a clean Python dict.
The executor will consume this dict to run rules against.
Uses defusedxml to prevent XXE attacks and other XML vulnerabilities.
"""

from defusedxml import ElementTree as ET
from datetime import datetime
from typing import Optional


def parse_invoice_xml(source: str) -> dict:
    """
    Accepts either:
      - A file path string ending in .xml
      - A raw XML string
    
    Safely parses XML using defusedxml to prevent XXE and other vulnerabilities.
    Returns a clean dict with all invoice fields.
    Missing fields return None — executor handles None safely.
    """
    # Parse XML first
    root = None
    try:
        # Detect if input is XML content or file path
        source_str = source.strip()
        if source_str.startswith("<"):
            # Direct XML string
            root = ET.fromstring(source_str)
        else:
            # File path
            try:
                tree = ET.parse(source)
                root = tree.getroot()
            except FileNotFoundError:
                return {"_parse_error": f"File not found: {source}"}
    except ET.ParseError as e:
        return {"_parse_error": f"XML parse error: {str(e)[:100]}"}
    except ValueError as e:
        return {"_parse_error": f"Invalid XML content: {str(e)[:100]}"}
    except Exception as e:
        return {"_parse_error": f"XML processing error: {str(e)[:100]}"}

    # If parsing failed, root will be None
    if root is None:
        return {"_parse_error": "Failed to parse XML: root element is None"}

    def get(tag: str) -> Optional[str]:
        """Safe tag getter with namespace support."""
        el = root.find(tag)
        if el is None:
            # Try with common namespaces
            for ns in ["{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}", 
                       "{urn:un:unece:uncefact:data:standard:UnqualifiedDataTypes:100}",
                       ""]:
                el = root.find(f"{ns}{tag}")
                if el is not None:
                    break
        
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
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(val.split("T")[0], fmt)  # Handle ISO format
            except (ValueError, AttributeError):
                continue
        return None  # unparseable date

    # ── Line items ────────────────────────────────────────────────────────────
    line_items = []
    line_items_el = root.find("line_items") if root is not None else None
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


# ── Helper class for evaluator integration ────────────────────────────────────

class XMLReader:
    """Class-based wrapper for XML parsing to support evaluator.py integration."""
    
    def extract(self, xml_content: str) -> dict:
        """Extract fields from XML content.
        
        Args:
            xml_content: Raw XML string or file path
            
        Returns:
            Dictionary of extracted invoice fields
        """
        return parse_invoice_xml(xml_content)
    
    def parse(self, xml_content: str) -> dict:
        """Alias for extract() for compatibility."""
        return self.extract(xml_content)


import xml.etree.ElementTree as ET
import re

def extract_xml_tags(xml_content: str) -> dict:
    """
    Parse an XML string and extract all leaf node tags
    with sample values, inferred types, and xpath.
    No LLM involved. Pure deterministic extraction.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return {"error": f"Invalid XML: {str(e)}", "tags": [], "unknown_tags": [], "known_tags": []}

    from tag_registry import TAG_REGISTRY

    seen = {}  # tag → entry, deduplicated

    def infer_type(value: str) -> str:
        try:
            float(value)
            return "numeric"
        except ValueError:
            pass
        if re.match(r"\d{4}-\d{2}-\d{2}", value):
            return "date"
        return "string"

    def walk(element, path=""):
        current_path = f"{path}/{element.tag}"
        text = (element.text or "").strip()
        if text and element.tag not in seen:
            seen[element.tag] = {
                "tag": element.tag,
                "xpath": f"/Invoice/{element.tag}",
                "sample_value": text[:60],
                "inferred_type": infer_type(text),
                "canonical_field": TAG_REGISTRY.get(element.tag),
            }
        for child in element:
            walk(child, current_path)

    walk(root)

    all_tags = list(seen.values())
    return {
        "tags": all_tags,
        "known_tags": [t for t in all_tags if t["canonical_field"] is not None],
        "unknown_tags": [t for t in all_tags if t["canonical_field"] is None],
        "total": len(all_tags),
    }
