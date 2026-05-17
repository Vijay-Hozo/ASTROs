"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Copy, FileJson2, Lightbulb, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { ErrorAlert } from "../ui/error-alert";
import type { APIError } from "@/lib/api-client";
import type { ParseRuleResponse } from "@/lib/types";
import { buildXsltPreviewDocument } from "@/lib/xslt-generator";
import { previewMultiRuleText, splitMultiRuleText } from "@/lib/rule-parser";

interface RuleInputProps {
  onRuleParsed?: (rule: string, result: ParseRuleResponse) => void;
  initialValue?: string;
}

export default function RuleInput({ onRuleParsed, initialValue = "" }: RuleInputProps) {
  const [rule, setRule] = useState(initialValue || "seller_name is required\nbuyer_name is required");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);
  const [parsedResult, setParsedResult] = useState<ParseRuleResponse | null>(null);

  const previewClauses = useMemo(() => previewMultiRuleText(rule), [rule]);
  const clauseCount = useMemo(() => splitMultiRuleText(rule).length, [rule]);

  const handleParseRule = async () => {
    if (!rule.trim()) {
      setError({
        code: "VALIDATION_ERROR",
        message: "Please enter a rule before parsing",
        status: 400,
      });
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await apiClient.post<ParseRuleResponse>("/parse-rule", {
        rule_text: rule,
      });
      setParsedResult(result);
      onRuleParsed?.(rule, result);
    } catch (err) {
      const apiError = err as APIError;
      setError(apiError);
      console.error("Parse rule failed:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm md:p-5"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-[#07122F]">Multi-Rule Input</h3>
          <p className="mt-1 text-sm text-slate-500">Separate clauses with new lines or commas. Execution order is preserved.</p>
        </div>
        <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
          {clauseCount} clause{clauseCount === 1 ? "" : "s"}
        </div>
      </div>

      {error && <ErrorAlert error={error} />}

      <textarea
        value={rule}
        onChange={(e) => setRule(e.target.value)}
        disabled={isLoading}
        className="h-36 w-full resize-none rounded-xl border border-slate-300 bg-white p-4 text-slate-900 transition focus:outline-none focus:ring-4 focus:ring-indigo-100 md:h-40 disabled:bg-slate-50 disabled:opacity-50"
        placeholder="Example: seller_name is required, buyer_name is required, payable_amount should be greater than 100"
        maxLength={500}
      />

      <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
        <p>{rule.length}/500</p>
        <p>{clauseCount} parsed rule{clauseCount === 1 ? "" : "s"}</p>
      </div>

      {previewClauses.length > 0 && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Parsed preview</p>
            <span className="text-[11px] text-slate-500">Order preserved</span>
          </div>
          <div className="space-y-2">
            {previewClauses.map((clause) => (
              <div
                key={`${clause.index}-${clause.text}`}
                className={`rounded-lg border p-3 text-sm ${clause.status === "valid" ? "border-emerald-200 bg-white" : "border-amber-200 bg-amber-50/70"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">{clause.text}</p>
                    <p className="mt-1 text-xs text-slate-500">{clause.ruleType.replace(/_/g, " ")}{clause.field ? ` · ${clause.field}` : ""}</p>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${clause.status === "valid" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-800"}`}>
                    {clause.status}
                  </span>
                </div>
                {clause.details.length > 0 && <p className="mt-2 text-xs text-slate-600">{clause.details.join(" ")}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="inline-flex items-center gap-2 text-xs text-slate-500">
          <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
          Tip: Use one clause per line for best results.
        </p>
        <motion.button
          whileHover={{ y: isLoading ? 0 : -1 }}
          whileTap={{ scale: isLoading ? 1 : 0.98 }}
          onClick={handleParseRule}
          disabled={isLoading || !rule.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] px-5 py-2.5 text-sm font-medium text-white shadow-[0_8px_24px_rgba(67,46,241,0.35)] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Sparkles className="h-4 w-4" />
          {isLoading ? "Parsing..." : "Parse Rule"}
        </motion.button>
      </div>

      {parsedResult && (
        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="inline-flex items-center gap-2 text-sm font-semibold text-slate-900">
              <FileJson2 className="h-4 w-4 text-[#432EF1]" />
              Structured Result
            </div>
            <button
              type="button"
              onClick={() => navigator.clipboard.writeText(JSON.stringify(parsedResult.parsed_rules, null, 2))}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition hover:text-slate-900"
            >
              <Copy className="h-3.5 w-3.5" />
              Copy JSON
            </button>
          </div>

          <div className="space-y-3">
            {parsedResult.parsed_rules.map((ruleItem, index) => (
              <div key={`${index}-${ruleItem.field ?? ruleItem.rule_type}`} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium text-slate-900">{index + 1}. {ruleItem.field ?? "rule"}</p>
                  <span className="rounded-full bg-indigo-50 px-2 py-1 text-[11px] font-medium text-indigo-700">{ruleItem.rule_type}</span>
                </div>
                <pre className="mt-2 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(ruleItem, null, 2)}</pre>
              </div>
            ))}

            <div className="rounded-lg border border-slate-200 bg-slate-950 p-3 text-xs text-slate-100">
              <div className="mb-2 flex items-center gap-2 font-medium text-slate-200">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                Generated XSLT preview
              </div>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap">{buildXsltPreviewDocument(parsedResult.parsed_rules)}</pre>
            </div>
          </div>
        </div>
      )}
    </motion.section>
  );
}
