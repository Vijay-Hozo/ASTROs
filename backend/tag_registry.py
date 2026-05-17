CANONICAL_FIELDS = {
    "tax_amount", "taxable_amount", "payable_amount",
    "invoice_id", "seller_name", "buyer_name", "issue_date",
    "currency_code", "tax_category", "tax_exemption_reason",
    "buyer_vat", "purchase_order",
}

TAG_REGISTRY: dict[str, str | None] = {
    # exact canonical matches
    "tax_amount": "tax_amount",
    "taxable_amount": "taxable_amount",
    "payable_amount": "payable_amount",
    "invoice_id": "invoice_id",
    "seller_name": "seller_name",
    "buyer_name": "buyer_name",
    "issue_date": "issue_date",
    "currency_code": "currency_code",
    "tax_category": "tax_category",
    "tax_exemption_reason": "tax_exemption_reason",
    "buyer_vat": "buyer_vat",
    "purchase_order": "purchase_order",

    # numeric synonyms
    "TaxAmount": "tax_amount",
    "GSTAmount": "tax_amount",
    "gst_amount": "tax_amount",
    "TaxableValue": "taxable_amount",
    "BaseAmount": "taxable_amount",
    "GrossTotal": "payable_amount",
    "AmountDue": "payable_amount",
    "NetPayable": "payable_amount",
    "TotalDue": "payable_amount",
    "total_amount": "payable_amount",
    "invoice_total": "payable_amount",

    # id synonyms
    "InvoiceNo": "invoice_id",
    "InvoiceNumber": "invoice_id",
    "invoice_no": "invoice_id",
    "invoice_number": "invoice_id",

    # date synonyms
    "InvoiceDate": "issue_date",
    "IssueDate": "issue_date",
    "invoice_date": "issue_date",

    # name synonyms
    "VendorName": "seller_name",
    "SupplierName": "seller_name",
    "vendor_name": "seller_name",
    "supplier_name": "seller_name",
    "CustomerName": "buyer_name",
    "customer_name": "buyer_name",

    # vat synonyms
    "BuyerGSTIN": "buyer_vat",
    "GSTIN": "buyer_vat",
    "gstin": "buyer_vat",
    "buyer_gstin": "buyer_vat",
    "gst_number": "buyer_vat",

    # currency synonyms
    "CurrencyCode": "currency_code",
    "Currency": "currency_code",

    # po synonyms
    "PONumber": "purchase_order",
    "PurchaseOrderNo": "purchase_order",
    "po_number": "purchase_order",

    # known unmappable — will be shown as amber chips
    # user must write rule using exact tag, XSLT queries directly
    "FreightCharges": None,
    "freight_charges": None,
    "RetentionAmount": None,
    "StampDuty": None,
    "Discount": None,
    "discount_amount": None,
    "LineItemTotal": None,
    "line_total": None,
    "seller_ph": None,
    "seller_phone": None,
    "phn_num": None,
    "phone": None,
    "seller_address": None,
    "buyer_address": None,
}

def resolve_tag(tag: str) -> tuple[str | None, float, list[str]]:
    """
    Returns (canonical_field, confidence, warnings).
    Resolution order: exact → case-insensitive → unknown.
    """
    # 1. exact match
    if tag in TAG_REGISTRY:
        mapped = TAG_REGISTRY[tag]
        if mapped is None:
            return None, 0.0, [
                f"'{tag}' has no standard field mapping.",
                "It will be queried directly from your XML using its exact tag name.",
            ]
        return mapped, 1.0, []

    # 2. case-insensitive match
    lower = tag.lower()
    for k, v in TAG_REGISTRY.items():
        if k.lower() == lower and v is not None:
            return v, 0.9, [f"'{tag}' matched '{k}' → mapped to '{v}'"]

    # 3. completely unknown
    return None, 0.0, [
        f"'{tag}' is not in the tag registry.",
        "It will be treated as a direct XML tag.",
        "If this resolves correctly, it will be added to the registry.",
    ]

def register_resolved_tag(raw_tag: str, canonical: str) -> None:
    """Call after LLM or user confirms a tag mapping."""
    if canonical in CANONICAL_FIELDS:
        TAG_REGISTRY[raw_tag] = canonical
