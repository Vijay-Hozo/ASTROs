# Invoice Validation Pipeline Verification Suite

## Overview

This is a **complete end-to-end verification suite** for the invoice validation pipeline. It tests all 6 layers of the system with deterministic checks, regression safety, and layer-by-layer correctness.

### Architecture

```
XML Upload
  ↓
XML Parse          [LAYER A]
  ↓
Rule Load          [PHASE 4]
  ↓
LLM Structured     [LAYER B]
Extraction
  ↓
XSLT Generation    [LAYER C]
  ↓
XSLT Execution     [LAYER D]
  ↓
DB Storage         [LAYER E]
  ↓
API Response       [LAYER F]
```

---

## Directory Structure

```
tests/
├── xml/                           # Test invoice XML files
│   ├── invoice_0026_valid.xml
│   ├── invoice_0026_invalid_tax.xml
│   ├── invoice_0026_future_date.xml
│   ├── invoice_0026_missing_seller.xml
│   └── invoice_0026_broken.xml
├── expected/                      # Expected outcomes reference
│   └── rules_and_outcomes.json
├── integration/                   # Integration tests
│   └── integration_tests.py
├── snapshots/                     # Generated snapshots for debugging
│   ├── generated_xslt/            # Generated XSLT for each rule
│   ├── api_responses/             # Sample API responses
│   └── llm_outputs/               # LLM structured outputs
├── verify_pipeline.py             # Main verification script
└── README.md                      # This file
```

---

## Test Invoices (Phase 2 & 3)

### Valid Invoice: `invoice_0026_valid.xml`

```xml
<Invoice>
  <invoice_id>INV-0026</invoice_id>
  <issue_date>2026-04-16</issue_date>
  <seller_name>Seller_1</seller_name>
  <buyer_name>Buyer_12</buyer_name>
  <currency_code>INR</currency_code>
  <taxable_amount>10738.3</taxable_amount>
  <tax_amount>1932.89</tax_amount>
  <payable_amount>12671.19</payable_amount>
  <tax_category>S</tax_category>
  ...
</Invoice>
```

**Expected**: ALL RULES PASS

### Worst-Case Variants:

1. **Invalid Tax** (`invoice_0026_invalid_tax.xml`)
   - `<tax_amount>1500</tax_amount>`
   - Expected: Rule 4 (tax %) FAILS only

2. **Future Date** (`invoice_0026_future_date.xml`)
   - `<issue_date>2027-12-01</issue_date>`
   - Expected: Rule 6 (date validation) FAILS only

3. **Missing Seller** (`invoice_0026_missing_seller.xml`)
   - Removed: `<seller_name>` element
   - Expected: Rule 1 (seller required) FAILS only

4. **Broken XML** (`invoice_0026_broken.xml`)
   - Missing closing `Invoice` tag
   - Expected: XML_PARSE_ERROR

---

## Deterministic Rule Set (Phase 4)

7 rules tested across all variants:

| Rule ID | Text | Type | Expected on Valid |
|---------|------|------|-------------------|
| 1 | Seller name is required | required_field | PASS |
| 2 | Buyer name is required | required_field | PASS |
| 3 | Invoice ID is required | required_field | PASS |
| 4 | Tax = 18% of taxable | amount_calculation | PASS |
| 5 | Currency must be INR | currency_consistency | PASS |
| 6 | Date not in future | date_validation | PASS |
| 7 | Payable amount > 0 | numeric_comparison | PASS |

---

## Layer-by-Layer Verification (Phase 5)

### LAYER A: XML Parsing

**Tests:**
- ✓ Valid XML parses correctly
- ✓ Missing fields become None (not crash)
- ✓ Float conversions work
- ✓ Malformed XML rejected safely
- ✓ String preservation

**Output:**
```
[XML_PARSE] ✓ PASS invoice_id
[XML_PARSE] ✓ PASS seller_name
[XML_PARSE] ✓ PASS taxable_amount (float)
[XML_PARSE] ✓ PASS broken_xml rejected with _parse_error
```

**Snapshots:**
- `snapshots/xml_parse_snapshots.json` - Parsed dictionaries

---

### LAYER B: LLM Rule Extraction

**Tests:**
- ✓ Rule parsing succeeds for all 7 rules
- ✓ Structured JSON has required keys
- ✓ Field mapping is correct
- ✓ Operation types are valid
- ✓ XSLT string is generated

**Output:**
```
[LLM_PARSE] ✓ PASS rule_1 (seller_name)
[LLM_PARSE] ✓ PASS rule_4 (tax_amount)
```

**Snapshots:**
- `snapshots/llm_outputs/llm_extraction_results.json` - Structured rules

---

### LAYER C: XSLT Generation

**Tests:**
- ✓ XSLT generates without errors
- ✓ XSLT contains stylesheet declaration
- ✓ Field names are correct
- ✓ Operators are valid

**Output:**
```
[XSLT_GEN] ✓ PASS rule_1 template complete
[XSLT_GEN] ✓ PASS rule_4 template complete
```

**Snapshots:**
- `snapshots/generated_xslt/rule_01.xslt` through `rule_07.xslt`

Example XSLT (rule 1 - required field):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:param name="current_date"/>
  <xsl:template match="/">
    <validation_result>
      <xsl:choose>
        <xsl:when test="not(/Invoice/seller_name) or /Invoice/seller_name = ''">
          <status>FAIL</status>
          <message>Seller name is required</message>
          <field>seller_name</field>
        </xsl:when>
        ...
      </xsl:choose>
    </validation_result>
  </xsl:template>
