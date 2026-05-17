CANONICAL_FIELDS = {
    "tax_amount", "taxable_amount", "payable_amount",
    "invoice_id", "seller_name", "buyer_name", "issue_date",
    "currency_code", "tax_category", "tax_exemption_reason",
    "buyer_vat", "purchase_order",
}

# Deterministic lookup — grows over time as new tags are resolved
TAG_REGISTRY: dict[str, str | None] = {
    # exact
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

    # vendor synonyms — high confidence
    "TaxAmount": "tax_amount",
    "GSTAmount": "tax_amount",
    "TaxableValue": "taxable_amount",
    "BaseAmount": "taxable_amount",
    "GrossTotal": "payable_amount",
    "AmountDue": "payable_amount",
    "NetPayable": "payable_amount",
    "TotalDue": "payable_amount",
    "InvoiceNo": "invoice_id",
    "InvoiceNumber": "invoice_id",
    "InvoiceDate": "issue_date",
    "IssueDate": "issue_date",
    "VendorName": "seller_name",
    "SupplierName": "seller_name",
    "CustomerName": "buyer_name",
    "BuyerGSTIN": "buyer_vat",
    "GSTIN": "buyer_vat",
    "CurrencyCode": "currency_code",
    "PONumber": "purchase_order",
    "PurchaseOrderNo": "purchase_order",
    "ExemptionReason": "tax_exemption_reason",

    # common short synonyms / abbreviations
    "tax_amt": "tax_amount",
    "taxable_amt": "taxable_amount",
    "payable_amt": "payable_amount",
    "inv_id": "invoice_id",
    "seller_nm": "seller_name",
    "buyer_nm": "buyer_name",
    "issue_dt": "issue_date",
    "currency": "currency_code",
    "tax_cat": "tax_category",
    "exemption_reason": "tax_exemption_reason",
    "vat": "buyer_vat",
    "po": "purchase_order",

    # known unmappable — send to LLM for judgment
    "FreightCharges": None,
    "RetentionAmount": None,
    "StampDuty": None,
    "Discount": None,
    "LineItemTotal": None,
}

def resolve_tag(tag: str) -> tuple[str | None, float, list[str]]:
    """
    Returns (canonical_field, confidence, warnings).
    canonical_field is None if unmappable.
    """
    # Normalize input
    tag_clean = tag.strip()

    # 1. Direct hit
    if tag_clean in TAG_REGISTRY:
        mapped = TAG_REGISTRY[tag_clean]
        if mapped is None:
            return None, 0.0, [
                f"XML tag '{tag_clean}' is known but has no supported field mapping.",
                f"This tag will be sent to LLM for best-effort resolution.",
            ]
        return mapped, 1.0, []

    # 2. Case-insensitive hit
    lower = tag_clean.lower()
    for k, v in TAG_REGISTRY.items():
        if k.lower() == lower:
            if v is None:
                return None, 0.0, [
                    f"XML tag '{tag_clean}' matched '{k}' case-insensitively, which has no supported mapping.",
                ]
            confidence = 0.9
            return v, confidence, [f"'{tag_clean}' matched '{k}' case-insensitively → {v}"]

    # 3. Fuzzy matching fallback using standard difflib (Levenshtein-like)
    import difflib
    candidates = list(CANONICAL_FIELDS) + [k for k, v in TAG_REGISTRY.items() if v is not None]
    best_matches = difflib.get_close_matches(tag_clean, candidates, n=1, cutoff=0.7)
    
    if best_matches:
        match = best_matches[0]
        mapped = match if match in CANONICAL_FIELDS else TAG_REGISTRY[match]
        if mapped:
            return mapped, 0.8, [
                f"'{tag_clean}' did not match directly. Fuzzy matched to '{match}' (confidence 0.8) → {mapped}."
            ]

    # 4. Unknown — fall through to LLM
    return None, 0.0, [
        f"XML tag '{tag_clean}' is not in the tag registry.",
        f"Sending to LLM for semantic resolution.",
        f"If resolved correctly, add it to TAG_REGISTRY in tag_registry.py.",
    ]

def register_resolved_tag(raw_tag: str, canonical: str) -> None:
    """Call this after LLM successfully resolves an unknown tag."""
    if canonical in CANONICAL_FIELDS:
        TAG_REGISTRY[raw_tag] = canonical
