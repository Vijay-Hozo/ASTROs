"use client";

import { motion } from "framer-motion";
import { Lightbulb, Sparkles } from "lucide-react";
import { useState } from "react";

export default function RuleInput() {
  const [rule, setRule] = useState("If tax category is exempt, tax exemption reason is required.");

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm md:p-5"
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-[#07122F]">1. Write Rule in Natural Language</h3>
        <button className="text-sm text-[#432EF1] transition hover:text-[#3223bd]">Examples</button>
      </div>
      <textarea
        value={rule}
        onChange={(e) => setRule(e.target.value)}
        className="h-28 w-full resize-none rounded-xl border border-slate-300 p-4 text-white transition focus:outline-none focus:ring-4 focus:ring-indigo-100 md:h-32"
        placeholder="If tax category is exempt, tax exemption reason is required."
      />
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="inline-flex items-center gap-2 text-xs text-slate-500">
          <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
          Tip: Use simple English. Example: Buyer name is required
        </p>
        <motion.button
          whileHover={{ y: -1 }}
          whileTap={{ scale: 0.98 }}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] px-5 py-2.5 text-sm font-medium text-white shadow-[0_8px_24px_rgba(67,46,241,0.35)]"
        >
          <Sparkles className="h-4 w-4" />
          Parse Rule
        </motion.button>
      </div>
    </motion.section>
  );
}