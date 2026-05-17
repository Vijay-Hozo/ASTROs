# Backend Integration Guide

**PS-3 Natural Language Rule Engine — Complete Backend Wiring**

## 📋 Architecture Overview

All backend components are now wired together. Here's the data flow:

```
User Request
    ↓
main.py (FastAPI routes)
    ↓
evaluator.py (Orchestrates scoring)
    ├─→ rule_parser.py (RuleParser class - parses natural language rules)
    ├─→ xml_reader.py (XMLReader class - extracts invoice fields)
    └─→ executor.py (RuleExecutor class - executes parsed rules)
    ↓
orm_models.py (SQLAlchemy ORM - persists to database)
    ↓
API Response
```

## 🔧 Component Details

### 1. **rule_parser.py** - Natural Language Rule Parsing
- **Class**: `RuleParser`
- **Main Method**: `parse(rule_text: str) -> dict`
- **Returns**: Structured rule dictionary with `rule_type`, `field`, `operation`, etc.
- **Supported Rule Types**:
  - `amount_calculation` - percentage or sum operations
  - `required_field` - mandatory field validation
  - `date_validation` - date checks (future dates, valid format)
  - `numeric_comparison` - greater than, less than, etc.
  - `currency_consistency` - validate currency codes
  - `tax_category_validation` - validate tax categories
  - `conditional_required_field` - conditional requirements
  - `duplicate_field_check` - uniqueness validation

### 2. **xml_reader.py** - Invoice XML Parsing
- **Class**: `XMLReader`
- **Main Method**: `extract(xml_content: str) -> dict`
- **Returns**: Dictionary with extracted invoice fields:
  - Identity: `invoice_id`, `invoice_number`
  - Parties: `seller_name`, `buyer_name`, `seller_vat`, `buyer_vat`
  - Dates: `issue_date`, `issue_date_raw`
  - Amounts: `taxable_amount`, `tax_amount`, `payable_amount`
  - Currency: `currency_code`
  - Tax: `tax_category`, `tax_exemption_reason`
  - Line Items: `line_items` (array of items with description, qty, unit_price, line_total)

### 3. **executor.py** - Rule Execution Engine
- **Class**: `RuleExecutor`
- **Main Method**: `execute(rule: dict, invoice: dict) -> tuple[str, str]`
- **Returns**: Tuple of `(status, message)` where status is one of:
  - `PASS` - Rule validation passed
  - `FAIL` - Rule validation failed
  - `ERROR` - Execution error
- **Batch Method**: `execute_all(rules: list, invoice: dict) -> dict`
- **Features**:
  - 2 cents (0.02) tolerance for amount calculations
  - Null-safe field access
  - Clear error messages for debugging

### 4. **evaluator.py** - Batch Scoring Engine
- **Class**: `Evaluator`
- **Purpose**: Orchestrates parsing, extracting, and executing
- **Methods**:
  - `evaluate_one(rule_text, xml_content)` - single rule, single invoice
  - `evaluate_rule_against_many(rule_text, xml_files)` - single rule, many invoices
  - `evaluate_many_rules(rules, xml_content)` - many rules, single invoice
- **Returns**: List of `EvaluationResult` objects with detailed scoring
- **Fallback**: Has inline minimal executor if executor.py unavailable

### 5. **orm_models.py** - Database Layer
- **Engine**: SQLAlchemy AsyncSession with aiosqlite
- **Models**:
  - `Rule` - Stores parsed rules with metadata
  - `Invoice` - Stores uploaded invoice XMLs
  - `ValidationResult` - Stores individual validation results
- **Functions**:
  - `init_db()` - Create all tables on startup
  - `get_db()` - FastAPI dependency for DB sessions
- **Database File**: `database.db` (single file, configurable via `DB_PATH` env var)

### 6. **main.py** - FastAPI Application
- **Routes Available**:
  - `GET /health` - System health check
  - `POST /validate` - Single rule + single XML
  - `POST /validate/batch` - Single rule + many XMLs
  - `POST /validate/all-rules` - All saved rules + single XML
  - `POST /rules` - Create and parse a new rule
  - `GET /rules` - List all saved rules
  - `DELETE /rules/{rule_id}` - Delete a saved rule
  - `POST /invoices` - Upload invoice XML
  - `GET /invoices` - List all invoices
  - `GET /results` - List all validation results
  - `GET /results/{invoice_id}` - Results for specific invoice
  - `GET /dashboard` - Summary statistics
  - `GET /trends` - Validation trends over time

### 7. **schemas.py** - Request/Response Models
- **Pydantic Models** for API validation:
  - `ValidateRequest` - Input: rule_text + xml_content
  - `ValidateBatchRequest` - Input: rule_text + xml_files[]
  - `SaveRuleRequest` - Input: rule_text + severity
  - `BatchEvaluateRequest` - Input: invoice_id + optional rule_ids[]
  - `ValidationResult` - Output: rule result with metadata
  - `BatchValidationResponse` - Output: results[] + summary
  - And many more for responses

### 8. **models.py** - Pydantic Request/Response Models
- **Note**: This is different from orm_models.py
- Contains `RuleCreate`, `RuleResponse`, `InvoiceResponse`, `ValidateRequest`, etc.
- Used by FastAPI for validation and documentation

