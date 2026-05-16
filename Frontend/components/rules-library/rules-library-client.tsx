/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useMemo, useState } from "react";
import { DesktopSidebar, MobileSidebar } from "@/components/rule-engine/sidebar";
import Header from "@/components/rule-engine/header";
import StatsCards from "./stats-cards";
// import RuleFilters from "./rule-filters";
// import SearchBar from "./search-bar";
import RulesTable from "./rules-table";
import RuleDetailDrawer from "./rule-detail-drawer";
import RuleCard from "./rule-card";
import { SAMPLE_RULES } from "./sample-data";

export default function RulesLibraryClient() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selected, setSelected] = useState<any | null>(null);
  const [view, setView] = useState<'table'|'grid'>('table');

  const rules = useMemo(() => SAMPLE_RULES, []);

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8faff_0%,#f4f7ff_42%,#eef3fb_100%)] text-slate-900">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header onOpenSidebar={() => setMobileOpen(true)} title="Rules Library" subtitle="Manage reusable XML invoice validation rules and compliance templates." />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1400px] space-y-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center gap-4">
                {/* <SearchBar value={""} onChange={() => {}} /> */}
                {/* <div className="hidden lg:block">
                  <button className="rounded-xl bg-indigo-600 px-3 py-2 text-sm text-white">Import Rules</button>
                </div> */}
              </div>
              <div className="flex items-center gap-3">
                <button onClick={() => setView(view === 'table' ? 'grid' : 'table')} className="rounded-xl border px-3 py-2">{view === 'table' ? 'Grid View' : 'Table View'}</button>
                <button className="rounded-xl bg-indigo-600 px-3 py-2 text-sm text-white">Create New Rule</button>
              </div>
            </div>

            <StatsCards />

            <div className="rounded-2xl bg-transparent p-4">
              {/* <RuleFilters /> */}
            </div>

            {view === 'table' ? (
              <div>
                <RulesTable onSelect={(r) => setSelected(r)} />
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {rules.map((r) => (
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
