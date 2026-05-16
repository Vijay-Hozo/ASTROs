"use client";

import React, { useState } from "react";
import { BadgeCheck, Link, Clock, Zap } from "lucide-react";

const CATEGORIES = [
  { key: "required_field", label: "Required" },
  { key: "conditional_required", label: "Conditional" },
  { key: "date_validation", label: "Date" },
  { key: "numeric_comparison", label: "Numeric" },
  { key: "amount_calculation", label: "Calculation" },
  { key: "currency_consistency", label: "Currency" },
  { key: "tax_category_validation", label: "Tax" },
  { key: "duplicate_field_check", label: "Duplicate" },
];

export default function RuleFilters({ active, onChange }: { active?: string; onChange?: (k: string) => void }) {
  const [selected, setSelected] = useState<string | undefined>(active);

  function toggle(key: string) {
    const next = selected === key ? undefined : key;
    setSelected(next);
    onChange?.(next ?? "");
  }

  return (
    <div className="flex flex-wrap gap-2">
      {CATEGORIES.map((c) => (
        <button
          key={c.key}
          onClick={() => toggle(c.key)}
          className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm transition ${
            selected === c.key ? "bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] text-white shadow-lg" : "bg-white border border-slate-200 text-slate-700"
          }`}
        >
          <span className="text-xs">{c.label}</span>
          <span className="ml-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-white/10 text-xs">{/* count placeholder */}3</span>
        </button>
      ))}
    </div>
  );
}
