"use client";

import React from "react";

export default function EmptyState({ onValidate }: { onValidate?: () => void }) {
  return (
    <div className="rounded-xl border bg-white p-6 text-center shadow-sm">
      <div className="text-slate-700">No validation results yet.</div>
      <div className="mt-4">
        <button onClick={onValidate} className="rounded-xl bg-indigo-600 px-4 py-2 text-white">Validate Invoice</button>
      </div>
    </div>
  );
}
