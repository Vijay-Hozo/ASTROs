"use client";

import { motion } from "framer-motion";
import { Lightbulb, Sparkles } from "lucide-react";
import { useState } from "react";

export default function RuleInput() {
  const [rule, setRule] = useState(
    "If tax category is exempt, tax exemption reason is required.",
  );

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-4 md:p-5 shadow-sm"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-[#07122F]">1. Write Rule in Natural Language</h3>
        <button className="text-sm text-[#432EF1] hover:text-[#3223bd] transition">Examples</button>
      </div>
      <textarea
        value={rule}
        onChange={(e) => setRule(e.target.value)}
        className="w-full h-28 md:h-32 rounded-xl border border-slate-300 p-4 text-white placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-indigo-100 transition resize-none"
        placeholder="If tax category is exempt, tax exemption reason is required."
      />
      <div className="mt-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <p className="text-xs text-slate-500 inline-flex items-center gap-2">
          <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
          Tip: Use simple English. Example: Buyer name is required
        </p>
        <motion.button
          whileHover={{ y: -1 }}
          whileTap={{ scale: 0.98 }}
          className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] shadow-[0_8px_24px_rgba(67,46,241,0.35)]"
        >
          <Sparkles className="h-4 w-4" />
          Parse Rule
        </motion.button>
      </div>
    </motion.section>
  );
}
