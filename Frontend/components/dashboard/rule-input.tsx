"use client";

import { motion } from "framer-motion";
import { Lightbulb, Sparkles } from "lucide-react";
import { useState } from "react";
import { useMutate } from "@/lib/hooks";
import { ErrorAlert } from "../ui/error-alert";
import type { SingleValidationResponse, ValidateRequest } from "@/lib/types";

interface RuleInputProps {
  onValidationResult?: (result: SingleValidationResponse) => void;
  onXmlRequired?: () => void;
}

export default function RuleInput({ onValidationResult, onXmlRequired }: RuleInputProps) {
  const [rule, setRule] = useState("");
  const [xmlContent, setXmlContent] = useState("");

  const { mutate: validateRule, isLoading: isValidating, error } = useMutate<SingleValidationResponse>(
    "/validate",
    {
      onSuccess: (result) => {
        onValidationResult?.(result);
      },
    }
  );

  const handleValidate = async () => {
    if (!rule.trim()) {
      alert("Please enter a rule");
      return;
    }

    if (!xmlContent.trim()) {
      onXmlRequired?.();
      alert("Please provide XML content to test against. Use the XML Preview panel.");
      return;
    }

    try {
      await validateRule({
        rule_text: rule,
        xml_content: xmlContent,
      } as ValidateRequest);
    } catch (err) {
      console.error("Validation failed:", err);
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
        disabled={isValidating}
        className="h-28 w-full resize-none rounded-xl border border-slate-300 p-4 text-slate-900 bg-white transition focus:outline-none focus:ring-4 focus:ring-indigo-100 md:h-32 disabled:bg-slate-50 disabled:opacity-50"
        placeholder="Example: If tax category is exempt, tax exemption reason is required."
        maxLength={500}
      />

      <div className="mt-2 flex justify-end">
        <p className="text-xs text-slate-500">
          {rule.length}/500
        </p>
      </div>

      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="inline-flex items-center gap-2 text-xs text-slate-500">
          <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
          Tip: Use simple English. Example: Buyer name is required
        </p>
        <motion.button
          whileHover={{ y: isValidating ? 0 : -1 }}
          whileTap={{ scale: isValidating ? 1 : 0.98 }}
          onClick={handleValidate}
          disabled={isValidating || !rule.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] px-5 py-2.5 text-sm font-medium text-white shadow-[0_8px_24px_rgba(67,46,241,0.35)] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Sparkles className="h-4 w-4" />
          {isValidating ? "Validating..." : "Parse Rule"}
        </motion.button>
      </div>
    </motion.section>
  );
}