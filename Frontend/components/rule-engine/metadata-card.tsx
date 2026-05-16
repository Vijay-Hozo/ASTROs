"use client";

import { motion } from "framer-motion";
import { BadgeCheck, CalendarDays, FileDigit, Gauge, Link2, Sparkles, User } from "lucide-react";

const metadata = [
  { label: "Rule ID", value: "R-10023", icon: FileDigit },
  { label: "Created On", value: "20 May 2025 10:30 AM", icon: CalendarDays },
  { label: "Created By", value: "Admin User", icon: User },
  { label: "Severity", value: "High", icon: Gauge, badge: "text-rose-600 bg-rose-50 border-rose-200" },
  { label: "Rule Type", value: "Conditional Required Field", icon: Sparkles, badge: "text-[#4c2ff1] bg-[#f2efff] border-[#d8d1ff]" },
  { label: "Status", value: "Active", icon: BadgeCheck, badge: "text-emerald-600 bg-emerald-50 border-emerald-200" },
  { label: "Version", value: "1.0", icon: Link2 },
];

export default function MetadataCard() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)]"
    >
      <div className="mb-4 flex items-center gap-2">
        <div className="rounded-lg bg-[#f2efff] p-2 text-[#4c2ff1]">
          <Sparkles className="h-4 w-4" />
        </div>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">Rule Metadata</h2>
          <p className="text-sm text-slate-500">Structured summary of the parsed policy.</p>
        </div>
      </div>

      <dl className="space-y-3">
        {metadata.map(({ label, value, icon: Icon, badge }) => (
          <div key={label} className="flex items-center justify-between gap-4 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2.5">
            <dt className="flex items-center gap-2 text-sm text-slate-500">
              <Icon className="h-4 w-4 text-slate-400" />
              {label}
            </dt>
            <dd
              className={[
                "rounded-full border px-2.5 py-1 text-xs font-medium",
                badge ?? "border-slate-200 bg-white text-slate-700",
              ].join(" ")}
            >
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </motion.section>
  );
}