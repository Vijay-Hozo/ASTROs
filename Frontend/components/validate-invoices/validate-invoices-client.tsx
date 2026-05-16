"use client";

import React, { useState } from "react";
import { DesktopSidebar, MobileSidebar } from "@/components/rule-engine/sidebar";
import Header from "@/components/rule-engine/header";
import ValidateInvoicesShell from "@/components/validate-invoices/validate-invoices-shell";

export default function ValidateInvoicesClient() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8faff_0%,#f4f7ff_42%,#eef3fb_100%)] text-slate-900">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header onOpenSidebar={() => setMobileOpen(true)} title="Validate Invoices" subtitle="Upload invoices and validate against rules" />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1600px] space-y-6">
            <ValidateInvoicesShell />
          </div>
        </main>
      </div>
    </div>
  );
}
