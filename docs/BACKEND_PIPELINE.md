# Backend XML Invoice Pipeline Documentation

## Overview

This document describes the complete data transformation pipeline from XML invoice upload through validation result storage and API response.

---

## Pipeline Flow Diagram

```
Upload XML → Parse XML → Load Rules → LLM Parse → XSLT Gen → Execute → Store DB → API Response
```

---

## Step-by-Step Pipeline

### Step 1: XML Upload 🚀

**User uploads an invoice:**

```xml
<Invoice>
  <invoice_id>INV-0002</invoice_id>
  <issue_date>2026-04-04</issue_date>
  <seller_name>Seller_8</seller_name>
  <buyer_name>Buyer_8</buyer_name>
  <currency_code>GBP</currency_code>
  <taxable_amount>35790.97</taxable_amount>
  <tax_amount>6442.37</tax_amount>
  <payable_amount>42233.34</payable_amount>
  <tax_category>AE</tax_category>
  <line_items>
    <item>
      <description>Item 1</description>
      <quantity>6</quantity>
      <unit_price>154.12</unit_price>
      <line_total>924.72</line_total>
    </item>
  </line_items>
</Invoice>
```

**Endpoint:** `POST /validate/all-rules`

**Request Body:**
```json
{
  "xml_content": "<Invoice>...</Invoice>"
}
```

---

### Step 2: XML Parsing 🔍

**File:** `xml_reader.py` - `parse_invoice_xml()`

**Process:**
- Safely parses XML using `defusedxml` (prevents XXE attacks)
- Extracts all fields and converts to Python dictionary
- Handles missing fields gracefully (returns `None`)
- Converts data types: dates, floats, strings

**Output Dictionary:**
```python
{
  "invoice_id": "INV-0002",
  "issue_date": datetime(2026, 4, 4),
  "seller_name": "Seller_8",
  "buyer_name": "Buyer_8",
  "currency_code": "GBP",
  "taxable_amount": 35790.97,
  "tax_amount": 6442.37,
  "payable_amount": 42233.34,
  "tax_category": "AE",
  "line_items": [
    {
      "description": "Item 1",
      "quantity": 6.0,
      "unit_price": 154.12,
      "line_total": 924.72
    }
  ]
}
```

**Key Features:**
- Handles namespace-aware XML
- Multiple date format support
- Defusedxml safeguards against malicious XML
- Max XML size: 1MB

---

### Step 3: Load Saved Rules 📚

**Database Query:** Fetch all rules from `rules` table

**SQL:**
```sql
SELECT id, rule_text, parsed_json, rule_type, severity 
FROM rules 
ORDER BY id
```

**Example Rules (stored earlier):**
```
Rule 1: "Tax amount must be exactly 18% of taxable amount"
Rule 2: "Seller name is required"
Rule 3: "Invoice ID cannot be empty"
```

**Output Format:**
```python
[
  {
    "id": 1,
    "rule_text": "Tax amount must be exactly 18% of taxable amount",
    "parsed_json": '{"rule_type": "amount_calculation", "field": "tax_amount", ...}'
  },
  {
    "id": 2,
    "rule_text": "Seller name is required",
    "parsed_json": '{"rule_type": "required_field", "field": "seller_name", ...}'
  },
  ...
]
```

---

### Step 4: LLM Rule Parsing 🧠

**File:** `llm_rule_parser.py` - `parse_rule_and_build_xslt()`

**Process:**
- Sends rule text to LLM API (Groq or OpenRouter)
- LLM follows system prompt to extract structured parameters
- Validates response is valid JSON
- Applies timeout protection (30 seconds)

**Primary LLM:** Groq `llama-3.3-70b-versatile` (fast, free)
**Fallback LLM:** OpenRouter with Claude

**System Prompt Guides Extraction to:**
```
- rule_type: One of 8 predefined types
- field: XML field name (snake_case mapped)
- operation: Action to perform (gt, gte, percentage, sum, etc.)
- base_field: For calculations (what to calculate from)
- value: Numeric threshold or allowed values
- condition_field: For conditional rules
- message: Error message if rule fails
```

**Example Parsing:**

**Input Rule:**
```
"Tax amount must be exactly 18% of taxable amount"
```

