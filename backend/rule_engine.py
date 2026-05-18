"""
rule_engine.py — deterministic multi-rule parser and XSLT generator.

The module accepts a single natural-language input that may contain multiple
rules separated by newlines or commas, converts each clause into a structured
rule object, and emits one XSLT document with one named template per rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from html import escape
import json
import re
from typing import Any, Callable
from xml.sax.saxutils import escape as xml_escape

SUPPORTED_FIELD_ALIASES: dict[str, str] = {
    "seller": "seller_name",
    "seller name": "seller_name",
    "vendor name": "seller_name",
    "buyer": "buyer_name",
    "buyer name": "buyer_name",
    "customer name": "buyer_name",
    "invoice date": "issue_date",
    "issue date": "issue_date",
    "date of invoice": "issue_date",
    "invoice id": "invoice_id",
    "invoice number": "invoice_id",
    "invoice no": "invoice_id",
    "invoice no.": "invoice_id",
    "invoice_id": "invoice_id",
    "payable amount": "payable_amount",
    "total amount": "payable_amount",
    "amount due": "payable_amount",
    "tax amount": "tax_amount",
    "taxable amount": "taxable_amount",
    "tax category": "tax_category",
    "tax exemption reason": "tax_exemption_reason",
    "buyer vat": "buyer_vat",
    "buyer gst": "buyer_vat",
    "gst number": "buyer_vat",
    "purchase order": "purchase_order",
    "purchase order number": "purchase_order",
    "currency": "currency_code",
    "currency code": "currency_code",
}

CANONICAL_FIELDS = {
    "tax_amount",
    "taxable_amount",
    "payable_amount",
    "invoice_id",
    "seller_name",
    "buyer_name",
    "issue_date",
    "currency_code",
    "tax_category",
    "tax_exemption_reason",
    "buyer_vat",
    "purchase_order",
}

RuleParser = Callable[[str], dict[str, Any] | None]


@dataclass
class ParsedRuleObject:
    rule_type: str
    field: str | None = None
    operator: str | None = None
    value: Any = None
    min: float | None = None
    max: float | None = None
    constraint: str | None = None
    reference_field: str | None = None
    expression: str | None = None
    rate: float | None = None
    tolerance: float | None = 0.01
    description: str = ""
    confidence: float = 1.0
    warnings: list[str] = dataclass_field(default_factory=list)
    condition_field: str | None = None
    condition_value: str | None = None
    pattern: str | None = None
    allowed_values: list[str] | None = None
    order: int | None = None
    is_direct_tag: bool | None = None
    xpath: str | None = None

    def as_dict(self) -> dict[str, Any]:
        data = {
            "rule_type": self.rule_type,
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "min": self.min,
            "max": self.max,
            "constraint": self.constraint,
            "reference_field": self.reference_field,
            "expression": self.expression,
            "rate": self.rate,
            "tolerance": self.tolerance,
            "description": self.description,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "condition_field": self.condition_field,
            "condition_value": self.condition_value,
            "pattern": self.pattern,
            "allowed_values": self.allowed_values,
            "order": self.order,
            "is_direct_tag": self.is_direct_tag,
            "xpath": self.xpath,
        }
        return {key: value for key, value in data.items() if value is not None}


@dataclass
class ParsedRuleSet:
    rule_text: str
    rules: list[dict[str, Any]]
    warnings: list[str] = dataclass_field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        primary = self.rules[0] if self.rules else None
        return {
            "rule_text": self.rule_text,
            "parsed_rule": primary,
            "parsed_rules": self.rules,
            "rule_count": len(self.rules),
            "warnings": self.warnings,
        }


_SPLIT_PATTERN = re.compile(r"\n+|,\s*(?=[A-Za-z(])")
_CONJUNCTION_SPLIT_PATTERN = re.compile(
    r"(?<![a-z_])\s+(?:and|then)\s+(?!(?:[a-z_]+\s+and\s+)?(?:[a-z_]+\s+)*(?:must not be|should not be|cannot be)\s+the same)(?=(?:[A-Za-z][\w\s-]*?)\s+(?:is|required|must be|should be|cannot be|can't be|must not be|should not be|is not|must|should)\b)",
    re.IGNORECASE,
)
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_QUOTED_PATTERN = re.compile(r'"([^"]+)"|\'([^\']+)\'')

_NUMBER_WORDS: dict[str, float] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().rstrip(".;")).strip()


def _split_rule_input(rule_text: str) -> list[str]:
    parts = [part.strip() for part in _SPLIT_PATTERN.split(rule_text) if part.strip()]
    merged: list[str] = []
    for part in parts:
        if merged and len(part) <= 3:
            merged[-1] = f"{merged[-1]}, {part}"
        else:
            merged.append(part)
    expanded: list[str] = []
    for part in merged:
        expanded.extend([segment.strip() for segment in _CONJUNCTION_SPLIT_PATTERN.split(part) if segment.strip()])
    return expanded


def _canonicalize_field(raw_field: str) -> tuple[str | None, list[str]]:
    field = _clean_text(raw_field).lower()
    warnings: list[str] = []
    if field in CANONICAL_FIELDS:
        return field, warnings
    if field in SUPPORTED_FIELD_ALIASES:
        canonical = SUPPORTED_FIELD_ALIASES[field]
        if canonical != field:
            warnings.append(f"'{raw_field}' mapped to '{canonical}'")
        return canonical, warnings

    normalized = field.replace("_", " ")
    if normalized in SUPPORTED_FIELD_ALIASES:
        canonical = SUPPORTED_FIELD_ALIASES[normalized]
        warnings.append(f"'{raw_field}' mapped to '{canonical}'")
        return canonical, warnings

    closest = _closest_field(field)
    warnings.append(f"Unrecognized field: '{raw_field}'")
    if closest:
        warnings.append(f"Closest supported field: '{closest}'")
        warnings.append(f"Suggested rewrite: '{raw_field} is required' -> '{closest} is required'")
    return None, warnings


def _closest_field(raw_field: str) -> str | None:
    candidates = list(CANONICAL_FIELDS)
    best = None
    best_score = 0.0
    for candidate in candidates:
        score = _similarity_score(raw_field, candidate)
        if score > best_score:
            best = candidate
            best_score = score
    return best if best_score >= 0.35 else None


def _similarity_score(left: str, right: str) -> float:
    left_parts = set(re.split(r"[^a-z0-9]+", left.lower())) - {""}
    right_parts = set(re.split(r"[^a-z0-9]+", right.lower())) - {""}
    if not left_parts or not right_parts:
        return 0.0
    overlap = len(left_parts & right_parts)
    total = len(left_parts | right_parts)
    return overlap / total if total else 0.0


def _parse_number(value: str) -> float:
    cleaned = value.strip().lower()
    if cleaned in _NUMBER_WORDS:
        return float(_NUMBER_WORDS[cleaned])
    return float(cleaned)


def _parse_required(clause: str, order: int) -> dict[str, Any] | None:
    match = re.match(
        r"^(?P<field>.+?)\s+(?:is|required|must be|should be|should|cannot be|can't be)?\s*(?:required|mandatory|present|non-empty|not empty|non empty|not null|not blank|must exist|should exist|cannot be empty|must not be empty|should not be empty)$",
        clause,
        re.IGNORECASE,
    )
    if not match:
        return None
    field, warnings = _canonicalize_field(match.group("field"))
    if not field:
        return _unsupported_rule(clause, warnings, order)
    return ParsedRuleObject(
        rule_type="required_field",
        field=field,
        description=clause,
        confidence=0.98,
        warnings=warnings,
        order=order,
    ).as_dict()


def _parse_conditional_required(clause: str, order: int) -> dict[str, Any] | None:
    match = re.match(
        r"^(?:if|when)\s+(?P<condition_field>.+?)\s+is\s+(?P<condition_value>.+?),\s*(?P<target>.+?)\s+(?:is|required|must be|should be|should)\s+(?:required|mandatory|present|non-empty|not empty|non null|not null)$",
        clause,
        re.IGNORECASE,
    )
    if not match:
        return None
    condition_field, condition_warnings = _canonicalize_field(match.group("condition_field"))
    target_field, target_warnings = _canonicalize_field(match.group("target"))
    warnings = condition_warnings + target_warnings
    if not target_field:
        return _unsupported_rule(clause, warnings, order)
    return ParsedRuleObject(
        rule_type="conditional_required",
        field=target_field,
        condition_field=condition_field,
        condition_value=_clean_text(match.group("condition_value")),
        description=clause,
        confidence=0.94,
        warnings=warnings,
        order=order,
    ).as_dict()


def _parse_numeric_comparison(clause: str, order: int) -> dict[str, Any] | None:
    number_pattern = r"(?P<value>-?\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
    patterns = [
        (rf"^(?P<field>.+?)\s+(?:should be|must be|is|should|must)\s+greater than\s+{number_pattern}$", ">"),
        (rf"^(?P<field>.+?)\s+(?:should be|must be|is|should|must)\s+less than\s+{number_pattern}$", "<"),
        (rf"^(?P<field>.+?)\s+(?:should be|must be|is|should|must)\s+at least\s+{number_pattern}$", ">="),
        (rf"^(?P<field>.+?)\s+(?:should be|must be|is|should|must)\s+at most\s+{number_pattern}$", "<="),
        (rf"^(?P<field>.+?)\s+(?:should be|must be|is|should|must)\s+equal to\s+{number_pattern}$", "=="),
        (rf"^(?P<field>.+?)\s+(?:should be|must be|is|should|must)\s+greater than or equal to\s+{number_pattern}$", ">="),
        (rf"^(?P<field>.+?)\s+(?:should be|must be|is|should|must)\s+less than or equal to\s+{number_pattern}$", "<="),
    ]
    # Add "!=" (not equal) patterns
    patterns.append((rf"^(?P<field>.+?)\s+(?:should not be|must not be|is not|cannot be)\s+equal to\s+{number_pattern}$", "!="))
    patterns.append((rf"^(?P<field>.+?)\s+(?:should|must)\s+not\s+equal\s+{number_pattern}$", "!="))
    
    for pattern, operator in patterns:
        match = re.match(pattern, clause, re.IGNORECASE)
        if not match:
            continue
        field, warnings = _canonicalize_field(match.group("field"))
        if not field:
            return _unsupported_rule(clause, warnings, order)
        return ParsedRuleObject(
            rule_type="numeric_comparison",
            field=field,
            operator=operator,
            value=_parse_number(match.group("value")),
            description=clause,
            confidence=0.96,
            warnings=warnings,
            order=order,
        ).as_dict()

    between = re.match(
        r"^(?P<field>.+?)\s+(?:should be|must be|is|should|must)\s+between\s+(?P<min>-?\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten)\s+and\s+(?P<max>-?\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten)$",
        clause,
        re.IGNORECASE,
    )
    if between:
        field, warnings = _canonicalize_field(between.group("field"))
        if not field:
            return _unsupported_rule(clause, warnings, order)
        return ParsedRuleObject(
            rule_type="numeric_comparison",
            field=field,
            operator="between",
            min=_parse_number(between.group("min")),
            max=_parse_number(between.group("max")),
            description=clause,
            confidence=0.95,
            warnings=warnings,
            order=order,
        ).as_dict()

    # Cross-field numeric comparison: "payable_amount must be greater than taxable_amount"
    cross_match = re.match(
        r"^(?P<field>.+?)\s+(?:should|must)(?:\s+not)?\s+(?:be|be)?\s*"
        r"(?P<op>greater than|less than|greater than or equal to|"
        r"less than or equal to|equal to|not equal to)\s+"
        r"(?P<ref_field>[a-z][a-z_]+)$",
        clause,
        re.IGNORECASE,
    )
    if cross_match:
        field, warnings = _canonicalize_field(cross_match.group("field"))
        ref_field, ref_warnings = _canonicalize_field(cross_match.group("ref_field"))
        warnings.extend(ref_warnings)
        op_word = cross_match.group("op").lower()
        op_map = {
            "greater than": ">",
            "less than": "<",
            "greater than or equal to": ">=",
            "less than or equal to": "<=",
            "equal to": "==",
            "not equal to": "!=",
        }
        operator = op_map.get(op_word, ">")
        if not field or not ref_field:
            return _unsupported_rule(clause, warnings, order)
        return ParsedRuleObject(
            rule_type="cross_field_validation",
            field=field,
            reference_field=ref_field,
            operator=operator,
            description=clause,
            confidence=0.93,
            warnings=warnings,
            order=order,
        ).as_dict()

    return None


def _parse_date_validation(clause: str, order: int) -> dict[str, Any] | None:
    patterns = [
        (r"^(?P<field>.+?)\s+(?:cannot be|must not be|should not be|is not)\s+in\s+the\s+future$", "not_future"),
        (r"^(?P<field>.+?)\s+(?:cannot be|must not be|should not be|is not)\s+in\s+the\s+past$", "not_past"),
        (r"^(?P<field>.+?)\s+(?:must be|should be|is)\s+after\s+(?P<reference_field>.+)$", "after_field"),
        (r"^(?P<field>.+?)\s+(?:must be|should be|is)\s+before\s+(?P<reference_field>.+)$", "before_field"),
    ]
    for pattern, constraint in patterns:
        match = re.match(pattern, clause, re.IGNORECASE)
        if not match:
            continue
        field, warnings = _canonicalize_field(match.group("field"))
        if not field:
            return _unsupported_rule(clause, warnings, order)
        reference_field = None
        if match.groupdict().get("reference_field"):
            reference_field, ref_warnings = _canonicalize_field(match.group("reference_field"))
            warnings.extend(ref_warnings)
        return ParsedRuleObject(
            rule_type="date_validation",
            field=field,
            constraint=constraint,
            reference_field=reference_field,
            description=clause,
            confidence=0.97,
            warnings=warnings,
            order=order,
        ).as_dict()
    return None


def _parse_amount_calculation(clause: str, order: int) -> dict[str, Any] | None:
    percent_match = re.match(
        r"^(?P<field>.+?)\s+(?:must be|should be|is)\s+(?P<rate>\d+(?:\.\d+)?)%\s+of\s+(?P<base_field>.+)$",
        clause,
        re.IGNORECASE,
    )
    if percent_match:
        field, warnings = _canonicalize_field(percent_match.group("field"))
        base_field, base_warnings = _canonicalize_field(percent_match.group("base_field"))
        warnings.extend(base_warnings)
        if not field or not base_field:
            return _unsupported_rule(clause, warnings, order)
        return ParsedRuleObject(
            rule_type="amount_calculation",
            field=field,
            reference_field=base_field,
            rate=_parse_number(percent_match.group("rate")),
            operator="percentage",
            description=clause,
            confidence=0.96,
            warnings=warnings,
            order=order,
        ).as_dict()

    sum_match = re.match(
        r"^(?P<field>.+?)\s+(?:must equal|should equal|equals|must be equal to|should be equal to|must be|should be|is)\s+equal\s+to\s+(?P<left>.+?)\s+(?:\+|plus)\s+(?P<right>.+)$",
        clause,
        re.IGNORECASE,
    )
    if not sum_match:
        sum_match = re.match(
            r"^(?P<field>.+?)\s+(?:must equal|should equal|equals|must be equal to|should be equal to)\s+(?P<left>.+?)\s+(?:\+|plus)\s+(?P<right>.+)$",
            clause,
            re.IGNORECASE,
        )
    if sum_match:
        field, warnings = _canonicalize_field(sum_match.group("field"))
        left_field, left_warnings = _canonicalize_field(sum_match.group("left"))
        right_field, right_warnings = _canonicalize_field(sum_match.group("right"))
        warnings.extend(left_warnings)
        warnings.extend(right_warnings)
        if not field or not left_field or not right_field:
            return _unsupported_rule(clause, warnings, order)
        return ParsedRuleObject(
            rule_type="amount_calculation",
            field=field,
            expression=f"{left_field} + {right_field}",
            operator="sum",
            description=clause,
            confidence=0.95,
            warnings=warnings,
            order=order,
        ).as_dict()

    multiply_match = re.match(
        r"^(?P<field>.+?)\s+(?:must equal|should equal|equals|must be equal to|must be)\s+(?P<left>.+?)\s+(?:\*|multiplied by|times)\s+(?P<right>.+)$",
        clause,
        re.IGNORECASE,
    )
    if multiply_match:
        field, warnings = _canonicalize_field(multiply_match.group("field"))
        left_field, left_warnings = _canonicalize_field(multiply_match.group("left"))
        right_field, right_warnings = _canonicalize_field(multiply_match.group("right"))
        warnings.extend(left_warnings)
        warnings.extend(right_warnings)
        if not field or not left_field or not right_field:
            return _unsupported_rule(clause, warnings, order)
        return ParsedRuleObject(
            rule_type="amount_calculation",
            field=field,
            expression=f"{left_field} * {right_field}",
            operator="multiply",
            description=clause,
            confidence=0.95,
            warnings=warnings,
            order=order,
        ).as_dict()

    return None


def _parse_not_same(clause: str, order: int) -> dict[str, Any] | None:
    """Parse 'field1 and field2 must not be the same' patterns."""
    match = re.match(
        r"^(?P<field1>.+?)\s+and\s+(?P<field2>.+?)\s+"
        r"(?:must not be|should not be|cannot be)\s+the same$",
        clause,
        re.IGNORECASE,
    )
    if not match:
        return None
    field1, w1 = _canonicalize_field(match.group("field1"))
    field2, w2 = _canonicalize_field(match.group("field2"))
    warnings = w1 + w2
    if not field1 or not field2:
        return _unsupported_rule(clause, warnings, order)
    return ParsedRuleObject(
        rule_type="cross_field_validation",
        field=field1,
        reference_field=field2,
        operator="!=",
        description=clause,
        confidence=0.94,
        warnings=warnings,
        order=order,
    ).as_dict()


def _parse_string_length(clause: str, order: int) -> dict[str, Any] | None:
    """Parse 'field must contain exactly N characters' patterns."""
    match = re.match(
        r"^(?P<field>.+?)\s+(?:must contain|should contain|must have|has)\s+"
        r"exactly\s+(?P<length>\d+)\s+characters?$",
        clause,
        re.IGNORECASE,
    )
    if not match:
        return None
    field, warnings = _canonicalize_field(match.group("field"))
    if not field:
        return _unsupported_rule(clause, warnings, order)
    length = int(match.group("length"))
    return ParsedRuleObject(
        rule_type="regex_validation",
        field=field,
        pattern=f"^.{{{length}}}$",
        description=clause,
        confidence=0.93,
        warnings=warnings,
        order=order,
    ).as_dict()


def _parse_regex_validation(clause: str, order: int) -> dict[str, Any] | None:
    match = re.match(
        r"^(?P<field>.+?)\s+(?:must|should|is required to)?\s*match(?:es)?\s+(?:regex\s*)?(?P<pattern>.+)$",
        clause,
        re.IGNORECASE,
    )
    if not match:
        return None
    field, warnings = _canonicalize_field(match.group("field"))
    if not field:
        return _unsupported_rule(clause, warnings, order)
    pattern = _clean_text(match.group("pattern"))
    return ParsedRuleObject(
        rule_type="regex_validation",
        field=field,
        pattern=pattern,
        description=clause,
        confidence=0.92,
        warnings=warnings,
        order=order,
    ).as_dict()


def _parse_enum_validation(clause: str, order: int) -> dict[str, Any] | None:
    match = re.match(
        r"^(?P<field>.+?)\s+(?:must be|should be|is)\s+(?:one of|in)\s+(?P<values>.+)$",
        clause,
        re.IGNORECASE,
    )
    if not match:
        return None
    field, warnings = _canonicalize_field(match.group("field"))
    if not field:
        return _unsupported_rule(clause, warnings, order)
    raw_values = re.split(r",|\bor\b", match.group("values"), flags=re.IGNORECASE)
    values = [value.strip().strip(".") for value in raw_values if value.strip()]
    return ParsedRuleObject(
        rule_type="enum_validation",
        field=field,
        allowed_values=values,
        description=clause,
        confidence=0.93,
        warnings=warnings,
        order=order,
    ).as_dict()


def _parse_cross_field_validation(clause: str, order: int) -> dict[str, Any] | None:
    patterns = [
        (r"^(?P<field>.+?)\s+(?:must be|should be|is)\s+the same as\s+(?P<reference_field>.+)$", "eq"),
        (r"^(?P<field>.+?)\s+(?:must be|should be|is)\s+equal to\s+(?P<reference_field>.+)$", "eq"),
        (r"^(?P<field>.+?)\s+(?:must not exceed|should not exceed|cannot exceed)\s+(?P<reference_field>.+)$", "lte"),
        (r"^(?P<field>.+?)\s+(?:must be greater than|should be greater than)\s+(?P<reference_field>.+)$", "gt"),
    ]
    for pattern, operator in patterns:
        match = re.match(pattern, clause, re.IGNORECASE)
        if not match:
            continue
        field, warnings = _canonicalize_field(match.group("field"))
        reference_field, reference_warnings = _canonicalize_field(match.group("reference_field"))
        warnings.extend(reference_warnings)
        if not field or not reference_field:
            return _unsupported_rule(clause, warnings, order)
        return ParsedRuleObject(
            rule_type="cross_field_validation",
            field=field,
            reference_field=reference_field,
            operator=operator,
            description=clause,
            confidence=0.91,
            warnings=warnings,
            order=order,
        ).as_dict()
    return None


def _unsupported_rule(clause: str, warnings: list[str], order: int) -> dict[str, Any]:
    if not warnings:
        warnings = ["Rule is not recognized by the deterministic parser."]
    return ParsedRuleObject(
        rule_type="unsupported",
        field=None,
        description=clause,
        confidence=0.0,
        warnings=warnings,
        order=order,
    ).as_dict()


PARSERS: list[tuple[str, RuleParser]] = [
    ("conditional_required", _parse_conditional_required),
    ("required_field", _parse_required),
    ("numeric_comparison", _parse_numeric_comparison),
    ("date_validation", _parse_date_validation),
    ("amount_calculation", _parse_amount_calculation),
    ("not_same", _parse_not_same),
    ("string_length", _parse_string_length),
    ("regex_validation", _parse_regex_validation),
    ("enum_validation", _parse_enum_validation),
    ("cross_field_validation", _parse_cross_field_validation),
]


def parse_rule_clause(clause: str, order: int) -> dict[str, Any]:
    normalized = _clean_text(clause)
    for _, parser in PARSERS:
        parsed = parser(normalized, order)
        if parsed is not None:
            return parsed
    field_match = re.match(r"^(?P<field>.+?)\s+", normalized)
    warnings = ["Unable to classify rule clause using supported patterns."]
    if field_match:
        warnings.append(f"Unrecognized field phrase: '{field_match.group('field')}'")
        closest = _closest_field(field_match.group("field"))
        if closest:
            warnings.append(f"Closest supported field: '{closest}'")
    return _unsupported_rule(normalized, warnings, order)


def parse_rule_text(rule_text: str) -> ParsedRuleSet:
    if not rule_text or not rule_text.strip():
        raise ValueError("rule_text cannot be empty")

    clauses = _split_rule_input(rule_text.strip())
    parsed_rules = [parse_rule_clause(clause, index + 1) for index, clause in enumerate(clauses)]
    warnings: list[str] = []
    for rule in parsed_rules:
        warnings.extend(rule.get("warnings", []))
    return ParsedRuleSet(rule_text=rule_text.strip(), rules=parsed_rules, warnings=warnings)


def _xslt_safe(value: str | None) -> str:
    return xml_escape(value or "", {'"': '&quot;', "'": '&apos;'})


def _make_rule_template(rule: dict[str, Any], index: int) -> str:
    rule_type = rule.get("rule_type", "unsupported")
    field = rule.get("field") or ""
    field_xpath = f"/Invoice/{field}" if field else ""
    title = _xslt_safe(rule.get("description") or field or rule_type)
    rule_name = f"rule-{index}"

    if rule_type == "required_field":
        return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"required_field\" field=\"{_xslt_safe(field)}\">\n      <xsl:choose>\n        <xsl:when test=\"not({field_xpath}) or normalize-space(string({field_xpath})) = ''\">\n          <status>FAIL</status>\n          <message>{title} is required</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} is present</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""

    if rule_type == "conditional_required":
        condition_field = rule.get("condition_field") or ""
        condition_value = rule.get("condition_value") or ""
        condition_xpath = f"/Invoice/{condition_field}"
        return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"conditional_required\" field=\"{_xslt_safe(field)}\">\n      <xsl:choose>\n        <xsl:when test=\"normalize-space(string({condition_xpath})) = '{_xslt_safe(condition_value)}' and (not({field_xpath}) or normalize-space(string({field_xpath})) = '')\">\n          <status>FAIL</status>\n          <message>{title} is required when {condition_field} is {condition_value}</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} passes conditional requirement</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""

    if rule_type == "numeric_comparison":
        operator = rule.get("operator")
        if operator == "between":
            lower = rule.get("min")
            upper = rule.get("max")
            return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"numeric_comparison\" field=\"{_xslt_safe(field)}\">\n      <xsl:variable name=\"actual\" select=\"number({field_xpath})\"/>\n      <xsl:choose>\n        <xsl:when test=\"not($actual &gt;= {lower} and $actual &lt;= {upper})\">\n          <status>FAIL</status>\n          <message>{title} must be between {lower} and {upper}</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} is within range</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""
        op_map = {
            ">": ">",
            "<": "&lt;",
            ">=": ">=",
            "<=": "&lt;=",
            "==": "=",
            "!=": "!=",
        }
        op_text = {">": "greater than", "<": "less than", ">=": "greater than or equal to", "<=": "less than or equal to", "==": "equal to", "!=": "not equal to"}.get(operator, "compare against")
        actual_operator = op_map.get(operator, ">")
        value = rule.get("value")
        return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"numeric_comparison\" field=\"{_xslt_safe(field)}\">\n      <xsl:variable name=\"actual\" select=\"number({field_xpath})\"/>\n      <xsl:choose>\n        <xsl:when test=\"not($actual {actual_operator} {value})\">\n          <status>FAIL</status>\n          <message>{title} must be {op_text} {value}</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} passes numeric comparison</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""

    if rule_type == "date_validation":
        constraint = rule.get("constraint")
        if constraint == "not_future":
            return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"date_validation\" field=\"{_xslt_safe(field)}\">\n      <xsl:variable name=\"inv_y\" select=\"number(substring(string({field_xpath}), 1, 4))\"/>\n      <xsl:variable name=\"inv_m\" select=\"number(substring(string({field_xpath}), 6, 2))\"/>\n      <xsl:variable name=\"inv_d\" select=\"number(substring(string({field_xpath}), 9, 2))\"/>\n      <xsl:variable name=\"cur_y\" select=\"number(substring($current_date, 1, 4))\"/>\n      <xsl:variable name=\"cur_m\" select=\"number(substring($current_date, 6, 2))\"/>\n      <xsl:variable name=\"cur_d\" select=\"number(substring($current_date, 9, 2))\"/>\n      <xsl:variable name=\"is_future\" select=\"$inv_y &gt; $cur_y or ($inv_y = $cur_y and $inv_m &gt; $cur_m) or ($inv_y = $cur_y and $inv_m = $cur_m and $inv_d &gt; $cur_d)\"/>\n      <xsl:choose>\n        <xsl:when test=\"$is_future\">\n          <status>FAIL</status>\n          <message>{title} cannot be in the future</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} is not in the future</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""
        if constraint in {"after_field", "before_field"} and rule.get("reference_field"):
            reference_field = rule.get("reference_field")
            operator = ">" if constraint == "after_field" else "<"
            return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"date_validation\" field=\"{_xslt_safe(field)}\">\n      <xsl:choose>\n        <xsl:when test=\"not(string({field_xpath})) or not(string(/Invoice/{reference_field}))\">\n          <status>FAIL</status>\n          <message>{title} requires both date fields</message>\n        </xsl:when>\n        <xsl:when test=\"string({field_xpath}) {operator} string(/Invoice/{reference_field})\">\n          <status>PASS</status>\n          <message>{title} passes date comparison</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>FAIL</status>\n          <message>{title} failed date comparison</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""

    if rule_type == "amount_calculation":
        if rule.get("operator") == "percentage" and rule.get("reference_field"):
            rate = rule.get("rate")
            return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"amount_calculation\" field=\"{_xslt_safe(field)}\">\n      <xsl:variable name=\"actual\" select=\"number({field_xpath})\"/>\n      <xsl:variable name=\"expected\" select=\"number(/Invoice/{rule.get('reference_field')}) * {rate} div 100\"/>\n      <xsl:variable name=\"diff\" select=\"$actual - $expected\"/>\n      <xsl:choose>\n        <xsl:when test=\"not($diff &lt;= $tolerance and $diff &gt;= (0 - $tolerance))\">\n          <status>FAIL</status>\n          <message>{title} must equal {rate}% of {rule.get('reference_field')}</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} matches calculated amount</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""
        if rule.get("expression") and "+" in rule.get("expression"):
            left, right = [part.strip() for part in rule.get("expression", "").split("+", 1)]
            return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"amount_calculation\" field=\"{_xslt_safe(field)}\">\n      <xsl:variable name=\"actual\" select=\"number({field_xpath})\"/>\n      <xsl:variable name=\"expected\" select=\"number(/Invoice/{left}) + number(/Invoice/{right})\"/>\n      <xsl:choose>\n        <xsl:when test=\"not($actual = $expected)\">\n          <status>FAIL</status>\n          <message>{title} must equal {left} + {right}</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} matches calculated amount</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""
        if rule.get("expression") and "*" in rule.get("expression"):
            left, right = [part.strip() for part in rule.get("expression", "").split("*", 1)]
            return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"amount_calculation\" field=\"{_xslt_safe(field)}\">\n      <xsl:variable name=\"actual\" select=\"number({field_xpath})\"/>\n      <xsl:variable name=\"expected\" select=\"number(/Invoice/{left}) * number(/Invoice/{right})\"/>\n      <xsl:choose>\n        <xsl:when test=\"not($actual = $expected)\">\n          <status>FAIL</status>\n          <message>{title} must equal {left} * {right}</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} matches calculated amount</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""

    if rule_type == "regex_validation" and rule.get("pattern"):
        pattern = _xslt_safe(rule.get("pattern"))
        return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"regex_validation\" field=\"{_xslt_safe(field)}\">\n      <xsl:choose>\n        <xsl:when test=\"not(re:test(normalize-space(string({field_xpath})), '{pattern}'))\">\n          <status>FAIL</status>\n          <message>{title} must match pattern {pattern}</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} matches pattern</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""

    if rule_type == "enum_validation" and rule.get("allowed_values"):
        values = rule.get("allowed_values") or []
        conditions = " or ".join([f"normalize-space(string({field_xpath})) = '{_xslt_safe(value)}'" for value in values])
        return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"enum_validation\" field=\"{_xslt_safe(field)}\">\n      <xsl:choose>\n        <xsl:when test=\"not({conditions})\">\n          <status>FAIL</status>\n          <message>{title} must be one of {', '.join(values)}</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} is valid</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""

    if rule_type == "cross_field_validation" and rule.get("reference_field"):
        operator = rule.get("operator") or "eq"
        comparison = {
            "eq": "=",
            "==": "=",
            "neq": "!=",
            "!=": "!=",
            "lte": "&lt;=",
            "<=": "&lt;=",
            "gte": ">=",
            ">=": ">=",
            "gt": ">",
            ">": ">",
            "lt": "&lt;",
            "<": "&lt;",
        }.get(operator, "=")
        return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"cross_field_validation\" field=\"{_xslt_safe(field)}\">\n      <xsl:choose>\n        <xsl:when test=\"not(string(/Invoice/{field})) or not(string(/Invoice/{rule.get('reference_field')}))\">
          <status>FAIL</status>\n          <message>{title} requires both fields</message>\n        </xsl:when>\n        <xsl:when test=\"not(number(/Invoice/{field}) {comparison} number(/Invoice/{rule.get('reference_field')}))\">
          <status>FAIL</status>\n          <message>{title} failed cross-field check</message>\n        </xsl:when>\n        <xsl:otherwise>\n          <status>PASS</status>\n          <message>{title} passes cross-field check</message>\n        </xsl:otherwise>\n      </xsl:choose>\n    </rule_result>\n  </xsl:template>"""

    return f"""
  <xsl:template name=\"{rule_name}\">\n    <rule_result order=\"{index}\" rule_type=\"unsupported\" field=\"{_xslt_safe(field)}\">\n      <status>SKIP</status>\n      <message>Unsupported rule: {title}</message>\n    </rule_result>\n  </xsl:template>"""


def build_xslt_document(parsed_rules: list[dict[str, Any]]) -> str:
    templates = [
        _make_rule_template(rule, index + 1)
        for index, rule in enumerate(parsed_rules)
    ]
    call_templates = [f"      <xsl:call-template name=\"rule-{index + 1}\"/>" for index in range(len(parsed_rules))]
    templates_block = "\n".join(templates)
    calls_block = "\n".join(call_templates)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:re="http://exslt.org/regular-expressions"
  extension-element-prefixes="re">

  <xsl:output method="xml" indent="yes"/>
  <xsl:param name="current_date"/>
  <xsl:param name="tolerance" select="0.01"/>

  <xsl:template match="/">
    <validation_result>
      <rule_results>
{calls_block}
      </rule_results>
    </validation_result>
  </xsl:template>

{templates_block}

</xsl:stylesheet>'''


def parse_and_build_xslt(rule_text: str) -> dict[str, Any]:
    parsed = parse_rule_text(rule_text)
    xslt = build_xslt_document(parsed.rules)
    payload = parsed.as_dict()
    payload["xslt"] = xslt
    return {"structured": payload, "xslt": xslt}
