"use client";

import { motion } from "framer-motion";
import { Braces, FileType2 } from "lucide-react";

const fields = [
  { label: "tax_category", type: "Condition Field", icon: Braces },
  { label: "tax_exemption_reason", type: "Required Field", icon: FileType2 },
];

export default function FieldReferenceCard() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)]"
    >
      <div className="mb-4">
        <h2 className="text-lg font-semibold tracking-tight text-slate-900">Field References Detected</h2>
        <p className="mt-1 text-sm text-slate-500">The parser identified these XML fields.</p>
      </div>

      <div className="space-y-3">
        {fields.map(({ label, type, icon: Icon }) => (
          <div key={label} className="flex items-center justify-between gap-4 rounded-xl border border-slate-100 bg-slate-50/70 px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-white p-2 text-[#4c2ff1] shadow-sm">
                <Icon className="h-4 w-4" />
              </div>
              <span className="font-medium text-slate-800">{label}</span>
            </div>
            <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-500">
              {type}
            </span>
          </div>
        ))}
      </div>
    </motion.section>
  );
}