**LLM Structured Output:**
```json
{
  "rule_type": "amount_calculation",
  "field": "tax_amount",
  "operation": "percentage",
  "base_field": "taxable_amount",
  "value": 18,
  "message": "Tax amount mismatch"
}
```

**Field Name Mappings (LLM Converts):**
- "tax amount" → `tax_amount`
- "taxable amount" → `taxable_amount`
- "payable amount" / "total amount" → `payable_amount`
- "invoice id" / "invoice number" → `invoice_id`
- "seller name" → `seller_name`
- "buyer name" → `buyer_name`
- "issue date" → `issue_date`
- "currency code" / "currency" → `currency_code`
- "tax category" → `tax_category`

**Rule Types Supported:**
1. `required_field` - Field must not be empty
2. `amount_calculation` - Math validation (percentage, sum)
3. `date_validation` - Date comparisons
4. `numeric_comparison` - Value threshold checks
5. `currency_consistency` - Currency code validation
6. `tax_category_validation` - Allowed tax categories
7. `conditional_required_field` - Field required only if condition met
8. `duplicate_field_check` - Uniqueness validation

---

### Step 5: XSLT Generation 🔧

**File:** `xslt_templates.py` - `build_xslt()`

**Process:**
- Takes structured rule from LLM
- Generates XSLT 1.0 stylesheet (XML transformation language)
- XSLT will be executed against the invoice XML
- Includes logic for all 8 rule types

**Generated XSLT for Rule 1** (Tax calculation):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:param name="current_date"/>
  
  <xsl:template match="/">
    <validation>
      <xsl:variable name="tax" select="number(//tax_amount)"/>
      <xsl:variable name="taxable" select="number(//taxable_amount)"/>
      <xsl:variable name="expected" select="$taxable * 0.18"/>
      
      <xsl:choose>
        <xsl:when test="abs($tax - $expected) &lt; 0.01">
          <status>PASS</status>
          <field>tax_amount</field>
          <message>Tax calculation correct</message>
        </xsl:when>
        <xsl:otherwise>
          <status>FAIL</status>
          <field>tax_amount</field>
          <message>Tax amount mismatch</message>
        </xsl:otherwise>
      </xsl:choose>
    </validation>
  </xsl:template>
</xsl:stylesheet>
```

**Generated XSLT for Rule 2** (Required field):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <validation>
      <xsl:choose>
        <xsl:when test="//seller_name and normalize-space(//seller_name) != ''">
          <status>PASS</status>
          <field>seller_name</field>
          <message>Field exists and is not empty</message>
        </xsl:when>
        <xsl:otherwise>
          <status>FAIL</status>
          <field>seller_name</field>
          <message>Seller name is required</message>
        </xsl:otherwise>
      </xsl:choose>
    </validation>
  </xsl:template>
</xsl:stylesheet>
```

---

### Step 6: XSLT Execution ⚙️

**File:** `xslt_executor.py` - `execute_xslt()`

**Process:**
- Loads XSLT stylesheet using `lxml.etree.XSLT`
- Loads invoice XML using safe defusedxml parser
- Injects current date for date validations
- Executes XSLT transformation
- Parses result and returns structured validation outcome

**Execution for INV-0002 with Rule 1:**

**Inputs:**
```
XSLT: <xsl:stylesheet>... (from Step 5)
XML: <Invoice>... (your invoice)
current_date: 2026-05-16
```

**XSLT Calculates:**
```
tax_amount = 6442.37
taxable_amount = 35790.97
expected = 35790.97 × 0.18 = 6,442.3746
difference = abs(6442.37 - 6,442.3746) = 0.0046
threshold = 0.01

0.0046 < 0.01 → ✅ PASS
```

**Output:**
```xml
<validation>
  <status>PASS</status>
  <field>tax_amount</field>
  <message>Tax calculation correct</message>
</validation>
```

**Error Handling:**
- Invalid XSLT syntax → `ERROR` status
- Malformed XML → `ERROR` status
- Execution timeout → `ERROR` status
- All errors returned in consistent format

---

### Step 7: Result Generation ✅/❌

**File:** `evaluator.py` - `evaluate_batch()`

**Process:**
- Collects all rule execution results
- Counts PASS/FAIL/ERROR statuses
- Normalizes result format for API
- Calculates summary statistics

