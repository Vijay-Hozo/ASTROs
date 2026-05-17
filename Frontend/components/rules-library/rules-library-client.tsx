"use client";

import React, { useState } from "react";
import { DesktopSidebar, MobileSidebar } from "../dashboard/sidebar";
import Header from "../dashboard/header";
import XsltFilesTable from "./xslt-files-table";
import StatsCards from "./stats-cards";
import { ErrorAlert } from "../ui/error-alert";
import { useApiData } from "../../lib/hooks";
import type { Rule } from "../../lib/types";
import ActiveXsltBanner from "@/components/workspace/active-xslt-banner";

export default function RulesLibraryClient() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Keep rules data for the stats cards at top
  const { error } = useApiData<Rule[]>("/rules");

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8faff_0%,#f4f7ff_42%,#eef3fb_100%)] text-slate-900">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header
          onOpenSidebar={() => setMobileOpen(true)}
          title="Rules Library"
          subtitle="Manage XSLT validation files and their linked compliance rules."
        />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1400px] space-y-6">
            <ActiveXsltBanner compact />

            <StatsCards />

            {error && <ErrorAlert error={error} onRetry={() => setRefreshTrigger((t) => t + 1)} />}

            {/* XSLT Files Table — one row per XSLT file */}
            <XsltFilesTable refreshTrigger={refreshTrigger} />
          </div>
        </main>
      </div>
    </div>
  );
}
