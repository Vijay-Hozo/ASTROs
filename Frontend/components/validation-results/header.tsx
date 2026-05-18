/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import React, { useState } from "react";
import { Download, Loader2 } from "lucide-react";

export default function Header({ onOpenSidebar }: { onOpenSidebar?: () => void }) {
  const [isExporting, setIsExporting] = useState(false);

  const handleExportZip = async () => {
    setIsExporting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://astros.onrender.com";
      const response = await fetch(`${apiUrl}/api/results/export-zip`);
      if (!response.ok) {
        throw new Error("Failed to export results ZIP");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "validated-invoice-results.zip";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
      alert("Failed to export validation results ZIP.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 px-4 py-4 md:px-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Validation Results</h1>
          <p className="text-sm text-slate-500">View invoice validation outcomes and rule violations.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportZip}
            disabled={isExporting}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white flex items-center gap-2 hover:bg-indigo-700 disabled:opacity-50 transition shadow-sm"
          >
            {isExporting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Exporting ZIP…
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                Export Results ZIP
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
