"use client";

import { Copy, FileJson2, AlertCircle } from "lucide-react";
import type { ParseRuleResponse } from "@/lib/types";

interface ParsedRuleCardProps {
  result?: ParseRuleResponse | null;
  isLoading?: boolean;
}

export default function ParsedRuleCard({ result, isLoading }: ParsedRuleCardProps) {
  async function copyRule() {
    if (!result) return;
    const text = JSON.stringify(result.parsed_rule, null, 2);
    await navigator.clipboard.writeText(text);
  }

  if (!result && !isLoading) {
    return (
      <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-[#07122F] inline-flex items-center gap-2">
            <FileJson2 className="h-4 w-4 text-[#432EF1]" />
            2. Parsed Rule (Structured)
          </h3>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center">
          <p className="text-sm text-slate-500">Parse a rule to see structured output</p>
        </div>
      </section>
    );
  }

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-[#07122F] inline-flex items-center gap-2">
            <FileJson2 className="h-4 w-4 text-[#432EF1]" />
            2. Parsed Rule (Structured)
          </h3>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center">
          <p className="text-sm text-slate-500">Loading...</p>
        </div>
      </section>
    );
  }

  if (!result) return null;
  const parsedJson = JSON.stringify(result.parsed_rule, null, 2);

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
        <code className="text-slate-200 whitespace-pre">{parsedJson}</code>
      </pre>
    </section>
  );
}