**Individual Result Format:**
```json
{
  "rule_id": 1,
  "rule_text": "Tax amount must be exactly 18% of taxable amount",
  "rule_type": "amount_calculation",
  "status": "PASS",
  "message": "Tax calculation correct",
  "field": "tax_amount"
}
```

**Batch Results for All 3 Rules:**
```json
{
  "invoice_id": null,
  "summary": {
    "total": 3,
    "passed": 2,
    "failed": 1
  },
  "results": [
    {
      "rule_id": 1,
      "rule_text": "Tax amount must be exactly 18% of taxable amount",
      "rule_type": "amount_calculation",
      "status": "PASS",
      "message": "Tax calculation correct",
      "field": "tax_amount"
    },
    {
      "rule_id": 2,
      "rule_text": "Seller name is required",
      "rule_type": "required_field",
      "status": "PASS",
      "message": "Field exists and is not empty",
      "field": "seller_name"
    },
    {
      "rule_id": 3,
      "rule_text": "Invoice ID cannot be empty",
      "rule_type": "required_field",
      "status": "PASS",
      "message": "Field exists and is not empty",
      "field": "invoice_id"
    }
  ]
}
```

---

### Step 8: Database Storage 💾

**File:** `orm_models.py` - SQLAlchemy ORM Models

**Process:**
1. Store uploaded invoice in `invoices` table
2. Store each rule result in `validation_results` table
3. Create foreign key relationships

**Database Schema:**

#### Table: `invoices`
```
id           INT PRIMARY KEY
filename     VARCHAR(255) - "inline_upload"
xml_content  TEXT - Full XML string
uploaded_at  DATETIME - Timestamp
```

**Insert:**
```sql
INSERT INTO invoices (filename, xml_content, uploaded_at)
VALUES ('inline_upload', '<Invoice>...</Invoice>', NOW())
```

**Result:** `invoice_id = 1`

#### Table: `validation_results`
```
id            INT PRIMARY KEY
invoice_id    INT FOREIGN KEY → invoices.id
rule_id       INT FOREIGN KEY → rules.id
rule_text     VARCHAR(500) - Rule description
status        VARCHAR(20) - "PASS", "FAIL", "ERROR"
message       TEXT - Validation message
rule_type     VARCHAR(50) - Rule category
validated_at  DATETIME - Execution timestamp
```

**Inserts (for 3 rules):**
```sql
INSERT INTO validation_results (invoice_id, rule_id, rule_text, status, message, rule_type, validated_at)
VALUES 
  (1, 1, "Tax amount must be exactly 18% of taxable amount", "PASS", "Tax calculation correct", "amount_calculation", NOW()),
  (1, 2, "Seller name is required", "PASS", "Field exists and is not empty", "required_field", NOW()),
  (1, 3, "Invoice ID cannot be empty", "PASS", "Field exists and is not empty", "required_field", NOW());
```

**Cascade Delete:**
- Delete `invoices` row → automatically deletes related `validation_results`
- Delete `rules` row → automatically deletes related `validation_results`

---

### Step 9: API Response 📊

**File:** `main.py` - `/validate/all-rules` endpoint

**Response Format:**
```json
{
  "success": true,
  "data": {
    "invoice_id": 1,
    "summary": {
      "total": 3,
      "passed": 2,
      "failed": 1
    },
    "results": [
      {
        "rule_id": 1,
        "rule_text": "Tax amount must be exactly 18% of taxable amount",
        "rule_type": "amount_calculation",
        "status": "PASS",
        "message": "Tax calculation correct",
        "field": "tax_amount"
      },
      {
        "rule_id": 2,
        "rule_text": "Seller name is required",
        "rule_type": "required_field",
        "status": "PASS",
        "message": "Field exists and is not empty",
        "field": "seller_name"
      },
      {
        "rule_id": 3,
        "rule_text": "Invoice ID cannot be empty",
        "rule_type": "required_field",
        "status": "PASS",
        "message": "Field exists and is not empty",
        "field": "invoice_id"
      }
    ]
  }
}
```

**Returns to Frontend:**
- Used by dashboard to display validation results
- Shows passed/failed counts
- Lists each rule result with status and message
- Frontend stores and displays in tables/charts

---

## Key Technologies & Libraries

