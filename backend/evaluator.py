"""
evaluator.py - Batch scoring engine for the PS-3 Rule Engine.

Responsibility:
  - Accept one or many XML invoice strings and a list of rule texts (or saved rule IDs)
  - Call executor.py for each (rule, invoice) pair
  - Aggregate results into PASS/FAIL summaries
  - Optionally persist results to the database via models

This module is stateless — it does not open DB connections itself.
The caller (main.py) passes DB sessions if persistence is needed.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

from rule_parser import RuleParser
from xml_reader import XMLReader

# executor is Steve's module — import defensively
try:
    # pyrefly: ignore [missing-import]
    from executor import RuleExecutor
    _EXECUTOR_AVAILABLE = True
except ImportError:
    _EXECUTOR_AVAILABLE = False


class EvaluationResult:
    """Data class holding the result of one (rule, invoice) evaluation."""

    __slots__ = (
        "rule_text", "parsed_rule", "result",
        "message", "invoice_id", "rule_id",
        "duration_ms"
    )

    def __init__(
        self,
        rule_text: str,
        parsed_rule: Optional[dict],
        result: str,             # "PASS" | "FAIL" | "ERROR"
        message: Optional[str],
        invoice_id: Optional[str] = None,
        rule_id: Optional[int] = None,
        duration_ms: float = 0.0,
    ) -> None:
        self.rule_text = rule_text
        self.parsed_rule = parsed_rule
        self.result = result
        self.message = message
        self.invoice_id = invoice_id
        self.rule_id = rule_id
        self.duration_ms = duration_ms

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_text": self.rule_text,
            "parsed_rule": self.parsed_rule,
            "result": self.result,
            "message": self.message,
            "invoice_id": self.invoice_id,
            "duration_ms": round(self.duration_ms, 2),
        }


class BatchSummary:
    """Aggregated counts for a batch evaluation run."""

    def __init__(self, results: List[EvaluationResult]) -> None:
        self.total = len(results)
        self.passed = sum(1 for r in results if r.result == "PASS")
        self.failed = sum(1 for r in results if r.result == "FAIL")
        self.errors = sum(1 for r in results if r.result == "ERROR")

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.passed / self.total * 100, 1)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "pass_rate": self.pass_rate,
        }


class Evaluator:
    """
    Main batch evaluation engine.

    Usage
    -----
    evaluator = Evaluator()

    # One rule, one XML
    result = evaluator.evaluate_one(rule_text, xml_content)

    # One rule, many XMLs
    results, summary = evaluator.evaluate_rule_against_many(rule_text, xml_list)

    # Many rules, one XML  (used by /validate/batch when rules come from the DB)
    results, summary = evaluator.evaluate_many_rules(rules, xml_content)
    """

    def __init__(self) -> None:
        self.parser = RuleParser()
        self.reader = XMLReader()
        if _EXECUTOR_AVAILABLE:
            self.executor = RuleExecutor()
        else:
            self.executor = None

    # ──────────────────────────────────────────
    # CORE: evaluate one (rule, xml) pair
    # ──────────────────────────────────────────

    def evaluate_one(
        self,
        rule_text: str,
        xml_content: str,
        rule_id: Optional[int] = None,
    ) -> EvaluationResult:
        """
        Parse `rule_text`, extract fields from `xml_content`,
        and execute the rule. Returns one EvaluationResult.
        """
        t0 = time.perf_counter()

        # 1. Parse the natural language rule → structured JSON
        try:
            parsed = self.parser.parse(rule_text)
        except Exception as exc:
            return EvaluationResult(
                rule_text=rule_text,
                parsed_rule=None,
                result="ERROR",
                message=f"Rule parsing failed: {exc}",
                rule_id=rule_id,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        if parsed.get("rule_type") == "unknown":
            return EvaluationResult(
                rule_text=rule_text,
                parsed_rule=parsed,
                result="ERROR",
                message="Rule could not be understood. Please rephrase.",
                rule_id=rule_id,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        # 2. Extract fields from the XML
        try:
            fields = self.reader.extract(xml_content)
        except Exception as exc:
            return EvaluationResult(
                rule_text=rule_text,
                parsed_rule=parsed,
                result="ERROR",
                message=f"XML parsing failed: {exc}",
                rule_id=rule_id,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        invoice_id = fields.get("invoice_id") or fields.get("id")

        # 3. Execute the parsed rule against extracted fields
        if self.executor:
            try:
                status, message = self.executor.execute(parsed, fields)
            except Exception as exc:
                status, message = "ERROR", f"Execution error: {exc}"
        else:
            # Fallback: inline minimal executor so the system still works
            # even if Steve's executor.py is not yet available
            status, message = self._fallback_execute(parsed, fields)

        elapsed = (time.perf_counter() - t0) * 1000
        return EvaluationResult(
            rule_text=rule_text,
            parsed_rule=parsed,
            result=status,
            message=message,
            invoice_id=str(invoice_id) if invoice_id else None,
            rule_id=rule_id,
            duration_ms=elapsed,
        )

    # ──────────────────────────────────────────
    # BATCH: one rule → many XMLs
    # ──────────────────────────────────────────

    def evaluate_rule_against_many(
        self,
        rule_text: str,
        xml_files: List[str],
        rule_id: Optional[int] = None,
    ) -> Tuple[List[EvaluationResult], BatchSummary]:
        """Validate a single rule text against a list of XML invoice strings."""
        results: List[EvaluationResult] = []
        for xml in xml_files:
            result = self.evaluate_one(rule_text, xml, rule_id=rule_id)
            results.append(result)
        summary = BatchSummary(results)
        return results, summary

    # ──────────────────────────────────────────
    # BATCH: many rules → one XML
    # ──────────────────────────────────────────

    def evaluate_many_rules(
        self,
        rules: List[dict],
        xml_content: str,
    ) -> Tuple[List[EvaluationResult], BatchSummary]:
        """
        Validate a list of rule dicts against one XML invoice.

        Each rule dict must have at minimum:
          - rule_text (str)
          - id (int, optional)
        """
        results: List[EvaluationResult] = []
        for rule in rules:
            rule_text = rule.get("rule_text", "")
            rule_id = rule.get("id")
            result = self.evaluate_one(rule_text, xml_content, rule_id=rule_id)
            results.append(result)
        summary = BatchSummary(results)
        return results, summary

    # ──────────────────────────────────────────
    # FALLBACK EXECUTOR (used only if executor.py not yet available)
    # Mirrors the interface Steve's executor.execute() is expected to expose.
    # ──────────────────────────────────────────

    def _fallback_execute(
        self, parsed: dict, fields: dict
    ) -> Tuple[str, str]:
        """
        Minimal inline execution of parsed rules so evaluator.py
        is self-contained during development. Steve's executor.py
        will replace this automatically once imported successfully.
        """
        rule_type = parsed.get("rule_type", "unknown")
        field = parsed.get("field")
        value = parsed.get("value")
        operation = parsed.get("operation")

        # ── required_field ──
        if rule_type == "required_field":
            if field and fields.get(field) not in (None, "", []):
                return "PASS", f"{field} is present: {fields[field]}"
            return "FAIL", f"Required field '{field}' is missing or empty"

        # ── numeric_comparison ──
        if rule_type == "numeric_comparison":
            raw = fields.get(field)
            if raw is None:
                return "FAIL", f"Field '{field}' not found in invoice"
            try:
                actual = float(str(raw).replace(",", ""))
            except ValueError:
                return "ERROR", f"Field '{field}' is not numeric: {raw}"
            try:
                threshold = float(value)
            except (TypeError, ValueError):
                return "ERROR", f"Rule value is not numeric: {value}"

            op_map = {
                "greater_than": (actual > threshold, f"{field} = {actual} > {threshold}"),
                "less_than": (actual < threshold, f"{field} = {actual} < {threshold}"),
                "equal": (actual == threshold, f"{field} = {actual} == {threshold}"),
                "not_equal": (actual != threshold, f"{field} = {actual} != {threshold}"),
                "greater_than_or_equal": (actual >= threshold, f"{field} = {actual} >= {threshold}"),
                "less_than_or_equal": (actual <= threshold, f"{field} = {actual} <= {threshold}"),
            }
            check, desc = op_map.get(operation, (None, ""))
            if check is None:
                return "ERROR", f"Unknown operation '{operation}'"
            status = "PASS" if check else "FAIL"
            msg = desc if check else f"{field} value {actual} failed '{operation}' {threshold}"
            return status, msg

        # ── amount_calculation ──
        if rule_type == "amount_calculation":
            lhs_field = parsed.get("field")
            rhs_fields = parsed.get("components", [parsed.get("base_field"), parsed.get("add_field")])
            rhs_fields = [f for f in rhs_fields if f]

            try:
                lhs = float(str(fields.get(lhs_field, 0)).replace(",", ""))
            except ValueError:
                return "ERROR", f"'{lhs_field}' is not numeric"
            try:
                rhs = sum(
                    float(str(fields.get(f, 0)).replace(",", ""))
                    for f in rhs_fields
                )
            except ValueError:
                return "ERROR", "One or more component fields are not numeric"

            if abs(lhs - rhs) < 0.01:
                return "PASS", f"{lhs_field} = {lhs} matches sum {rhs}"
            return "FAIL", (
                f"{lhs_field} mismatch. Expected {rhs:.2f}, found {lhs:.2f}"
            )

        # ── date_validation ──
        if rule_type == "date_validation":
            from datetime import date
            raw = fields.get(field)
            if not raw:
                return "FAIL", f"Date field '{field}' is missing"
            try:
                parts = str(raw).split("-")
                invoice_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                return "ERROR", f"Cannot parse date '{raw}' for field '{field}'"
            today = date.today()
            op = parsed.get("operation", "not_future")
            if op == "not_future":
                if invoice_date <= today:
                    return "PASS", f"{field} = {raw} is not in the future"
                return "FAIL", f"{field} = {raw} is in the future (today = {today})"
            if op == "not_past":
                if invoice_date >= today:
                    return "PASS", f"{field} = {raw} is not in the past"
                return "FAIL", f"{field} = {raw} is in the past (today = {today})"
            return "ERROR", f"Unknown date operation '{op}'"

        # ── currency_consistency ──
        if rule_type == "currency_consistency":
            invoice_currency = fields.get("invoice_currency") or fields.get("currency")
            line_currency = fields.get("line_item_currency") or fields.get("line_currency")
            if not invoice_currency:
                return "FAIL", "Invoice currency is missing"
            if not line_currency:
                return "FAIL", "Line item currency is missing"
            if str(invoice_currency).strip().upper() == str(line_currency).strip().upper():
                return "PASS", f"Currency consistent: {invoice_currency}"
            return "FAIL", f"Currency mismatch: invoice={invoice_currency}, line={line_currency}"

        # ── tax_category_validation ──
        if rule_type == "tax_category_validation":
            category = fields.get("tax_category") or fields.get("tax_category_code")
            tax_amt_raw = fields.get("tax_amount", 0)
            try:
                tax_amt = float(str(tax_amt_raw).replace(",", ""))
            except ValueError:
                return "ERROR", "tax_amount is not numeric"
            exempt_cats = {"exempt", "e", "o", "z"}
            if str(category).lower() in exempt_cats:
                if tax_amt == 0:
                    return "PASS", f"Tax category '{category}' is exempt and tax amount is 0"
                return "FAIL", f"Tax category '{category}' is exempt but tax amount is {tax_amt}"
            return "PASS", f"Tax category '{category}' is not exempt"

        # ── conditional_required_field ──
        if rule_type == "conditional_required_field":
            cond_field = parsed.get("condition_field")
            cond_value = parsed.get("condition_value")
            target_field = parsed.get("field")
            actual_cond = str(fields.get(cond_field, "")).strip().lower()
            expected_cond = str(cond_value).strip().lower()
            if actual_cond == expected_cond:
                if fields.get(target_field) not in (None, "", []):
                    return "PASS", f"'{target_field}' is present as required when {cond_field}={cond_value}"
                return "FAIL", f"'{target_field}' is required when {cond_field}={cond_value} but is missing"
            return "PASS", f"Condition not met ({cond_field} != {cond_value}), rule skipped"

        return "ERROR", f"Unsupported rule type: '{rule_type}'"
