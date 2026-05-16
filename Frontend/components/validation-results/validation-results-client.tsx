"use client";

import React, { useState } from "react";
import { DesktopSidebar, MobileSidebar } from "@/components/rule-engine/sidebar";
import Header from "@/components/validation-results/header";
import SummaryCards from "./summary-cards";
import ValidationTable from "./validation-table";
import ResultDetailDrawer from "./result-detail-drawer";
import FailedRulesList from "./failed-rules-list";
import EmptyState from "./empty-state";
import { SAMPLE_RESULTS } from "./sample-data";

export default function ValidationResultsClient() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selected, setSelected] = useState<any | null>(null);

  const hasResults = SAMPLE_RESULTS.length > 0;

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8faff_0%,#f4f7ff_42%,#eef3fb_100%)] text-slate-900">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header onOpenSidebar={() => setMobileOpen(true)} />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1200px] space-y-6">
            <SummaryCards />

            {hasResults ? (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <ValidationTable onView={(r) => setSelected(r)} />
                </div>
                <div className="lg:col-span-1 space-y-4">
                  <FailedRulesList />
                </div>
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
