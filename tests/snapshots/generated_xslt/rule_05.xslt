<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="xml" indent="yes"/>

  <!-- Injected by executor: today's date in YYYY-MM-DD format -->
  <xsl:param name="current_date"/>

  <xsl:template match="/">
    <validation_result>

      <xsl:choose>
        <xsl:when test="not(/Invoice/currency_code = 'INR')">
          <status>FAIL</status>
          <message>Currency '<xsl:value-of select="/Invoice/currency_code"/>' not in allowed list: ['INR']</message>
          <field>currency_code</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>Currency is valid</message>
          <field>currency_code</field>
        </xsl:otherwise>
      </xsl:choose>
    </validation_result>
  </xsl:template>

</xsl:stylesheet>