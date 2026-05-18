# Database Schema Documentation

## Overview

The ASTROs backend uses SQLAlchemy ORM with native support exclusively for PostgreSQL (Supabase). The schema has been fully updated with complete field definitions for production use.

## Tables

### 1. Rules Table

Stores parsed natural-language rules with generated validation logic.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique rule identifier |
| rule_text | VARCHAR(500) | NOT NULL | Original natural language rule (max 500 chars) |
| parsed_json | TEXT | NOT NULL | Full parsed structure as JSON string |
| rule_type | VARCHAR(100) | INDEXED | Type of rule (required_field, amount_calculation, etc.) |
| field | VARCHAR(100) | | Field name targeted by rule (e.g., "seller_name", "tax_amount") |
| operation | VARCHAR(100) | | Operation type (e.g., "required", "equals", "greater_than") |
| severity | VARCHAR(20) | INDEXED | Rule severity: high, medium, low, critical |
| xslt_logic | TEXT | | Generated XSLT validation code |
| xpath_logic | TEXT | | Generated XPath expression |
| python_logic | TEXT | | Generated Python validation code |
| is_active | BOOLEAN | INDEXED | Soft delete flag (true = active) |
| created_at | DATETIME | INDEXED | Timestamp when rule was created |
| updated_at | DATETIME | | Timestamp of last update |

**Indexes:**
- `rule_type` - For filtering by rule type
- `severity` - For filtering by severity
- `is_active` - For active rules queries
- `created_at` - For chronological sorting

### 2. Invoices Table

Stores uploaded or provided XML invoice documents with extracted metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique invoice identifier |
| filename | VARCHAR(255) | | Original filename if uploaded |
| xml_content | TEXT | NOT NULL | Raw XML invoice document |
| invoice_id | VARCHAR(100) | INDEXED | Invoice ID extracted from XML |
| seller_name | VARCHAR(255) | | Seller/supplier name from XML |
| buyer_name | VARCHAR(255) | | Buyer/customer name from XML |
| issue_date | VARCHAR(20) | | Invoice issue date from XML |
| currency_code | VARCHAR(10) | | Currency code (e.g., USD, EUR) |
| payable_amount | FLOAT | | Total payable amount |
| tax_amount | FLOAT | | Tax amount |
| total_rules_tested | INTEGER | | Count of validation rules executed |
| passed_count | INTEGER | | Number of rules that passed |
| failed_count | INTEGER | | Number of rules that failed |
| uploaded_at | DATETIME | INDEXED | Timestamp of upload |
| processed_at | DATETIME | | Timestamp of processing completion |

**Indexes:**
- `invoice_id` - For finding invoices by invoice ID
- `uploaded_at` - For chronological sorting

### 3. ValidationResults Table

Stores results of running rules against invoices.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique validation result identifier |
| invoice_id | INTEGER | FK → invoices.id | Reference to invoice (CASCADE DELETE) |
| rule_id | INTEGER | FK → rules.id | Reference to rule (CASCADE DELETE) |
| rule_text | VARCHAR(500) | NOT NULL | Rule text (denormalized for auditing) |
| rule_type | VARCHAR(100) | | Type of rule validated |
| rule_severity | VARCHAR(20) | | Severity of the rule |
| status | VARCHAR(20) | INDEXED | Result status: PASS, FAIL, ERROR, PENDING |
| message | TEXT | | Detailed result message/explanation |
| field_checked | VARCHAR(100) | | Field that was validated |
| execution_time_ms | FLOAT | | Milliseconds to execute the rule |
| xslt_result | TEXT | | Raw XSLT output/trace |
| validated_at | DATETIME | INDEXED | Timestamp of validation |

**Indexes:**
- `invoice_id` - For finding results for a specific invoice
- `rule_id` - For finding results for a specific rule
- `status` - For filtering by validation status
- `validated_at` - For chronological sorting

### 4. AuditLogs Table

Complete audit trail of all system actions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Audit log entry ID |
| action | VARCHAR(100) | INDEXED | Action type (create_rule, delete_rule, validate_invoice, etc.) |
| entity_type | VARCHAR(50) | INDEXED | Entity type (rule, invoice, validation_result) |
| entity_id | INTEGER | INDEXED | ID of affected entity |
| details | TEXT | | JSON details about the action |
| user_id | VARCHAR(100) | | User who performed action (for future auth) |
| ip_address | VARCHAR(50) | | IP address of requester |
| status | VARCHAR(20) | INDEXED | Action status (success, error) |
| error_message | TEXT | | Error details if action failed |
| created_at | DATETIME | INDEXED | Timestamp of action |

**Indexes:**
- `action` - For finding specific action types
- `entity_type` - For finding actions on specific entity types
- `entity_id` - For finding all actions affecting a specific entity
- `status` - For finding successful/failed actions
- `created_at` - For chronological sorting

### 5. SystemStats Table

System-wide statistics and metrics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Stats record ID |
| total_rules | INTEGER | | Count of all active rules |
| total_invoices | INTEGER | | Count of all invoices |
| total_validations | INTEGER | | Total validation operations |
| passed_validations | INTEGER | | Validations that passed |
| failed_validations | INTEGER | | Validations that failed |
| avg_validation_time_ms | FLOAT | | Average validation execution time |
| last_updated | DATETIME | | Timestamp of last update |

## Relationships

### Cascade Behavior
- When a `Rule` is deleted, all associated `ValidationResults` are deleted
- When an `Invoice` is deleted, all associated `ValidationResults` are deleted
- This ensures referential integrity and prevents orphaned records

### Foreign Keys
- `ValidationResult.invoice_id` → `Invoice.id` (CASCADE)
- `ValidationResult.rule_id` → `Rule.id` (CASCADE)

## Connection Configuration

### Supabase PostgreSQL (Required)
```
SUPABASE_DB_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

The system strictly requires the `SUPABASE_DB_URL` environment variable. SQLite fallbacks have been completely removed from all backend layers to ensure production stability and consistent performance.

## Initialization

The database schema is created automatically on backend startup via SQLAlchemy's `create_all()` function. Tables are created if they don't already exist.

### Table Creation Order
SQLAlchemy handles dependency order automatically, but logical order is:
1. `rules` - No dependencies
2. `invoices` - No dependencies
3. `validation_results` - Depends on rules & invoices
4. `audit_logs` - No dependencies
5. `system_stats` - No dependencies

## Migration Notes

**When upgrading from old schema:**
- New columns are nullable/have defaults
- Existing data in old schema is preserved
- Run `ALTER TABLE` migrations if using direct SQL

**For production deployments:**
- Use formal migration tools like Alembic for version control
- Test schema changes in staging environment first
- Keep backup of production database before migrations

## Example Queries

### Get all active rules
```sql
SELECT * FROM rules WHERE is_active = true ORDER BY created_at DESC;
```

### Get validation results for an invoice
```sql
SELECT vr.*, r.rule_text, r.rule_type
FROM validation_results vr
JOIN rules r ON vr.rule_id = r.id
WHERE vr.invoice_id = ?
ORDER BY vr.validated_at DESC;
```

### Get rule pass rate
```sql
SELECT 
  rule_id,
  COUNT(*) as total,
  SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
  ROUND(100.0 * SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) / COUNT(*), 1) as pass_rate
FROM validation_results
GROUP BY rule_id;
```

### Get statistics by date
```sql
SELECT 
  DATE(validated_at) as date,
  COUNT(*) as total_validations,
  SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
  SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed
FROM validation_results
GROUP BY DATE(validated_at)
ORDER BY date DESC;
```