| Component | Purpose | Library |
|-----------|---------|---------|
| **XML Parser** | Safely extract invoice fields | `defusedxml` + `lxml` |
| **LLM Parser** | Extract rule logic in English | Groq / OpenRouter API |
| **XSLT Generator** | Create validation logic | Custom templates |
| **XSLT Executor** | Execute validation against XML | `lxml.etree.XSLT` |
| **Database** | Persist invoices & results | SQLite + SQLAlchemy async |
| **API Framework** | Serve endpoints | FastAPI + Uvicorn |
| **Async Support** | Non-blocking I/O | asyncio + `run_in_threadpool` |

---

## Data Transformation Summary

```
English Rule Text
    ↓
LLM Parsing (via Groq/OpenRouter)
    ↓
Structured JSON with rule parameters
    ↓
XSLT Template Generation
    ↓
XSLT Stylesheet (XML transformation logic)
    ↓
XSLT Execution against Invoice XML
    ↓
Validation Result (PASS/FAIL/ERROR)
    ↓
Database Storage (invoices + validation_results tables)
    ↓
API Response to Frontend (JSON)
    ↓
Frontend Dashboard Display
```

---

## Performance & Reliability

### Timeouts
- **Rule Parsing:** 30 seconds max
- **Batch Validation:** 60 seconds max
- **Individual XSLT Execution:** Included in batch timeout

### Async Operations
- All CPU-bound operations run off event loop via `run_in_threadpool`
- Database operations use async SQLAlchemy
- API handles multiple concurrent requests

### Security
- XML parsing: `defusedxml` prevents XXE attacks
- Input validation: Rule text length/content checks
- Error messages: Sanitized, no stack traces leaked
- CORS: Configured for frontend communication

### Error Handling
- Global exception middleware catches all errors
- Timeouts return 504 status
- Invalid input returns 400 status
- Server errors return 500 (no details leaked)

---

## Example: Complete Flow for INV-0002

### 1. User Upload
```
POST /validate/all-rules
Body: { "xml_content": "<Invoice>..." }
```

### 2. XML Parsed
```
Invoice dict with all fields extracted
```

### 3. Rules Loaded
```
3 rules from database
```

### 4. Each Rule Parsed by LLM
```
Rule 1 → {rule_type: "amount_calculation", field: "tax_amount", ...}
Rule 2 → {rule_type: "required_field", field: "seller_name", ...}
Rule 3 → {rule_type: "required_field", field: "invoice_id", ...}
```

### 5. XSLT Generated
```
3 XSLT stylesheets created
```

### 6. XSLT Executed
```
Rule 1: 6442.37 ≈ 35790.97 × 0.18 → PASS ✅
Rule 2: seller_name = "Seller_8" → PASS ✅
Rule 3: invoice_id = "INV-0002" → PASS ✅
```

### 7. Results Stored
```
INSERT INTO validation_results (invoice_id=1, rule_id=1, status="PASS", ...)
INSERT INTO validation_results (invoice_id=1, rule_id=2, status="PASS", ...)
INSERT INTO validation_results (invoice_id=1, rule_id=3, status="PASS", ...)
```

### 8. Response Sent
```json
{
  "success": true,
  "data": {
    "invoice_id": 1,
    "summary": {"total": 3, "passed": 3, "failed": 0},
    "results": [...]
  }
}
```

### 9. Frontend Displays
```
Invoice ID-0002
✅ Tax calculation correct
✅ Seller name required
✅ Invoice ID required

3/3 rules passed
```

---

## Debugging Tips

### If validation fails:
1. Check XML parsing: Does the XML have all required fields?
2. Check rule parsing: Did the LLM extract correct parameters?
3. Check XSLT: Is the generated XSLT syntactically valid?
4. Check execution: Does the data match the rule logic?

### Check database:
```sql
SELECT * FROM validation_results WHERE invoice_id = 1;
SELECT * FROM rules;
SELECT * FROM invoices WHERE id = 1;
```

### Check logs:
```
Look at backend console output for errors during each stage
```

---

## Additional Resources

- Backend: `backend/main.py`
- XML Reader: `backend/xml_reader.py`
- Evaluator: `backend/evaluator.py`
- LLM Parser: `backend/llm_rule_parser.py`
- XSLT Executor: `backend/xslt_executor.py`
- XSLT Templates: `backend/xslt_templates.py`
- ORM Models: `backend/orm_models.py`
- Schemas: `backend/schemas.py`
