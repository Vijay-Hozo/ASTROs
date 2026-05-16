"use client";

import { Copy, FileJson2, AlertCircle } from "lucide-react";
import type { SingleValidationResponse } from "@/lib/types";

interface ParsedRuleCardProps {
  result?: SingleValidationResponse | null;
}

export default function ParsedRuleCard({ result }: ParsedRuleCardProps) {
  async function copyResult() {
    if (result) {
      const json = JSON.stringify(result, null, 2);
      await navigator.clipboard.writeText(json);
    }
  }

  if (!result) {
    return (
      <section className="rounded-2xl border border-slate-200/80 bg-slate-50 p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="inline-flex items-center gap-2 font-semibold text-[#07122F]">
            <FileJson2 className="h-4 w-4 text-[#432EF1]" />
            2. Validation Result
          </h3>
        </div>
        <div className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 bg-slate-100 p-8 text-center">
          <AlertCircle className="h-5 w-5 text-slate-400" />
          <p className="text-sm text-slate-500">
            Parse a rule and test it against XML to see the validation result
          </p>
        </div>
      </section>
    );
  }

  const displayJson = JSON.stringify(result, null, 2);

  const statusColor = {
    PASS: "bg-emerald-50 border-emerald-200 text-emerald-700",
    FAIL: "bg-rose-50 border-rose-200 text-rose-700",
    ERROR: "bg-amber-50 border-amber-200 text-amber-700",
  }[result.status] || "bg-slate-50 border-slate-200";

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="inline-flex items-center gap-2 font-semibold text-[#07122F]">
            <FileJson2 className="h-4 w-4 text-[#432EF1]" />
            2. Validation Result
          </h3>
          <p className={`mt-1 inline-block px-2 py-1 rounded text-xs font-medium border ${statusColor}`}>
            Status: {result.status}
          </p>
        </div>
        <button
          onClick={copyResult}
          className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:text-slate-700"
          aria-label="Copy validation result"
        >
          <Copy className="h-4 w-4" />
        </button>
      </div>

      {result.message && (
        <div className="mb-3 rounded-lg bg-blue-50 border border-blue-200 p-3 text-sm text-blue-700">
          {result.message}
        </div>
      )}

      <pre className="overflow-auto rounded-xl border border-slate-200 bg-[#0f172a] p-4 text-xs leading-6 max-h-64">
        <code className="whitespace-pre text-slate-200">{displayJson}</code>
      </pre>

      {result.field && (
        <p className="mt-3 text-xs text-slate-500">
          <span className="font-medium">Field:</span> {result.field}
        </p>
      )}
    </section>
  );
}