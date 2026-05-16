"use client";

import { motion } from "framer-motion";
import { ChevronDown, Play } from "lucide-react";

export default function RuleTestPanel() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)]"
    >
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight text-slate-900">Rule Test Panel</h2>
        <p className="mt-1 text-sm text-slate-500">Validate the rule against sample XML documents.</p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700">Test with Sample Data</label>
          <button className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm text-slate-600 transition hover:border-slate-300 hover:bg-slate-100">
            <span>sample_invoice_exempt_missing_reason.xml</span>
            <ChevronDown className="h-4 w-4" />
          </button>
        </div>

        <motion.button
          whileHover={{ scale: 1.01, y: -1 }}
          whileTap={{ scale: 0.99 }}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] px-4 py-3 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(67,46,241,0.3)]"
        >
          <Play className="h-4 w-4" />
          Run Validation
        </motion.button>

        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <span className="text-sm font-medium text-slate-700">Result</span>
            <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-600">FAIL</span>
          </div>
          <p className="text-sm leading-6 text-slate-600">
            Tax exemption reason is required when tax category is EXEMPT.
          </p>
        </div>

        <button className="text-sm font-medium text-[#4c2ff1] transition hover:text-[#3520d0]">
          View Details →
        </button>
      </div>
    </motion.section>
  );
}