## 🚀 Running the Backend

### Prerequisites
```bash
pip install fastapi uvicorn pydantic sqlalchemy aiosqlite python-multipart
```

### Start Server
```bash
cd Backend
uvicorn main:app --reload --port 8000
```

### Access Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🧪 Testing the Integration

### Test 1: Parse a Rule
```bash
curl -X POST http://localhost:8000/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_text": "Tax amount must be exactly 18% of taxable amount",
    "severity": "high"
  }'
```

### Test 2: Validate Single Rule
```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "rule_text": "Seller name is required",
    "xml_content": "<Invoice><seller_name>ABC Ltd</seller_name></Invoice>"
  }'
```

### Test 3: Upload Invoice
```bash
curl -X POST http://localhost:8000/invoices \
  -F "file=@sample_invoice.xml"
```

### Test 4: Check Health
```bash
curl http://localhost:8000/health
```

## 📊 Database Schema

### rules table
```sql
CREATE TABLE rules (
  id INTEGER PRIMARY KEY,
  rule_text TEXT NOT NULL,
  parsed_json TEXT NOT NULL,
  rule_type TEXT,
  severity TEXT DEFAULT 'error',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### invoices table
```sql
CREATE TABLE invoices (
  id INTEGER PRIMARY KEY,
  filename TEXT,
  xml_content TEXT NOT NULL,
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### validation_results table
```sql
CREATE TABLE validation_results (
  id INTEGER PRIMARY KEY,
  invoice_id INTEGER FOREIGN KEY,
  rule_id INTEGER FOREIGN KEY,
  rule_text TEXT,
  status TEXT NOT NULL,
  message TEXT,
  rule_type TEXT,
  validated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## ⚙️ Configuration

### Environment Variables
- `DB_PATH` - Path to SQLite database file (default: `database.db`)
- `FRONTEND_URL` - Frontend URL for CORS (default: `https://ps3-rule-engine.vercel.app`)

### CORS Configuration
Allowed origins in main.py:
- `http://localhost:3000` (local React dev)
- `http://localhost:3001` (alternative local)
- `${FRONTEND_URL}` env variable or Vercel URL

## 🔗 Integration Points

### Rule Parser → Executor
1. User provides natural language rule text
2. RuleParser.parse() converts to structured JSON
3. JSON is passed to RuleExecutor.execute() with invoice dict

### XML Reader → Executor
1. User provides invoice XML
2. XMLReader.extract() converts to Python dict
3. Dict is passed to RuleExecutor.execute() with parsed rule

### Evaluator Orchestration
1. Evaluator receives rule_text + xml_content
2. Calls RuleParser.parse() to structure the rule
3. Calls XMLReader.extract() to structure the invoice
4. Calls RuleExecutor.execute() to validate
5. Returns EvaluationResult with status, message, timing

### Database Persistence
1. Parsed rules saved to rules table via ORM
2. Invoices uploaded saved to invoices table
3. Validation results stored in validation_results table
4. All operations use AsyncSession for async/await

## 🛠️ Debugging

### Import Issues
- All modules import from Backend/ (the unified directory)
- Check that orm_models.py exists
- Verify database.py forwards to orm_models.py

### Class Not Found Errors
- RuleParser must be imported from rule_parser.py
- XMLReader must be imported from xml_reader.py
- RuleExecutor must be imported from executor.py
- Evaluator must be imported from evaluator.py

### Database Errors
- Ensure `database.db` file is writable
- Check `DB_PATH` environment variable if custom path used
- SQLAlchemy async requires aiosqlite

### Rule Parsing Issues
- Check rule_parser.py has RuleParser class
- Verify HANDLERS list contains all handler functions
- Test with simple rules first (e.g., "Seller name is required")

## 📝 File Structure
```
Backend/
├── main.py              # FastAPI app and routes
├── evaluator.py         # Batch scoring orchestrator
├── rule_parser.py       # Natural language → JSON
├── xml_reader.py        # XML → Python dict
├── executor.py          # Rule execution engine
├── orm_models.py        # SQLAlchemy ORM models
├── database.py          # DB forwards to orm_models
├── models.py            # Pydantic models (old - keep for compatibility)
├── schemas.py           # Pydantic request/response models
├── generate_dataset.py  # Dataset generation utility
├── requirements.txt     # Python dependencies
└── main.js              # Utility script (optional)
```

## ✅ Verification Checklist

- [ ] All 11 Python files present in Backend/
- [ ] orm_models.py exists with SQLAlchemy setup
- [ ] database.py forwards to orm_models.py
- [ ] main.py imports from orm_models (Rule, Invoice, ValidationResult)
- [ ] evaluator.py can instantiate RuleParser()
- [ ] evaluator.py can instantiate XMLReader()
- [ ] evaluator.py can instantiate RuleExecutor()
- [ ] RuleParser has .parse() method
- [ ] XMLReader has .extract() method
- [ ] RuleExecutor has .execute() and .execute_all() methods
- [ ] Database initialization runs without errors
- [ ] Health check endpoint responds
- [ ] Rules can be created and persisted
- [ ] Invoices can be validated

---

**Last Updated**: 2026-05-16
**Branch**: Steve/backend
**Status**: ✅ Fully Wired
