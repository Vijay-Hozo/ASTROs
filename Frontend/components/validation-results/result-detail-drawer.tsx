"use client";

import React from "react";
import { motion } from "framer-motion";
import type { ValidationResult } from "@/lib/types";

export default function ResultDetailDrawer({ result, onClose }: { result?: ValidationResult | null; onClose?: () => void }) {
  if (!result) return null;

  return (
    <motion.aside initial={{ x: 300 }} animate={{ x: 0 }} exit={{ x: 300 }} className="fixed right-0 top-0 z-50 h-full w-[520px] bg-white p-6 shadow-xl overflow-y-auto">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Validation Result #{result.id}</h3>
          <p className="text-sm text-slate-500">Invoice: {result.invoice_id} • Rule: {result.rule_id}</p>
        </div>
        <button onClick={onClose} className="text-slate-500">Close</button>
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <h4 className="text-sm font-medium">Status</h4>
          <div className={`mt-2 inline-block px-3 py-1 rounded-full text-sm font-medium ${
            result.status === 'PASS' 
              ? 'bg-emerald-100 text-emerald-700' 
              : result.status === 'FAIL'
              ? 'bg-rose-100 text-rose-700'
              : 'bg-amber-100 text-amber-700'
          }`}>
            {result.status}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium">Message</h4>
          <p className="mt-1 text-sm text-slate-700">{result.message}</p>
        </div>

        <div>
          <h4 className="text-sm font-medium">Metadata</h4>
          <div className="mt-2 text-sm text-slate-600 space-y-1">
            <div>ID: {result.id}</div>
            <div>Invoice ID: {result.invoice_id}</div>
            <div>Rule ID: {result.rule_id}</div>
            <div>Created: {new Date(result.created_at).toLocaleDateString()}</div>
          </div>
        </div>
      </div>
    </motion.aside>
  );
}
