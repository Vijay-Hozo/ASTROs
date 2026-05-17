"use client";

import React, { useState } from "react";
import { DesktopSidebar, MobileSidebar } from "@/components/dashboard/sidebar";
import Header from "@/components/validation-results/header";
import SummaryCards from "./summary-cards";
import ValidationTable from "./validation-table";
import ResultDetailDrawer from "./result-detail-drawer";
import FailedRulesList from "./failed-rules-list";
import EmptyState from "./empty-state";
import { useApiData } from "@/lib/hooks";
import { ErrorAlert } from "../ui/error-alert";
import type { ValidationReportRow } from "@/lib/types";
import ActiveXsltBanner from "@/components/workspace/active-xslt-banner";

export default function ValidationResultsClient() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selected, setSelected] = useState<ValidationReportRow | null>(null);

  const { data: results, isLoading, error, refetch } = useApiData<ValidationReportRow[]>("/results");
  const resultsList = results || [];

  const hasResults = resultsList.length > 0;

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8faff_0%,#f4f7ff_42%,#eef3fb_100%)] text-slate-900">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header onOpenSidebar={() => setMobileOpen(true)} />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1200px] space-y-6">
            <ActiveXsltBanner compact />
            <SummaryCards results={resultsList} isLoading={isLoading} />

            {error && <ErrorAlert error={error} onRetry={refetch} />}

            {hasResults ? (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <ValidationTable
                    onView={(r) => setSelected(r)}
                    isLoading={isLoading}
                    results={resultsList}
                    error={error}
                    refetch={refetch}
                  />
                </div>
                <div className="lg:col-span-1 space-y-4">
                  <FailedRulesList results={resultsList} />
                </div>
              </div>
            ) : isLoading ? (
              <div className="text-center py-12">
                <p className="text-slate-500">Loading validation results...</p>
              </div>
            ) : (
              <EmptyState />
            )}
          </div>
        </main>
      </div>

      <ResultDetailDrawer result={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
