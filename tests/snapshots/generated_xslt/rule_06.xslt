<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="xml" indent="yes"/>

  <!-- Injected by executor: today's date in YYYY-MM-DD format -->
  <xsl:param name="current_date"/>

  <xsl:template match="/">
    <validation_result>

      <xsl:variable name="inv_y" select="number(substring(/Invoice/issue_date, 1, 4))"/>
      <xsl:variable name="inv_m" select="number(substring(/Invoice/issue_date, 6, 2))"/>
      <xsl:variable name="inv_d" select="number(substring(/Invoice/issue_date, 9, 2))"/>
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
          <message>Date validation failed. 'issue_date' is in the future</message>
          <field>issue_date</field>
        </xsl:when>
        <xsl:otherwise>
          <status>PASS</status>
          <message>issue_date is not in the future</message>
          <field>issue_date</field>
        </xsl:otherwise>
      </xsl:choose>
    </validation_result>
  </xsl:template>

</xsl:stylesheet>