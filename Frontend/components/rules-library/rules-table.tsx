"use client";

import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { MoreHorizontal } from "lucide-react";
import { SAMPLE_RULES, Rule } from "./sample-data";

export default function RulesTable({ onSelect }: { onSelect?: (r: Rule) => void }) {
  const [query, setQuery] = useState("");
//   const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    if (!query) return SAMPLE_RULES;
    const q = query.toLowerCase();
    return SAMPLE_RULES.filter((r) => r.name.toLowerCase().includes(q) || r.id.toLowerCase().includes(q) || r.type.toLowerCase().includes(q));
  }, [query]);

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm overflow-hidden">
      <div className="mb-3 flex items-center justify-between gap-4">
        <div className="text-sm font-semibold">Rules</div>
        <div className="flex items-center gap-2">
          <input placeholder="Search table..." className="rounded-md border px-3 py-1 text-sm bg-buttonBlue text-buttonText placeholder:text-buttonText" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="pb-2">Rule ID</th>
              <th className="pb-2">Name</th>
              <th className="pb-2">Type</th>
              <th className="pb-2">Severity</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Last Updated</th>
              <th className="pb-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <motion.tr key={r.id} className="border-t" >
                <td className="py-3 w-[110px]">{r.id}</td>
                <td className="py-3">{r.name}</td>
                <td className="py-3">{r.type}</td>
                <td className="py-3">{r.severity}</td>
                <td className="py-3">{r.status}</td>
                <td className="py-3">{r.updatedAt}</td>
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <button onClick={() => onSelect?.(r)} className="rounded-md bg-slate-50 px-2 py-1 text-xs">View</button>
                    <button className="rounded-md px-2 py-1 text-xs text-slate-600 hover:bg-slate-100"><MoreHorizontal className="h-4 w-4" /></button>
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
