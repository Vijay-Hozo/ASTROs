/**
 * Production TypeScript Interfaces
 * Shared types for API requests/responses and component state
 */

// ============================================================================
// Rules
// ============================================================================

export type RuleType =
  | "required_field"
  | "conditional_required"
  | "date_validation"
  | "numeric_comparison"
  | "amount_calculation"
  | "currency_consistency"
  | "tax_category_validation"
  | "duplicate_field_check";

export type RuleSeverity = "low" | "medium" | "high";

export interface ParsedRule {
  rule_type: RuleType;
  field: string;
  operation: string;
  value: unknown;
  condition_field?: string;
  condition_value?: string;
  xslt: string;
  _provider?: "groq" | "openrouter";
}

export interface Rule {
  id: number;
  rule_text: string;
  parsed_json: ParsedRule;
  severity: RuleSeverity;
  created_at: string;
}

export interface CreateRuleRequest {
  rule_text: string;
  severity: RuleSeverity;
}

export interface CreateRuleResponse {
  id: number;
  rule_text: string;
  parsed_json: ParsedRule;
  severity: RuleSeverity;
  created_at: string;
}

// ============================================================================
// Invoices
// ============================================================================

export interface Invoice {
  id: number;
  filename: string;
  size: number;
  uploaded_at: string;
  status: "pending" | "validated";
}

export interface UploadInvoiceResponse {
  id: number;
  filename: string;
  size: number;
  uploaded_at: string;
  status: "pending" | "validated";
}

// ============================================================================
// Validation Results
// ============================================================================

export type ValidationStatus = "PASS" | "FAIL" | "ERROR";

export interface ValidationResultItem {
  rule_id?: number;
  rule_text: string;
  rule_type?: RuleType;
  status: ValidationStatus;
  message: string;
  field?: string | null;
}

export interface ValidationSummary {
  total: number;
  passed: number;
  failed: number;
  errors: number;
}

export interface SingleValidationResponse {
  rule_id?: number;
  rule_text: string;
  rule_type?: RuleType;
  status: ValidationStatus;
  message: string;
  field?: string | null;
}

export interface BatchValidationResponse {
  invoice_id: string;
  summary: ValidationSummary;
  results: ValidationResultItem[];
}

export interface ValidationResult {
  id: number;
  invoice_id: number;
  rule_id: number;
  status: ValidationStatus;
  message: string;
  created_at: string;
}

export interface InvoiceValidationResponse {
  invoice_id: number;
  summary: ValidationSummary;
  results: ValidationResultItem[];
}

export interface ValidationResultsResponse {
  invoice_id: number;
  summary: ValidationSummary;
  results: ValidationResultItem[];
  invoice_data?: Record<string, unknown>;
}

// ============================================================================
// Dashboard
// ============================================================================

export interface RecentValidation {
  invoice_id: number;
  status: ValidationStatus;
  timestamp: string;
}

export interface DashboardStats {
  total_rules: number;
  total_invoices: number;
  total_validations: number;
  passed_validations: number;
  failed_validations: number;
  pass_rate: number;
  recent_validations: RecentValidation[];
}

// ============================================================================
// Validation Requests
// ============================================================================

export interface ValidateRequest {
  rule_text: string;
  xml_content: string;
}

export interface ValidateAllRulesRequest {
  xml_content: string;
}

export interface ValidateInvoiceRequest {
  rule_ids?: number[];
}

// ============================================================================
// Component State Types
// ============================================================================

export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

export interface DataState<T> extends LoadingState {
  data: T | null;
}

// ============================================================================
// API Response Envelopes
// ============================================================================

export interface APISuccessResponse<T> {
  data: T;
  error?: never;
}

export interface APIErrorResponse {
  detail?: string;
  message?: string;
  status?: number;
  [key: string]: unknown;
}

// ============================================================================
// Filter/Search Types
// ============================================================================

export interface RuleFilter {
  searchQuery?: string;
  severity?: RuleSeverity;
  status?: "Active" | "Draft" | "Disabled";
  ruleType?: RuleType;
}

export interface ValidationResultFilter {
  searchQuery?: string;
  status?: ValidationStatus;
  invoiceId?: number;
  dateFrom?: string;
  dateTo?: string;
}
