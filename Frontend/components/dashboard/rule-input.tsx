"use client";

import { motion } from "framer-motion";
import { Lightbulb, Sparkles } from "lucide-react";
import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { ErrorAlert } from "../ui/error-alert";
import type { APIError } from "@/lib/api-client";
import type { ParseRuleResponse } from "@/lib/types";

interface RuleInputProps {
  onRuleParsed?: (rule: string, result: ParseRuleResponse) => void;
}

export default function RuleInput({ onRuleParsed }: RuleInputProps) {
  const [rule, setRule] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);

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
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-[#07122F]">1. Write Rule in Natural Language</h3>
      </div>

      {error && <ErrorAlert error={error} />}

      <textarea
        value={rule}
        onChange={(e) => setRule(e.target.value)}
        disabled={isLoading}
        className="h-28 w-full resize-none rounded-xl border border-slate-300 p-4 text-slate-900 bg-white transition focus:outline-none focus:ring-4 focus:ring-indigo-100 md:h-32 disabled:bg-slate-50 disabled:opacity-50"
        placeholder="Example: If tax category is exempt, tax exemption reason is required."
        maxLength={500}
      />

      <div className="mt-2 flex justify-end">
        <p className="text-xs text-slate-500">
          {rule.length}/500
        </p>
      </div>

      {error && <ErrorAlert error={error} />}

      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="inline-flex items-center gap-2 text-xs text-slate-500">
          <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
          Tip: Use simple English. Example: Buyer name is required
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
    </motion.section>
  );
}
