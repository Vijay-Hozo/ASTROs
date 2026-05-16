<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="xml" indent="yes"/>

  <!-- Injected by executor: today's date in YYYY-MM-DD format -->
  <xsl:param name="current_date"/>

  <xsl:template match="/">
    <validation_result>

      <xsl:choose>
        <xsl:when test="not(/Invoice/invoice_id) or /Invoice/invoice_id = ''">
          <status>FAIL</status>
          <message>Invoice ID is missing</message>
          <field>invoice_id</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>invoice_id is present</message>
          <field>invoice_id</field>
        </xsl:otherwise>
      </xsl:choose>
    </validation_result>
  </xsl:template>

</xsl:stylesheet>