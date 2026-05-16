"use client";

import React, { useState } from "react";

export default function UploadCard() {
  const [fileName, setFileName] = useState<string | null>(null);

  return (
    <div className="rounded-2xl border p-6 bg-white shadow-sm">
      <div className="flex flex-col items-start gap-4">
        <div className="text-sm font-medium text-slate-700">Upload Invoices</div>
        <label className="w-full cursor-pointer rounded-lg border-dashed border-2 border-slate-200 p-6 text-center hover:border-slate-300">
          <input
            type="file"
            accept=".xml,.json,.csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              setFileName(f ? f.name : null);
            }}
          />
          <div className="text-sm text-slate-500">Drag & drop or click to upload an invoice (XML/CSV/JSON)</div>
          {fileName && <div className="mt-3 text-xs text-slate-600">Selected: {fileName}</div>}
        </label>
        <div className="flex w-full justify-end">
          <button className="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700">Validate</button>
        </div>
      </div>
    </div>
  );
}
