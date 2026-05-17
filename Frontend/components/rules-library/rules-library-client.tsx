"use client";

import React, { useState } from "react";
import { DesktopSidebar, MobileSidebar } from "../dashboard/sidebar";
import Header from "../dashboard/header";
import StatsCards from "./stats-cards";
import RulesTable from "./rules-table";
import RuleDetailDrawer from "./rule-detail-drawer";
import RuleCard from "./rule-card";
import { useApiData } from "../../lib/hooks";
import { ErrorAlert } from "../ui/error-alert";
import type { Rule } from "../../lib/types";
import ActiveXsltBanner from "@/components/workspace/active-xslt-banner";

export default function RulesLibraryClient() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selected, setSelected] = useState<Rule | null>(null);
  const [view, setView] = useState<"table" | "grid">("table");
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Fetch rules
  const { data: rules, error, refetch } = useApiData<Rule[]>("/rules");
  const rulesList = rules || [];

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8faff_0%,#f4f7ff_42%,#eef3fb_100%)] text-slate-900">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header
          onOpenSidebar={() => setMobileOpen(true)}
          title="Rules Library"
          subtitle="Manage reusable XML invoice validation rules and compliance templates."
        />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1400px] space-y-6">
            <ActiveXsltBanner compact />
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center gap-4" />
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setView(view === "table" ? "grid" : "table")}
                  className="rounded-xl border px-3 py-2 text-sm hover:bg-slate-50"
                >
                  {view === "table" ? "Grid View" : "Table View"}
                </button>
              </div>
            </div>

            <StatsCards />

            {error && <ErrorAlert error={error} onRetry={refetch} />}

            {view === "table" ? (
              <RulesTable
                onSelect={(r) => setSelected(r)}
                refreshTrigger={refreshTrigger}
                onDelete={() => setRefreshTrigger((t) => t + 1)}
              />
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {rulesList.map((r) => (
                  <RuleCard key={r.id} rule={r} onClick={() => setSelected(r)} />
                ))}
              </div>
            )}
          </div>
        </main>
      </div>

      <RuleDetailDrawer rule={selected} onClose={() => setSelected(null)} />

    </div>
  );
}
