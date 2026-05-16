"""
xslt_templates.py — One XSLT template per rule type.
LLM extracts variables → this file fills the template → runs against XML.
"""

def build_xslt(structured_rule: dict) -> str:
    """
    Takes a structured rule dict from LLM and returns a complete XSLT string.
    """
    rule_type = structured_rule.get("rule_type")

    builders = {
        "required_field":             _xslt_required_field,
        "amount_calculation":         _xslt_amount_calculation,
        "date_validation":            _xslt_date_validation,
        "numeric_comparison":         _xslt_numeric_comparison,
        "currency_consistency":       _xslt_currency_consistency,
        "tax_category_validation":    _xslt_tax_category,
        "conditional_required_field": _xslt_conditional_required,
        "duplicate_field_check":      _xslt_duplicate,
    }

    builder = builders.get(rule_type)
    if not builder:
        return _xslt_unknown(structured_rule)

    body = builder(structured_rule)
    return _wrap_xslt(body)


def _wrap_xslt(body: str) -> str:
    # current_date is injected at runtime by xslt_executor for date comparisons.
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="xml" indent="yes"/>

  <!-- Injected by executor: today's date in YYYY-MM-DD format -->
  <xsl:param name="current_date"/>

  <xsl:template match="/">
    <validation_result>
{body}
    </validation_result>
  </xsl:template>

