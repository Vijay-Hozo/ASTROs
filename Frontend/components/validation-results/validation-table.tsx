"use client";

import React, { useMemo, useState } from "react";
import { SAMPLE_RESULTS, ValidationResult } from "./sample-data";
import { motion } from "framer-motion";

export default function ValidationTable({ onView }: { onView?: (r: ValidationResult) => void }) {
  const [query, setQuery] = useState("");
  const results = useMemo(() => SAMPLE_RESULTS, []);

  const filtered = results.filter((r) => !query || r.invoiceId.includes(query) || r.id.includes(query));

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-semibold">Validation Results</div>
        <div>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search" className="rounded-md border px-2 py-1 text-sm text-white bg-buttonBlue placeholder:text-white" />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="pb-2">Invoice ID</th>
              <th className="pb-2">Validation Date</th>
              <th className="pb-2">Rules Checked</th>
              <th className="pb-2">Passed</th>
              <th className="pb-2">Failed</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <motion.tr key={r.id} className="border-t hover:bg-slate-50" whileHover={{ scale: 1.001 }}>
                <td className="py-3">{r.invoiceId}</td>
                <td className="py-3">{r.date}</td>
                <td className="py-3">{r.rulesChecked}</td>
                <td className="py-3">{r.passed}</td>
                <td className="py-3">{r.failed}</td>
                <td className="py-3">
                  <span className={`rounded-full px-3 py-1 text-xs ${r.status === 'PASS' ? 'bg-emerald-100 text-emerald-700' : r.status === 'FAIL' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'}`}>{r.status}</span>
                </td>
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <button onClick={() => onView?.(r)} className="rounded-md bg-slate-50 px-2 py-1 text-xs">View Details</button>
                    <a className="rounded-md border px-2 py-1 text-xs" href="#">Download</a>
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
