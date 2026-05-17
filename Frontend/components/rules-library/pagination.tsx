"use client";

import React from "react";

export default function Pagination({ page, total, onChange }: { page: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / 10));
  return (
    <div className="mt-4 flex items-center justify-end gap-2">
      <button onClick={() => onChange(Math.max(1, page - 1))} className="rounded-md border px-3 py-1 text-sm">Prev</button>
      <div className="text-sm">Page {page} of {pages}</div>
      <button onClick={() => onChange(Math.min(pages, page + 1))} className="rounded-md border px-3 py-1 text-sm">Next</button>
    </div>
  );
}
