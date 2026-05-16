"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { useState, useMemo } from "react";
import Header from "./header";
import ParsedRuleCard from "./parsed-rule-card";
import RuleInput from "./rule-input";
import StatsCard from "./stats-card";
import SummaryCard from "./summary-card";
import { DesktopSidebar, MobileSidebar } from "./sidebar";
import UploadCard from "./upload-card";
import ValidationLogicCard from "./validation-logic-card";
import ValidationTable from "./validation-table";
import XmlPreview from "./xml-preview";
import { useApiData } from "@/lib/hooks";
import { ErrorAlert } from "../ui/error-alert";
import { StatsCardLoadingSkeleton } from "../ui/loading-skeleton";
import type { DashboardStats, SingleValidationResponse, InvoiceValidationResponse } from "@/lib/types";

export default function DashboardShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [xmlContent, setXmlContent] = useState("");
  const [validationResult, setValidationResult] = useState<SingleValidationResponse | null>(null);
  const [invoiceValidationResult, setInvoiceValidationResult] = useState<InvoiceValidationResponse | null>(null);
  const [uploadedInvoiceId, setUploadedInvoiceId] = useState<number | null>(null);
  const [refreshStats, setRefreshStats] = useState(false);

  const { data: dashboardStats, isLoading, error, refetch } = useApiData<DashboardStats>("/dashboard/stats", {
    refetchInterval: 60000, // Refetch every 60 seconds
  });

  // Refresh stats when invoice is uploaded or validated
  const handleUploadSuccess = (invoiceId: number) => {
    setUploadedInvoiceId(invoiceId);
    setRefreshStats((s) => !s);
    refetch();
  };

  const handleValidationSuccess = (result: InvoiceValidationResponse) => {
    setInvoiceValidationResult(result);
    setRefreshStats((s) => !s);
    refetch();
  };

  const stats = useMemo(() => {
    if (!dashboardStats) {
      return [
        {
          title: "Total Rules",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: ShieldCheck,
          iconBg: "bg-indigo-50",
          iconColor: "text-indigo-600",
        },
        {
          title: "Invoices Validated",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: FileText,
          iconBg: "bg-emerald-50",
          iconColor: "text-emerald-600",
        },
        {
          title: "Passed Invoices",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: CheckCircle2,
          iconBg: "bg-emerald-50",
          iconColor: "text-emerald-600",
        },
        {
          title: "Failed Invoices",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: AlertTriangle,
          iconBg: "bg-rose-50",
          iconColor: "text-rose-600",
        },
        {
          title: "Total Validations",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: TriangleAlert,
          iconBg: "bg-amber-50",
          iconColor: "text-amber-600",
        },
      ];
    }

    const passRate = dashboardStats.pass_rate.toFixed(1);
    const failedCount = dashboardStats.total_validations - dashboardStats.passed_validations;

    return [
      {
        title: "Total Rules",
        value: String(dashboardStats.total_rules),
        note: "Active rules",
        noteColor: "text-indigo-600",
        icon: ShieldCheck,
        iconBg: "bg-indigo-50",
        iconColor: "text-indigo-600",
      },
      {
        title: "Invoices Validated",
        value: String(dashboardStats.total_invoices),
        note: `${dashboardStats.total_validations} validations`,
        noteColor: "text-emerald-600",
        icon: FileText,
        iconBg: "bg-emerald-50",
        iconColor: "text-emerald-600",
      },
      {
        title: "Passed Invoices",
        value: String(dashboardStats.passed_validations),
        note: `${passRate}% Pass Rate`,
        noteColor: "text-emerald-600",
        icon: CheckCircle2,
        iconBg: "bg-emerald-50",
        iconColor: "text-emerald-600",
      },
      {
        title: "Failed Invoices",
        value: String(failedCount),
        note: `${(100 - parseFloat(passRate)).toFixed(1)}% Fail Rate`,
        noteColor: "text-rose-600",
        icon: AlertTriangle,
        iconBg: "bg-rose-50",
        iconColor: "text-rose-600",
      },
      {
        title: "Total Validations",
        value: String(dashboardStats.total_validations),
        note: "All validations",
        noteColor: "text-amber-600",
        icon: TriangleAlert,
        iconBg: "bg-amber-50",
        iconColor: "text-amber-600",
      },
    ];
  }, [dashboardStats]);

  return (
    <div className="min-h-screen bg-[#f6f8ff]">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header onOpenSidebar={() => setMobileOpen(true)} />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1440px] space-y-6">
            {error && <ErrorAlert error={error} onRetry={refetch} />}

            {isLoading ? (
              <StatsCardLoadingSkeleton />
            ) : (
              <motion.section
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5"
              >
                {stats.map((item) => (
                  <StatsCard key={item.title} {...item} />
                ))}
              </motion.section>
            )}

            <section className="grid grid-cols-1 gap-6 xl:grid-cols-12">
              <div className="space-y-6 xl:col-span-8">
                <RuleInput
                  xmlContent={xmlContent}
                  onValidationResult={setValidationResult}
                  onXmlRequired={() => {}} // Can add custom handling here
                />
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <ParsedRuleCard result={validationResult} />
                  <ValidationLogicCard />
                </div>
                <ValidationTable />
              </div>

              <div className="space-y-6 xl:col-span-4">
                <UploadCard
                  onUploadSuccess={handleUploadSuccess}
                  onValidationSuccess={handleValidationSuccess}
                />
                <SummaryCard />
                <XmlPreview value={xmlContent} onChange={setXmlContent} />
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}