<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="xml" indent="yes"/>

  <!-- Injected by executor: today's date in YYYY-MM-DD format -->
  <xsl:param name="current_date"/>

  <xsl:template match="/">
    <validation_result>

      <xsl:choose>
        <xsl:when test="not(/Invoice/payable_amount > 0.0)">
          <status>FAIL</status>
          <message>payable_amount must be greater than 0.0. Found <xsl:value-of select="/Invoice/payable_amount"/></message>
          <field>payable_amount</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>payable_amount passes numeric check</message>
          <field>payable_amount</field>
        </xsl:otherwise>
      </xsl:choose>
    </validation_result>
  </xsl:template>

</xsl:stylesheet>