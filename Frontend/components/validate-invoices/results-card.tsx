"use client";

import React from "react";

export default function ResultsCard() {
  return (
    <div className="rounded-2xl border p-6 bg-white shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-700">Validation Results</h3>
        <div className="text-xs text-slate-500">Summary</div>
      </div>

      <div className="mt-4 space-y-3">
        <div className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-700">No errors found in sample invoice.</div>
        <div className="rounded-md bg-yellow-50 p-3 text-sm text-yellow-700">2 warnings: Missing optional field 'Notes'.</div>
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">1 error: Required field 'InvoiceNumber' missing.</div>
      </div>

      <div className="mt-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="pb-2">Field</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Details</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t">
              <td className="py-2">InvoiceNumber</td>
              <td className="py-2 text-red-600">Error</td>
              <td className="py-2 text-slate-600">Missing required field</td>
            </tr>
            <tr className="border-t">
              <td className="py-2">Notes</td>
              <td className="py-2 text-yellow-700">Warning</td>
              <td className="py-2 text-slate-600">Recommended for better processing</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
