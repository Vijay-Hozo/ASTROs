"use client";

import React from "react";
import { Search } from "lucide-react";

export default function SearchBar({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2">
      <div className="relative w-full">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search rules, rule IDs, or validation types..."
          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-2 pl-10 text-sm shadow-sm"
        />
        <Search className="absolute left-3 top-3 h-4 w-4 text-white" />
      </div>
    </div>
  );
}
