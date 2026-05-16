export type RuleType =
  | "required_field"
  | "conditional_required"
  | "date_validation"
  | "numeric_comparison"
  | "amount_calculation"
  | "currency_consistency"
  | "tax_category_validation"
  | "duplicate_field_check";

export type Severity = "High" | "Medium" | "Low" | "Critical";

export type Rule = {
  id: string;
  name: string;
  type: RuleType;
  severity: Severity;
  text: string;
  status: "Active" | "Draft" | "Disabled" | "Deprecated";
  updatedAt: string;
  createdBy: string;
};

export const SAMPLE_RULES: Rule[] = [
  {
    id: "RL-001",
    name: "Seller name is required",
    type: "required_field",
    severity: "High",
    text: "Ensure the seller name element is present and non-empty.",
    status: "Active",
    updatedAt: "2026-05-12",
    createdBy: "Compliance Bot",
  },
  {
    id: "RL-002",
    name: "Invoice date cannot be in the future",
    type: "date_validation",
    severity: "Medium",
    text: "The invoice issue date must not be greater than today's date.",
    status: "Active",
    updatedAt: "2026-05-10",
    createdBy: "Alice",
  },
  {
    id: "RL-003",
    name: "Invoice ID must be unique",
    type: "duplicate_field_check",
    severity: "Critical",
    text: "Invoice identifier must not duplicate existing invoices in dataset.",
    status: "Active",
    updatedAt: "2026-04-28",
    createdBy: "System",
  },
  {
    id: "RL-004",
    name: "Payable amount must equal taxable + tax",
    type: "amount_calculation",
    severity: "High",
    text: "Validate payable amount equals taxable amount plus tax amount.",
    status: "Draft",
    updatedAt: "2026-03-02",
    createdBy: "Bob",
  },
  {
    id: "RL-005",
    name: "If tax exempt then exemption reason required",
    type: "conditional_required",
    severity: "High",
    text: "When taxCategory == 'E', 'exemptionReason' must be present.",
    status: "Active",
    updatedAt: "2026-05-01",
    createdBy: "Carol",
  },
  {
    id: "RL-006",
    name: "Total amount must be > 0",
    type: "numeric_comparison",
    severity: "Medium",
    text: "The total invoice amount must be greater than zero.",
    status: "Active",
    updatedAt: "2026-02-18",
    createdBy: "Compliance Bot",
  },
  {
    id: "RL-007",
    name: "Tax category must be valid",
    type: "tax_category_validation",
    severity: "High",
    text: "Tax category must be one of S, Z, E, AE.",
    status: "Disabled",
    updatedAt: "2025-12-02",
    createdBy: "Dave",
  },
  {
    id: "RL-008",
    name: "Currency must be ISO code",
    type: "currency_consistency",
    severity: "Medium",
    text: "Currency values must conform to ISO 4217 codes.",
    status: "Active",
    updatedAt: "2026-01-09",
    createdBy: "Eve",
  },
];
