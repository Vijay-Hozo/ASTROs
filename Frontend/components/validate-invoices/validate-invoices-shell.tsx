"use client";

import React from "react";
import UploadCard from "@/components/validate-invoices/upload-card";
import ResultsCard from "@/components/validate-invoices/results-card";

export default function ValidateInvoicesShell() {
  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <UploadCard />
          </div>

          <div className="lg:col-span-2">
            <ResultsCard />
          </div>
        </div>
      </div>
    </div>
  );
}
