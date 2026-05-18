"use client";

import React from "react";
import { motion } from "framer-motion";
import { AlertOctagon, XCircle, CheckCircle2 } from "lucide-react";
import type { ValidationReportRow } from "@/lib/types";

export default function FailedRulesList({ results }: { results: ValidationReportRow[] }) {
  const failed = (results || []).filter((r) => r.overall_status === "FAIL").slice(0, 6);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-rose-100 bg-gradient-to-b from-rose-50/30 to-white p-5 shadow-[0_12px_36px_rgba(244,63,94,0.06)]"
    >
      <div className="flex items-center gap-2.5 border-b border-rose-100/60 pb-3 mb-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-rose-100 text-rose-600 shadow-sm">
          <AlertOctagon className="h-4 w-4" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-slate-900 tracking-tight">Recent Failed Validations</h3>
          <p className="text-xs text-slate-500 mt-0.5">Invoices requiring immediate attention</p>
        </div>
      </div>

      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
        {failed.map((f, idx) => (
          <motion.div
            key={f.id}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            whileHover={{ scale: 1.01, x: 2 }}
            className="group relative flex items-center justify-between rounded-xl border border-rose-200/60 bg-white p-3.5 shadow-sm transition-all hover:border-rose-300 hover:shadow-md"
          >
            <div className="flex items-start gap-3 min-w-0 pr-2 w-full">
              <div className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-rose-100 text-rose-600">
                <XCircle className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-900 truncate">
                    Invoice #{f.invoice_identifier || f.invoice_id}
                  </span>
                  <span className="inline-block rounded-md bg-rose-100 px-1.5 py-0.5 text-[10px] font-bold text-rose-700 uppercase tracking-wider flex-shrink-0">
                    FAIL
                  </span>
                </div>
                <p className="mt-1.5 text-xs font-medium text-slate-600 line-clamp-2 leading-relaxed bg-rose-50/50 p-2.5 rounded-lg border border-rose-100/50">
                  {f.message || "seller_name is required"}
                </p>
              </div>
            </div>
          </motion.div>
        ))}

        {failed.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center bg-slate-50/50 rounded-xl border border-slate-100/80 p-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 mb-3 shadow-sm">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <p className="text-sm font-semibold text-slate-800">All Clear!</p>
            <p className="text-xs text-slate-500 mt-1 max-w-[200px]">No recent validation failures requiring attention.</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

