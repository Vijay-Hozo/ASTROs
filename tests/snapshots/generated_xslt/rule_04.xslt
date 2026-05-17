<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="xml" indent="yes"/>

  <!-- Injected by executor: today's date in YYYY-MM-DD format -->
  <xsl:param name="current_date"/>

  <xsl:template match="/">
    <validation_result>

      <xsl:variable name="actual"   select="number(/Invoice/tax_amount)"/>
      <xsl:variable name="base_val" select="number(/Invoice/taxable_amount)"/>
      <xsl:variable name="expected" select="$base_val * 0.18"/>
      <xsl:variable name="diff"
        select="$actual - $expected"/>
      <xsl:variable name="absdiff"
        select="($diff * ($diff >= 0)) + (($diff * -1) * ($diff &lt; 0))"/>
      <xsl:choose>
        <xsl:when test="$absdiff > 0.02">
          <status>FAIL</status>
          <message>Amount mismatch. Expected <xsl:value-of select="$expected"/>, found <xsl:value-of select="$actual"/></message>
          <field>tax_amount</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>tax_amount correctly calculated as 18.0% of taxable_amount</message>
          <field>tax_amount</field>
        </xsl:otherwise>
      </xsl:choose>
    </validation_result>
  </xsl:template>

</xsl:stylesheet>