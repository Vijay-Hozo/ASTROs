"use client";

import { motion } from "framer-motion";
import { Lightbulb, Sparkles, AlertCircle, RotateCcw } from "lucide-react";
import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { APIError } from "@/lib/api-client";
import type { ParseRuleResponse } from "@/lib/types";

const examples = [
  "Buyer name is required",
  "Issue date cannot be in future",
  "Tax amount must be greater than 0",
];

interface RuleInputCardProps {
  onParsed?: (result: ParseRuleResponse) => void;
  onRuleChange?: (rule: string) => void;
  initialRule?: string;
}

export default function RuleInputCard({ onParsed, onRuleChange, initialRule = "" }: RuleInputCardProps) {
  const [rule, setRule] = useState(initialRule || "If tax category is exempt, tax exemption reason is required.");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);

  const handleRuleChange = (newRule: string) => {
    setRule(newRule);
    onRuleChange?.(newRule);
  };

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
      
      onParsed?.(result);
    } catch (err) {
      const apiError = err as APIError;
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)]"
    >
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">Write Rule in Natural Language</h2>
          <p className="mt-1 text-sm text-slate-500">Describe the invoice validation rule in plain English.</p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-2 transition focus-within:border-[#7b7dff] focus-within:ring-4 focus-within:ring-[#6f7bff1f]">
        <textarea
          value={rule}
          onChange={(event) => handleRuleChange(event.target.value)}
          placeholder="If tax category is exempt, tax exemption reason is required."
          disabled={isLoading}
          className="min-h-[140px] w-full resize-none rounded-[18px] border-0 bg-transparent p-4 text-[15px] text-slate-900 outline-none placeholder:text-slate-400 disabled:opacity-50"
        />
      </div>

      {error && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-900">{error.code === 'VALIDATION_ERROR' ? 'Validation Error' : 'Connection Error'}</p>
              <p className="text-sm text-red-700 mt-1 whitespace-pre-wrap">{error.message}</p>
              {error.code !== 'VALIDATION_ERROR' && (
                <button
                  onClick={handleParseRule}
                  disabled={isLoading}
                  className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-red-600 hover:text-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <RotateCcw className="h-4 w-4" />
                  Retry
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Lightbulb className="h-4 w-4 text-amber-500" />
            <span>Tip: Use simple English.</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {examples.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => handleRuleChange(example)}
                disabled={isLoading}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:-translate-y-0.5 hover:border-[#7b7dff] hover:text-[#4b52ff] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        <motion.button
          whileHover={{ scale: 1.01, y: -1 }}
          whileTap={{ scale: 0.99 }}
          onClick={handleParseRule}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(67,46,241,0.3)] transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Sparkles className="h-4 w-4" />
          {isLoading ? "Parsing..." : "Parse Rule"}
        </motion.button>
      </div>
    </motion.section>
  );
}
