"use client";

import React from "react";
import type { Rule } from "@/lib/types";

export default function RuleCard({ rule, onClick }: { rule: Rule; onClick?: () => void }) {
  return (
    <div onClick={onClick} className="rounded-2xl border bg-white p-4 shadow-sm hover:shadow-lg cursor-pointer">
      <div className="flex items-center justify-between">
        <div className="font-medium">Rule #{rule.id}</div>
        <div className="text-xs text-slate-500">{rule.severity}</div>
      </div>
      <div className="mt-2 text-sm text-slate-600">{rule.rule_text}</div>
    </div>
  );
}
