"use client";

import React from "react";
import { CheckCircle, XCircle, Clock, BarChart3 } from "lucide-react";
import { useApiData } from "@/lib/hooks";
import { StatsCardLoadingSkeleton } from "../ui/loading-skeleton";
import type { ValidationResult } from "@/lib/types";

function Card({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-white p-3 shadow-sm">
      <div className="rounded-lg bg-slate-50 p-2">{icon}</div>
      <div>
        <div className="text-sm text-slate-500">{label}</div>
        <div className="text-lg font-semibold text-slate-900">{value}</div>
      </div>
    </div>
  );
}

export default function SummaryCards() {
  const { data: results, isLoading } = useApiData<ValidationResult[]>("/results");
  const resultsList = results || [];

  if (isLoading) return <StatsCardLoadingSkeleton />;

  const total = resultsList.length;
  const passed = resultsList.filter((r) => r.status === "PASS").length;
  const failed = resultsList.filter((r) => r.status === "FAIL").length;
  const errors = resultsList.filter((r) => r.status === "ERROR").length;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
      <Card
        icon={<BarChart3 className="h-5 w-5 text-slate-600" />}
        label="Total Validations"
        value={total}
      />
      <Card
        icon={<CheckCircle className="h-5 w-5 text-emerald-500" />}
        label="Passed"
        value={passed}
      />
      <Card
        icon={<XCircle className="h-5 w-5 text-rose-500" />}
        label="Failed"
        value={failed}
      />
      <Card
        icon={<Clock className="h-5 w-5 text-amber-500" />}
        label="Errors"
        value={errors}
      />
    </div>
  );
}
