<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="xml" indent="yes"/>

  <!-- Injected by executor: today's date in YYYY-MM-DD format -->
  <xsl:param name="current_date"/>

  <xsl:template match="/">
    <validation_result>

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
      </xsl:choose>
    </validation_result>
  </xsl:template>

</xsl:stylesheet>