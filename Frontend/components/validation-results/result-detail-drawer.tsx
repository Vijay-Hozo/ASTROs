"use client";

import React from "react";
import { motion } from "framer-motion";
import { ValidationResult } from "./sample-data";

export default function ResultDetailDrawer({ result, onClose }: { result?: ValidationResult | null; onClose?: () => void }) {
  if (!result) return null;

  return (
    <motion.aside initial={{ x: 300 }} animate={{ x: 0 }} exit={{ x: 300 }} className="fixed right-0 top-0 z-50 h-full w-[520px] bg-white p-6 shadow-xl">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold">{result.invoiceId}</h3>
          <p className="text-sm text-slate-500">{result.date} • {result.xmlFile}</p>
        </div>
        <button onClick={onClose} className="text-slate-500">Close</button>
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <h4 className="text-sm font-medium">Summary</h4>
          <div className="mt-2 text-sm text-slate-700">Rules Checked: {result.rulesChecked} • Passed: {result.passed} • Failed: {result.failed}</div>
        </div>

        <div>
          <h4 className="text-sm font-medium">Failed Rules</h4>
          <div className="mt-2 space-y-2">
            {result.failedRules && result.failedRules.length ? (
              result.failedRules.map((f, idx) => (
                <div key={idx} className="rounded-md border bg-slate-50 p-3">
                  <div className="font-medium">{f.rule}</div>
                  <div className="text-xs text-slate-600">Severity: {f.severity}</div>
                  {f.message && <div className="mt-1 text-sm text-slate-700">{f.message}</div>}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-600">No failed rules.</div>
            )}
          </div>
        </div>
      </div>
    </motion.aside>
  );
}
