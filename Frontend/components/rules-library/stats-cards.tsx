"use client";

import React from "react";
import { BarChart3, CheckCircle, Zap, Layers, Sparkles } from "lucide-react";
import { useApiData } from "@/lib/hooks";
import { StatsCardLoadingSkeleton } from "../ui/loading-skeleton";
import type { Rule } from "@/lib/types";

function getRuleType(rule: Rule): string {
  const parsed = rule.parsed_json as { rule_type?: string; parsed_rule?: { rule_type?: string } };
  return parsed.rule_type || parsed.parsed_rule?.rule_type || "unknown";
}

function Card({ title, value, icon }: { title: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-md hover:shadow-lg transition">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-slate-600">{title}</div>
        <div className="text-slate-400">{icon}</div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <div className="text-2xl font-semibold text-slate-900">{value}</div>
      </div>
    </div>
  );
}

export default function StatsCards() {
  const { data: rules, isLoading } = useApiData<Rule[]>("/rules");

  if (isLoading) return <StatsCardLoadingSkeleton />;

  const total = rules?.length || 0;
  const active = rules?.filter((r) => r.severity === "high").length || 0;
  const critical = rules?.filter((r) => r.severity === "high").length || 0;
  const categories = rules
    ? new Set(rules.map((r) => getRuleType(r))).size
    : 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <Card
        title="Total Rules"
        value={total}
        icon={<BarChart3 className="h-5 w-5 text-slate-500" />}
      />
      <Card
        title="Active Rules"
        value={active}
        icon={<CheckCircle className="h-5 w-5 text-emerald-500" />}
      />
      <Card
        title="Critical Rules"
        value={critical}
        icon={<Zap className="h-5 w-5 text-rose-500" />}
      />
      <Card
        title="Rule Categories"
        value={categories}
        icon={<Layers className="h-5 w-5 text-slate-500" />}
      />
      <Card
        title="Recently Added"
        value={rules?.length ? Math.min(rules.length, 3) : 0}
        icon={<Sparkles className="h-5 w-5 text-indigo-500" />}
      />
    </div>
  );
}