</xsl:stylesheet>"""


# ─── Rule type builders ───────────────────────────────────────────────────────

def _xslt_required_field(rule: dict) -> str:
    field   = rule.get("field", "")
    message = rule.get("message", f"{field} is required")
    return f"""
      <xsl:choose>
        <xsl:when test="not(/Invoice/{field}) or /Invoice/{field} = ''">
          <status>FAIL</status>
          <message>{message}</message>
          <field>{field}</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>{field} is present</message>
          <field>{field}</field>
        </xsl:otherwise>
      </xsl:choose>"""


def _xslt_amount_calculation(rule: dict) -> str:
    field     = rule.get("field", "")
    operation = rule.get("operation", "")
    message   = rule.get("message", "Amount mismatch")

    if operation == "percentage":
        base  = rule.get("base_field", "")
        rate  = float(rule.get("value", 0))
        mult  = rate / 100
        return f"""
      <xsl:variable name="actual"   select="number(/Invoice/{field})"/>
      <xsl:variable name="base_val" select="number(/Invoice/{base})"/>
      <xsl:variable name="expected" select="$base_val * {mult}"/>
      <xsl:variable name="diff"
        select="$actual - $expected"/>
      <xsl:variable name="absdiff"
        select="($diff * ($diff >= 0)) + (($diff * -1) * ($diff &lt; 0))"/>
      <xsl:choose>
        <xsl:when test="$absdiff > 0.02">
          <status>FAIL</status>
          <message>{message}. Expected <xsl:value-of select="$expected"/>, found <xsl:value-of select="$actual"/></message>
          <field>{field}</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>{field} correctly calculated as {rate}% of {base}</message>
          <field>{field}</field>
        </xsl:otherwise>
      </xsl:choose>"""

    elif operation == "sum":
        base  = rule.get("base_field", "")
        add   = rule.get("add_field", "")
        return f"""
      <xsl:variable name="actual"   select="number(/Invoice/{field})"/>
      <xsl:variable name="expected" select="number(/Invoice/{base}) + number(/Invoice/{add})"/>
      <xsl:variable name="diff"     select="$actual - $expected"/>
      <xsl:variable name="absdiff"
        select="($diff * ($diff >= 0)) + (($diff * -1) * ($diff &lt; 0))"/>
      <xsl:choose>
        <xsl:when test="$absdiff > 0.02">
          <status>FAIL</status>
          <message>{message}. Expected <xsl:value-of select="$expected"/> ({base} + {add}), found <xsl:value-of select="$actual"/></message>
          <field>{field}</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>{field} correctly equals {base} + {add}</message>
          <field>{field}</field>
        </xsl:otherwise>
      </xsl:choose>"""

    return _xslt_unknown(rule)


def _xslt_date_validation(rule: dict) -> str:
    operation = rule.get("operation", "")
    field     = rule.get("field", "issue_date")
    message   = rule.get("message", "Date validation failed")

    if operation == "not_future":
        # XPath 1.0 `>` coerces strings to numbers → ISO dates become NaN → always false.
        # Fix: compare year, month, day as separate integers via substring().
        # $current_date is injected at runtime by xslt_executor (YYYY-MM-DD string param).
        return f"""
      <xsl:variable name="inv_y" select="number(substring(/Invoice/{field}, 1, 4))"/>
      <xsl:variable name="inv_m" select="number(substring(/Invoice/{field}, 6, 2))"/>
      <xsl:variable name="inv_d" select="number(substring(/Invoice/{field}, 9, 2))"/>
      <xsl:variable name="cur_y" select="number(substring($current_date, 1, 4))"/>
      <xsl:variable name="cur_m" select="number(substring($current_date, 6, 2))"/>
      <xsl:variable name="cur_d" select="number(substring($current_date, 9, 2))"/>
      <xsl:variable name="is_future"
        select="$inv_y &gt; $cur_y or
                ($inv_y = $cur_y and $inv_m &gt; $cur_m) or
                ($inv_y = $cur_y and $inv_m = $cur_m and $inv_d &gt; $cur_d)"/>
      <xsl:choose>
        <xsl:when test="$is_future">
          <status>FAIL</status>
          <message>{message}. '{field}' is in the future</message>
          <field>{field}</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>{field} is not in the future</message>
          <field>{field}</field>
        </xsl:otherwise>
      </xsl:choose>"""

    elif operation == "valid_date":
        return f"""
      <xsl:choose>
        <xsl:when test="not(/Invoice/{field}) or /Invoice/{field} = ''">
          <status>FAIL</status>
          <message>{field} is missing or not a valid date</message>
          <field>{field}</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>{field} is present</message>
          <field>{field}</field>
        </xsl:otherwise>
      </xsl:choose>"""

    return _xslt_unknown(rule)


def _xslt_numeric_comparison(rule: dict) -> str:
    field     = rule.get("field", "")
    operation = rule.get("operation", "")
    value     = float(rule.get("value", 0))
    message   = rule.get("message", "Numeric check failed")

    op_map = {
        "gt":       f"not(/Invoice/{field} > {value})",
        "gte":      f"not(/Invoice/{field} >= {value})",
        "lt":       f"not(/Invoice/{field} &lt; {value})",
        "lte":      f"not(/Invoice/{field} &lt;= {value})",
        "gte_zero": f"/Invoice/{field} &lt; 0",
        "lte_zero": f"/Invoice/{field} > 0",
    }

    op_desc = {
        "gt":       f"greater than {value}",
        "gte":      f">= {value}",
        "lt":       f"less than {value}",
        "lte":      f"<= {value}",
        "gte_zero": "not negative",
        "lte_zero": "zero or less",
    }

    fail_condition = op_map.get(operation, "false()")
    description    = op_desc.get(operation, "")

    return f"""
      <xsl:choose>
        <xsl:when test="{fail_condition}">
          <status>FAIL</status>
          <message>{field} must be {description}. Found <xsl:value-of select="/Invoice/{field}"/></message>
          <field>{field}</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>{field} passes numeric check</message>
          <field>{field}</field>
        </xsl:otherwise>
      </xsl:choose>"""


def _xslt_currency_consistency(rule: dict) -> str:
    field     = rule.get("field", "currency_code")
    operation = rule.get("operation", "")
    message   = rule.get("message", "Currency validation failed")

    if operation == "in":
        allowed   = rule.get("value", [])
        # Build XPath OR chain: currency_code = 'USD' or currency_code = 'EUR' ...
        conditions = " or ".join(
            [f"/Invoice/currency_code = '{c}'" for c in allowed]
        )
        return f"""
      <xsl:choose>
        <xsl:when test="not({conditions})">
          <status>FAIL</status>
          <message>Currency '<xsl:value-of select="/Invoice/currency_code"/>' not in allowed list: {allowed}</message>
          <field>currency_code</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>Currency is valid</message>
          <field>currency_code</field>
        </xsl:otherwise>
      </xsl:choose>"""

    elif operation == "matches_invoice_currency":
        return f"""
      <xsl:variable name="inv_currency" select="/Invoice/currency_code"/>
      <xsl:choose>
        <xsl:when test="/Invoice/line_items/item[currency != $inv_currency]">
          <status>FAIL</status>
          <message>Line item currency does not match invoice currency</message>
          <field>line_item_currency</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>All line item currencies match invoice currency</message>
          <field>line_item_currency</field>
        </xsl:otherwise>
      </xsl:choose>"""

    return _xslt_unknown(rule)


def _xslt_tax_category(rule: dict) -> str:
    allowed    = rule.get("value", ["S", "Z", "E", "AE"])
    conditions = " or ".join(
        [f"/Invoice/tax_category = '{c}'" for c in allowed]
    )
    return f"""
      <xsl:choose>
        <xsl:when test="not({conditions})">
          <status>FAIL</status>
          <message>Tax category '<xsl:value-of select="/Invoice/tax_category"/>' is invalid. Allowed: {allowed}</message>
          <field>tax_category</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>Tax category is valid</message>
          <field>tax_category</field>
        </xsl:otherwise>
      </xsl:choose>"""


def _xslt_conditional_required(rule: dict) -> str:
    cond_field  = rule.get("condition_field", "")
    cond_value  = rule.get("condition_value", "")
    req_field   = rule.get("required_field", "")
    message     = rule.get("message",
        f"'{req_field}' is required when '{cond_field}' is '{cond_value}'")

    return f"""
      <xsl:choose>
        <xsl:when test="/Invoice/{cond_field} = '{cond_value}'
                        and (not(/Invoice/{req_field})
                             or /Invoice/{req_field} = '')">
          <status>FAIL</status>
          <message>{message}</message>
          <field>{req_field}</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>Conditional check passed</message>
          <field>{req_field}</field>
        </xsl:otherwise>
      </xsl:choose>"""


def _xslt_duplicate(rule: dict) -> str:
    field = rule.get("field", "invoice_id")
    # Note: true duplicate detection needs all invoice IDs passed in.
    # XSLT handles single invoice — API layer handles cross-invoice uniqueness.
    return f"""
      <xsl:choose>
        <xsl:when test="not(/Invoice/{field}) or /Invoice/{field} = ''">
          <status>FAIL</status>
          <message>{field} is missing — cannot check uniqueness</message>
          <field>{field}</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>{field} is present (cross-invoice uniqueness checked at API level)</message>
          <field>{field}</field>
        </xsl:otherwise>
      </xsl:choose>"""


def _xslt_unknown(rule: dict) -> str:
    return """
      <status>SKIP</status>
      <message>Rule type not recognised — skipped</message>
      <field></field>"""
