"use client";

import React from "react";
import { SAMPLE_RESULTS } from "./sample-data";

export default function FailedRulesList() {
  const failed = SAMPLE_RESULTS.filter((r) => r.failed > 0).slice(0, 5);

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold">Recent Failed Validations</div>
      <div className="mt-3 space-y-2">
        {failed.map((f) => (
          <div key={f.id} className="flex items-center justify-between rounded-md border p-3">
            <div>
              <div className="font-medium">{f.invoiceId}</div>
              <div className="text-xs text-slate-500">{f.failed} failed • {f.date}</div>
            </div>
            <div className="text-xs text-rose-600">{f.failed} errors</div>
          </div>
        ))}
        {failed.length === 0 && <div className="text-sm text-slate-600">No recent failures.</div>}
      </div>
    </div>
  );
}
