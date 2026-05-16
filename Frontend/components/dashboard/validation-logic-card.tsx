"use client";

import { Copy, FileCode2 } from "lucide-react";
import { useState } from "react";

const snippets = {
  XPath: `not(//tax_category='EXEMPT')
or
string-length(normalize-space(//tax_exemption_reason)) > 0`,
  XSLT: `<xsl:if test="//tax_category='EXEMPT' and not(normalize-space(//tax_exemption_reason))">
  <error>Tax exemption reason is required.</error>
</xsl:if>`,
  Python: `if tax_category == "EXEMPT" and not tax_exemption_reason.strip():
    raise ValidationError("Tax exemption reason is required")`,
} as const;

type TabKey = keyof typeof snippets;

export default function ValidationLogicCard() {
  const [tab, setTab] = useState<TabKey>("XPath");

  async function copySnippet() {
    await navigator.clipboard.writeText(snippets[tab]);
  }

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-[#07122F] inline-flex items-center gap-2">
          <FileCode2 className="h-4 w-4 text-[#432EF1]" />
          3. Generated Validation Logic
        </h3>
        <button
          onClick={copySnippet}
          className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:text-slate-700"
          aria-label="Copy generated logic"
        >
          <Copy className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-3 flex items-center gap-2">
        {(Object.keys(snippets) as TabKey[]).map((key) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={[
              "rounded-lg px-3 py-1.5 text-sm transition",
              tab === key
                ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                : "border border-slate-200 text-slate-600 hover:bg-slate-50",
            ].join(" ")}
          >
            {key}
          </button>
        ))}
      </div>

      <pre className="overflow-auto rounded-xl border border-slate-200 bg-[#0f172a] p-4 text-xs leading-6">
        <code className="text-slate-200 whitespace-pre">{snippets[tab]}</code>
      </pre>

      <p className="mt-3 rounded-xl border border-indigo-100 bg-indigo-50 px-3 py-2 text-xs text-indigo-700">
        This rule ensures that when tax category is EXEMPT, tax exemption reason must be provided.
      </p>
    </section>
  );
}
