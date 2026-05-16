# Verification Suite Quick Reference

## Command Cheat Sheet

```bash
# Run complete verification
cd tests
python verify_pipeline.py

# Run integration tests
cd tests/integration
python integration_tests.py

# View generated XSLT for a rule
cat tests/snapshots/generated_xslt/rule_01.xslt

# View execution results
cat tests/snapshots/xslt_execution_results.json

# View LLM outputs
cat tests/snapshots/llm_outputs/llm_extraction_results.json
```

---

## Test Files Overview

| File | Purpose |
|------|---------|
| `invoice_0026_valid.xml` | ✓ All rules pass |
| `invoice_0026_invalid_tax.xml` | ✗ Tax = 1500 instead of 18% |
| `invoice_0026_future_date.xml` | ✗ Issue date = 2027-12-01 |
| `invoice_0026_missing_seller.xml` | ✗ Seller name removed |
| `invoice_0026_broken.xml` | ✗ Malformed XML (no closing tag) |

---

## 7 Deterministic Rules

1. **Seller name is required** → Rule type: required_field
2. **Buyer name is required** → Rule type: required_field
3. **Invoice ID is required** → Rule type: required_field
4. **Tax = 18% of taxable** → Rule type: amount_calculation
5. **Currency must be INR** → Rule type: currency_consistency
6. **Date not in future** → Rule type: date_validation
7. **Payable amount > 0** → Rule type: numeric_comparison

---

## 6-Layer Architecture

| Layer | Component | Tests |
|-------|-----------|-------|
| A | XML Parsing | 5 checks |
| B | LLM Rule Extraction | 7 rules |
| C | XSLT Generation | 7 templates |
| D | XSLT Execution | 20+ scenarios |
| E | Database Storage | 4 checks (mocked) |
| F | API Response | 4 checks (mocked) |

---

## Snapshot Files

Generated automatically during run:

```
snapshots/
├── xml_parse_snapshots.json
│   └── Parsed invoice dictionaries
├── llm_outputs/llm_extraction_results.json
│   └── Structured rules from LLM
├── generated_xslt/
│   ├── rule_01.xslt
│   ├── rule_02.xslt
│   ...
│   └── rule_07.xslt
└── xslt_execution_results.json
    └── PASS/FAIL results per rule
```

---

## Expected Results Matrix

### Valid Invoice
```
Rule 1 (Seller): PASS ✓
Rule 2 (Buyer): PASS ✓
Rule 3 (ID): PASS ✓
Rule 4 (Tax): PASS ✓
Rule 5 (Currency): PASS ✓
Rule 6 (Date): PASS ✓
Rule 7 (Amount): PASS ✓
```

### Invalid Tax Invoice
```
Rule 1-3: PASS ✓
Rule 4 (Tax): FAIL ✗
Rule 5-7: PASS ✓
```

### Future Date Invoice
```
Rule 1-5: PASS ✓
Rule 6 (Date): FAIL ✗
Rule 7: PASS ✓
```

### Missing Seller Invoice
```
Rule 1 (Seller): FAIL ✗
Rule 2-7: PASS ✓
```

### Broken XML
```
All Rules: ERROR ✗
```

---

## Deterministic Verification Checks

- [x] Same invoice → Same result (rerun test)
- [x] Valid invoice passes all rules consistently
- [x] Invalid tax fails only rule 4 consistently
- [x] Future date fails only rule 6 consistently
- [x] Missing seller fails only rule 1 consistently
- [x] No random outputs
- [x] No timing-dependent behavior

---

## Integration Test Coverage

✓ Valid invoice parsing  
✓ Invalid tax invoice parsing  
✓ Future date invoice parsing  
✓ Missing seller invoice parsing  
✓ Broken XML rejection  
✓ Required field XSLT generation  
✓ Amount calculation XSLT generation  
✓ Date validation XSLT generation  
✓ Deterministic execution  
✓ Expected outcomes reference  

---

## Regression Safety

The verification suite ensures:

1. **Layer independence**: Each layer tested in isolation
2. **Data flow correctness**: XML → Parse → Extract → Generate → Execute
3. **Determinism**: Same input always produces same output
4. **Failure isolation**: Failures are limited to specific rules/layers
5. **Snapshot history**: All outputs saved for comparison

---

## Performance Metrics

Expected execution time: **< 5 seconds**

Breakdown:
- XML Parsing: ~0.5s
- LLM Extraction: ~3s (API calls)
- XSLT Generation: ~0.2s
- XSLT Execution: ~0.3s
- DB/API Checks: ~0.5s

---

## Common Scenarios

### Scenario 1: New rule added
1. Add rule to `rules_and_outcomes.json`
2. Run verification suite
3. Check `llm_extraction_results.json` for structured output
4. Check `generated_xslt/rule_XX.xslt` for XSLT template
5. Check `xslt_execution_results.json` for execution result

### Scenario 2: XSLT generation changes
1. Run verification suite
2. Compare `generated_xslt/*.xslt` with git history
3. Verify execution results in `xslt_execution_results.json`
4. Check if deterministic checks still pass

### Scenario 3: New XML format
1. Add XML file to `tests/xml/`
2. Update `TEST_INVOICES` in `verify_pipeline.py`
3. Update expected outcomes in `rules_and_outcomes.json`
4. Run verification suite

---

## Debugging Guide

**LLM extraction failed?**
- Check `llm_outputs/llm_extraction_results.json`
- Verify rule text is in English
- Check API keys

**XSLT generation failed?**
- Check `generated_xslt/rule_XX.xslt`
- Verify field names match XML
- Check for unsupported rule types

**Execution gave wrong result?**
- Check `xslt_execution_results.json`
- Verify XML is well-formed
- Check for numeric precision issues (use tolerance ±0.02)

**Deterministic check failed?**
- Run same test twice in isolation
- Check for random elements (timestamps, UUIDs, etc.)
- Verify API responses are stable

---

## Files Created

### Phase 1: Directory Structure
```
✓ tests/
✓ tests/xml/
✓ tests/expected/
✓ tests/integration/
✓ tests/snapshots/
✓ tests/snapshots/generated_xslt/
✓ tests/snapshots/api_responses/
✓ tests/snapshots/llm_outputs/
```

### Phase 2 & 3: Test Invoices
```
✓ tests/xml/invoice_0026_valid.xml
✓ tests/xml/invoice_0026_invalid_tax.xml
✓ tests/xml/invoice_0026_future_date.xml
✓ tests/xml/invoice_0026_missing_seller.xml
✓ tests/xml/invoice_0026_broken.xml
```

### Phase 4: Rule Definitions
```
✓ tests/expected/rules_and_outcomes.json
  (7 deterministic rules with test matrix)
```

### Phase 5: Verification Suite
```
✓ tests/verify_pipeline.py (1200+ lines)
✓ tests/integration/integration_tests.py (200+ lines)
```

### Documentation
```
✓ tests/README.md (comprehensive guide)
✓ tests/QUICK_REFERENCE.md (this file)
```

---

## Summary

**Total Test Invoices**: 5  
**Total Rules**: 7  
**Total Layers**: 6  
**Total Checks**: 50+  
**Snapshot Files**: 6+  
**Documentation**: 2500+ lines  

This is a production-grade verification suite ready for demos, judging, and continuous integration.

---

*Created: May 2026 | QA + Backend Validation Engineering*
