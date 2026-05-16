"use client";

import React from "react";
import { CheckCircle, XCircle, Clock } from "lucide-react";
import { SAMPLE_RESULTS } from "./sample-data";

function Card({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
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
  const total = SAMPLE_RESULTS.length;
  const passed = SAMPLE_RESULTS.filter((r) => r.status === "PASS").length;
  const failed = SAMPLE_RESULTS.filter((r) => r.status === "FAIL").length;
  const review = SAMPLE_RESULTS.filter((r) => r.status === "REVIEW").length;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
      <Card icon={<CheckCircle className="h-5 w-5 text-slate-600" />} label="Total Validations" value={String(total)} />
      <Card icon={<CheckCircle className="h-5 w-5 text-emerald-500" />} label="Passed" value={String(passed)} />
      <Card icon={<XCircle className="h-5 w-5 text-rose-500" />} label="Failed" value={String(failed)} />
      <Card icon={<Clock className="h-5 w-5 text-amber-500" />} label="Pending Review" value={String(review)} />
    </div>
  );
}
