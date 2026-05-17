import type { ParsedRule } from "@/lib/types";

function sanitizeComment(value: string): string {
  return value.replace(/--/g, "-").replace(/\s+/g, " ").trim();
}

export function buildXsltPreviewDocument(parsedRules: ParsedRule[]): string {
  const ruleComments = parsedRules
    .map((rule, index) => `    <!-- Rule ${index + 1}: ${sanitizeComment(rule.description || rule.field || rule.rule_type)} -->`)
    .join("\n");

  const ruleCalls = parsedRules
    .map((_, index) => `      <xsl:call-template name="rule-${index + 1}"/>`)
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="xml" indent="yes"/>

  <xsl:template match="/">
    <validation_result>
      <rule_results>
${ruleCalls}
      </rule_results>
    </validation_result>
  </xsl:template>

${ruleComments}

</xsl:stylesheet>`;
}

export function buildEmptyXsltDocument(name: string): string {
  const safeName = sanitizeComment(name);
  return `<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:output method="xml" indent="yes"/>

  <xsl:template match="/">
    <validation_result>
      <message>${safeName} is ready for validation rules.</message>
    </validation_result>
  </xsl:template>

</xsl:stylesheet>`;
}
