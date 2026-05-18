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
  | "duplicate_field_check"
  | "regex_validation"
  | "enum_validation"
  | "cross_field_validation"
  | "unsupported";

export type RuleSeverity = "low" | "medium" | "high";

export interface ParsedRule {
  description?: string | null;
  rule_type: RuleType;
  field?: string | null;
  operation?: string | null;
  value?: unknown;
  min?: number | null;
  max?: number | null;
  constraint?: string | null;
  reference_field?: string | null;
  expression?: string | null;
  rate?: number | null;
  tolerance?: number | null;
  condition_field?: string | null;
  condition_value?: string | null;
  base_field?: string | null;
  pattern?: string | null;
  allowed_values?: string[] | null;
  order?: number | null;
  is_direct_tag?: boolean | null;
  xpath?: string | null;
  extra?: Record<string, unknown>;
  python_logic?: string;
  xslt?: string;
  _provider?: "groq" | "openrouter";
}

export interface ParseRuleResponse {
  rule_text: string;
  parsed_rule: ParsedRule;
  parsed_rules: ParsedRule[];
  rule_count: number;
  warnings: string[];
  xslt: string;
  xpath?: string;
  python_logic?: string;
}

export interface XsltStorageFile {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  rule_count: number;
  documentPath: string;
  metadataPath: string;
}

export interface XsltFileDraft {
  name: string;
  description?: string;
  content?: string;
  rule_count?: number;
  id?: string;
  rule_texts?: string[];
  parsed_rules?: ParsedRule[];
}

export interface XsltSelection {
  mode: "existing" | "create";
  file?: XsltStorageFile | null;
  draft?: XsltFileDraft | null;
}

export interface Rule {
  id: number;
  rule_text: string;
  parsed_json: ParsedRule | ParseRuleResponse;
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
export type OverallValidationStatus = "PASS" | "FAIL" | "PARTIAL";

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
  invoice_identifier?: string;
  rule_id: number | null;
  rule_text?: string;
  rule_type?: RuleType | null;
  status: ValidationStatus;
  message: string | null;
  validated_at: string;
}

export interface ValidationReportRow {
  id: number;
  invoice_id: number;
  invoice_identifier: string;
  overall_status: OverallValidationStatus;
  message: string;
  validated_at: string;
  total_rules: number;
  passed_rules: number;
  failed_rules: number;
  error_rules: number;
  execution_status: string;
  xslt_filename?: string;
}

export interface ValidationDetailItem {
  rule_id: number | null;
  rule_text: string;
  rule_type?: RuleType | null;
  status: ValidationStatus;
  message: string;
  execution_result: string;
  validated_at: string;
}

export interface ValidationReportDetail {
  report_id: number;
  invoice_id: number;
  invoice_identifier: string;
  uploaded_at: string;
  processed_at?: string | null;
  execution_status: string;
  xslt_filename?: string;
  overall_status: OverallValidationStatus;
  summary: ValidationSummary;
  checklist: ValidationDetailItem[];
  references: {
    xpath: string[];
    xslt: string[];
    python: string[];
  };
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
  passed_validations?: number;
  failed_validations?: number;
  total_passed?: number;
  total_failed?: number;
  pass_rate: number;
  recent_validations?: RecentValidation[];
}

export interface ActiveWorkspaceSession {
  sample_id: number | null;
  sample_filename: string | null;
  xslt_id: string | null;
  xslt_filename: string | null;
  extracted_tags: string[];
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
