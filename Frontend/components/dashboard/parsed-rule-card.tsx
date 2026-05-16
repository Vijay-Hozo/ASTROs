"use client";

import { Copy, FileJson2 } from "lucide-react";

const parsedRule = `{
  "rule_id": "R00123",
  "rule_type": "conditional_required_field",
  "severity": "high",
  "condition": {
    "field": "tax_category",
    "operator": "==",
    "value": "EXEMPT"
  },
  "required_field": "tax_exemption_reason",
  "error_message": "Tax exemption reason is required when tax category is EXEMPT."
}`;

export default function ParsedRuleCard() {
  async function copyRule() {
    await navigator.clipboard.writeText(parsedRule);
  }

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-[#07122F] inline-flex items-center gap-2">
          <FileJson2 className="h-4 w-4 text-[#432EF1]" />
          2. Parsed Rule (Structured)
        </h3>
        <button
          onClick={copyRule}
          className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:text-slate-700"
          aria-label="Copy parsed rule"
        >
          <Copy className="h-4 w-4" />
        </button>
      </div>
      <pre className="overflow-auto rounded-xl border border-slate-200 bg-[#0f172a] p-4 text-xs leading-6">
        <code className="text-slate-200 whitespace-pre">{parsedRule}</code>
      </pre>
    </section>
  );
}