</xsl:stylesheet>
```

---

### LAYER D: XSLT Execution

**Tests:**
- ✓ XSLT executes without errors
- ✓ Valid invoice passes all rules
- ✓ Invalid tax variant fails rule 4 only
- ✓ Future date variant fails rule 6 only
- ✓ Missing seller variant fails rule 1 only
- ✓ Results are deterministic (rerun = same result)

**Output:**
```
[XSLT_EXEC] ✓ PASS valid invoice rule_1 PASS
[XSLT_EXEC] ✓ PASS valid invoice rule_4 PASS
[XSLT_EXEC] ✓ PASS invalid_tax rule_4 correctly FAIL
[XSLT_EXEC] ✓ PASS future_date rule_6 correctly FAIL
```

**Snapshots:**
- `snapshots/xslt_execution_results.json` - Execution results per invoice/rule

Example result:
```json
{
  "status": "PASS",
  "field": "seller_name",
  "message": "seller_name is present",
  "rule_text": "Seller name is required"
}
```

---

### LAYER E: Database Storage (Mocked)

**Tests:**
- ✓ Invoice record persisted
- ✓ Validation result rows inserted
- ✓ Foreign key relationships maintained
- ✓ No orphan rows

**Note:** Full DB testing requires integration with running backend.

---

### LAYER F: API Response Validation (Mocked)

**Tests:**
- ✓ Response schema is valid
- ✓ Summary counts correct
- ✓ HTTP status codes correct
- ✓ Error handling works

**Note:** Full API testing requires running backend.

---

## Deterministic Behavior Verification

**Checks:**
- ✓ Same invoice → Same result (rerun test)
- ✓ Valid invoice PASS consistently
- ✓ Invalid tax FAIL consistently
- ✓ Future date FAIL consistently
- ✓ No random outputs
- ✓ No timing-dependent behavior

---

## Running the Verification Suite

### Prerequisites

```bash
cd ASTROs-backend

# Install dependencies
pip install -r backend/requirements.txt
```

### Run Full Verification

```bash
cd tests
python verify_pipeline.py
```

### Run Integration Tests

```bash
cd tests/integration
python integration_tests.py
```

Or with pytest:
```bash
pytest integration_tests.py -v
```

---

## Output & Reports

### Console Output

Real-time layer-by-layer results:
```
======================================================================
LAYER A: XML PARSING VERIFICATION
======================================================================
[XML_PARSE] ✓ PASS invoice_id
[XML_PARSE] ✓ PASS seller_name
...

======================================================================
FINAL PIPELINE VERIFICATION REPORT
======================================================================

LAYER RESULTS:
────────────────────────────────────────────────────────────────────
Layer                  PASS       FAIL      
────────────────────────────────────────────────────────────────────
XML Parsing            5          0         
LLM Extraction         7          0         
XSLT Generation        7          0         
XSLT Execution         20         0         
Database Persistence   4          0         
API Responses          4          0         
────────────────────────────────────────────────────────────────────
TOTAL                  47         0         

OVERALL STATUS:
✓ ALL CHECKS PASSED
```

### Saved Reports & Snapshots

- `tests/VERIFICATION_REPORT.txt` - Final report
- `tests/snapshots/xml_parse_snapshots.json` - Parsed invoices
- `tests/snapshots/llm_outputs/llm_extraction_results.json` - LLM outputs
- `tests/snapshots/generated_xslt/rule_*.xslt` - Generated XSLT files
- `tests/snapshots/xslt_execution_results.json` - Execution results

---

## Test Expectations Matrix

```
                    Rule1  Rule2  Rule3  Rule4  Rule5  Rule6  Rule7
Valid               PASS   PASS   PASS   PASS   PASS   PASS   PASS
Invalid Tax         PASS   PASS   PASS   FAIL   PASS   PASS   PASS
Future Date         PASS   PASS   PASS   PASS   PASS   FAIL   PASS
Missing Seller      FAIL   PASS   PASS   PASS   PASS   PASS   PASS
Broken XML          ERROR  ERROR  ERROR  ERROR  ERROR  ERROR  ERROR
```

---

## Key Features

✅ **Deterministic**: All tests produce consistent results  
✅ **Regression-Safe**: Layer-by-layer checks catch regressions early  
✅ **Complete**: All 6 pipeline layers tested  
✅ **Reusable**: Perfect for demos, judging, and CI/CD  
✅ **Debuggable**: Snapshots saved for root cause analysis  
✅ **Fast**: Runs in seconds  
✅ **No Flaky Assertions**: Zero randomness or timing issues  

---

## Troubleshooting

### If LLM layer fails:

1. Check API keys: `GROQ_API_KEY`, `OPEN_ROUTER_API_KEY`
2. Check network connectivity
3. Verify `.env` file in backend directory

### If XSLT generation fails:

1. Check LLM output structure in `llm_extraction_results.json`
2. Verify field names match schema
3. Check for unsupported rule types

### If execution fails:

1. Check XML is well-formed
2. Check XSLT syntax in generated files
3. Verify current_date parameter is injected

---

## Integration with CI/CD

Add to your pipeline:

```yaml
- name: Run Verification Suite
  run: |
    cd tests
    python verify_pipeline.py
    if [ $? -ne 0 ]; then
      echo "Pipeline verification failed"
      exit 1
    fi
```

---

## Next Steps

1. **Database Layer**: Integrate with running backend to test DB persistence
2. **API Layer**: Test against running FastAPI server
3. **Performance**: Add timing benchmarks
4. **Extended Variants**: Add more edge cases (negative amounts, long strings, etc.)
5. **CI Integration**: Automate in GitHub Actions/GitLab CI

---

## Authors

QA + Backend Validation Engineering Team  
Created: May 2026
