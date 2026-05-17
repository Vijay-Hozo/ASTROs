"use client";

import { motion } from "framer-motion";
import { Save, AlertCircle, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { APIError } from "@/lib/api-client";
import type { RuleSeverity, CreateRuleResponse } from "@/lib/types";
import type { ParseRuleResponse } from "@/lib/types";

interface AddRuleCardProps {
  result: ParseRuleResponse | null;
  ruleText: string;
  onSaved?: (ruleId: number) => void;
}

export default function AddRuleCard({ result, ruleText, onSaved }: AddRuleCardProps) {
  const [severity, setSeverity] = useState<RuleSeverity>("high");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);
  const [success, setSuccess] = useState(false);

  const handleAddRule = async () => {
    if (!result || !ruleText.trim()) {
      setError({
        code: "VALIDATION_ERROR",
        message: "Please parse a rule first before saving",
        status: 400,
      });
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await apiClient.post<CreateRuleResponse>("/rules", {
        rule_text: ruleText,
        severity: severity,
      });

      await apiClient.put(`/rules/${response.id}/logic`, {
        xpath_logic: result.xpath || null,
        xslt_logic: result.xslt || null,
        python_logic: result.python_logic || null,
      });

      setSuccess(true);
      onSaved?.(response.id);

      // Reset after success
      setTimeout(() => {
        setSuccess(false);
      }, 3000);
    } catch (err) {
      const apiError = err as APIError;
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  };

  if (!result) {
    return null;
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)]"
    >
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight text-slate-900">Implement Rule</h2>
        <p className="mt-1 text-sm text-slate-500">Store this validation rule in the rules library with a severity level.</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Severity Level</label>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as RuleSeverity)}
            disabled={isLoading}
            className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none transition-all duration-200 cursor-pointer font-semibold disabled:opacity-50 ${
              severity === "high"
                ? "border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100 hover:border-rose-300 focus:ring-2 focus:ring-rose-100"
                : severity === "medium"
                ? "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 hover:border-amber-300 focus:ring-2 focus:ring-amber-100"
                : "border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100 hover:border-sky-300 focus:ring-2 focus:ring-sky-100"
            }`}
          >
            <option value="low" className="bg-white text-slate-800 font-normal">Low</option>
            <option value="medium" className="bg-white text-slate-800 font-normal">Medium</option>
            <option value="high" className="bg-white text-slate-800 font-normal">High</option>
          </select>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-red-700">{error.message}</p>
          </div>
        )}

        {success && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-3 flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-green-700">Rule saved successfully!</p>
          </div>
        )}

        <motion.button
          whileHover={{ scale: 1.01, y: -1 }}
          whileTap={{ scale: 0.99 }}
          onClick={handleAddRule}
          disabled={isLoading || success}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#16a34a] to-[#15803d] px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(22,163,74,0.3)] transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Save className="h-4 w-4" />
          {isLoading ? "Implementing..." : "Implement Rule"}
        </motion.button>
      </div>
    </motion.section>
  );
}
