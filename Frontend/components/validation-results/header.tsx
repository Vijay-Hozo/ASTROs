/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import React from "react";
import { Search, Filter, Download } from "lucide-react";

export default function Header({ onOpenSidebar }: { onOpenSidebar?: () => void }) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 px-4 py-4 md:px-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Validation Results</h1>
          <p className="text-sm text-slate-500">View invoice validation outcomes and rule violations.</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:block">
            <input placeholder="Search results..." className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm" />
          </div>
          <button className="rounded-xl border px-3 py-2 text-sm flex items-center gap-2"><Filter className="h-4 w-4" /> Filter</button>
          <button className="rounded-xl bg-indigo-600 px-3 py-2 text-sm text-white flex items-center gap-2"><Download className="h-4 w-4" /> Export</button>
        </div>
      </div>
    </header>
  );
}
