import type { ParsedRule, RuleType } from "@/lib/types";

export interface RuleClausePreview {
  index: number;
  text: string;
  status: "valid" | "warning" | "invalid";
  ruleType: RuleType;
  field?: string;
  details: string[];
}

const SPLIT_PATTERN = /\n+|,\s*(?=[A-Za-z(])/g;
const CONJUNCTION_SPLIT_PATTERN = /\s+(?:and|then)\s+(?=(?:[A-Za-z][\w\s-]*?)\s+(?:is|required|must be|should be|cannot be|can't be|must not be|should not be|is not|must|should)\b)/gi;

export function splitMultiRuleText(ruleText: string): string[] {
  if (!ruleText.trim()) return [];
  const clauses = ruleText
    .split(SPLIT_PATTERN)
    .map((part) => part.trim())
    .filter(Boolean);

  return clauses.flatMap((clause) =>
    clause
      .split(CONJUNCTION_SPLIT_PATTERN)
      .map((part) => part.trim())
      .filter(Boolean),
  );
}

function inferRuleType(clause: string): RuleType {
  const lowered = clause.toLowerCase();

  if (/(?:if|when)\s+.+?\s+is\s+.+?,\s*.+\s+(?:required|present)/i.test(clause)) {
    return "conditional_required";
  }

  if (/(?:required|present|not empty|non-empty|must exist)/i.test(lowered)) {
    return "required_field";
  }

  if (/(?:greater than|less than|at least|at most|between|equal to)/i.test(lowered)) {
    return "numeric_comparison";
  }

  if (/(?:future|past|before|after)/i.test(lowered)) {
    return "date_validation";
  }

  if (/(?:%\s+of|equal to\s+.+\s+(?:plus|\+)|calculated)/i.test(lowered)) {
    return "amount_calculation";
  }

  if (/match(?:es)?\s+(?:regex\s*)?/.test(lowered)) {
    return "regex_validation";
  }

  if (/(?:one of| in [A-Za-z0-9_,\s]+)/i.test(clause)) {
    return "enum_validation";
  }

  if (/(?:same as|equal to|must not exceed|must be greater than)\s+/.test(lowered)) {
    return "cross_field_validation";
  }

  return "unsupported";
}

function extractField(clause: string): string | undefined {
  const match = clause.match(/^([A-Za-z0-9_ ]+)/);
  return match?.[1]?.trim() || undefined;
}

export function previewMultiRuleText(ruleText: string): RuleClausePreview[] {
  return splitMultiRuleText(ruleText).map((clause, index) => {
    const ruleType = inferRuleType(clause);
    const field = extractField(clause);
    const status = ruleType === "unsupported" ? "warning" : "valid";

    return {
      index: index + 1,
      text: clause,
      status,
      ruleType,
      field,
      details:
        ruleType === "unsupported"
          ? ["Clause could not be matched to a supported rule pattern."]
          : [`Detected ${ruleType.replace(/_/g, " ")}`],
    };
  });
}

export function summarizeParsedRules(parsedRules: ParsedRule[]): string {
  if (parsedRules.length === 0) return "No parsed rules yet.";
  return parsedRules
    .map((rule, index) => `${index + 1}. ${rule.rule_type} ${rule.field ? `(${rule.field})` : ""}`.trim())
    .join("\n");
}
