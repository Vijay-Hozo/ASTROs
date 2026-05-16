"use client";

import React from "react";
import { BarChart3, CheckCircle, Zap, Layers, Sparkles } from "lucide-react";
import { SAMPLE_RULES } from "./sample-data";

function Card({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-md hover:shadow-lg transition">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-slate-600">{title}</div>
        <div className="text-slate-400">{icon}</div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <div className="text-2xl font-semibold text-slate-900">{value}</div>
        <div className="text-xs text-slate-500">+2.3%</div>
      </div>
    </div>
  );
}

export default function StatsCards() {
  const total = SAMPLE_RULES.length;
  const active = SAMPLE_RULES.filter((r) => r.status === "Active").length;
  const critical = SAMPLE_RULES.filter((r) => r.severity === "Critical").length;
  const categories = new Set(SAMPLE_RULES.map((r) => r.type)).size;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <Card title="Total Rules" value={String(total)} icon={<BarChart3 className="h-5 w-5 text-slate-500" />} />
      <Card title="Active Rules" value={String(active)} icon={<CheckCircle className="h-5 w-5 text-emerald-500" />} />
      <Card title="Critical Rules" value={String(critical)} icon={<Zap className="h-5 w-5 text-rose-500" />} />
      <Card title="Rule Categories" value={String(categories)} icon={<Layers className="h-5 w-5 text-slate-500" />} />
      <Card title="Recently Added" value="3" icon={<Sparkles className="h-5 w-5 text-indigo-500" />} />
    </div>
  );
}
