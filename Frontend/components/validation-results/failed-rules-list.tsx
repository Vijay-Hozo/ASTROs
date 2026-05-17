"use client";

import React from "react";
import type { ValidationReportRow } from "@/lib/types";

export default function FailedRulesList({ results }: { results: ValidationReportRow[] }) {
  const failed = (results || []).filter((r) => r.overall_status === "FAIL").slice(0, 5);

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold">Recent Failed Validations</div>
      <div className="mt-3 space-y-2">
        {failed.map((f) => (
          <div key={f.id} className="flex items-center justify-between rounded-md border p-3">
            <div>
              <div className="font-medium">Invoice #{f.invoice_identifier}</div>
              <div className="text-xs text-slate-500">{f.message || "Validation failed"}</div>
            </div>
            <div className="text-xs text-rose-600">FAIL</div>
          </div>
        ))}
        {failed.length === 0 && <div className="text-sm text-slate-600">No recent failures.</div>}
      </div>
    </div>
  );
}
