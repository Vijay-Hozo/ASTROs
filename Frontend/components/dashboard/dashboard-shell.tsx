"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { useState } from "react";
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

const stats = [
  {
    title: "Total Rules",
    value: "128",
    note: "+12 this week",
    noteColor: "text-indigo-600",
    icon: ShieldCheck,
    iconBg: "bg-indigo-50",
    iconColor: "text-indigo-600",
  },
  {
    title: "Invoices Validated",
    value: "452",
    note: "+80 this week",
    noteColor: "text-emerald-600",
    icon: FileText,
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-600",
  },
  {
    title: "Passed Invoices",
    value: "272",
    note: "60.2% Pass Rate",
    noteColor: "text-emerald-600",
    icon: CheckCircle2,
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-600",
  },
  {
    title: "Failed Invoices",
    value: "180",
    note: "39.8% Fail Rate",
    noteColor: "text-rose-600",
    icon: AlertTriangle,
    iconBg: "bg-rose-50",
    iconColor: "text-rose-600",
  },
  {
    title: "Total Validations",
    value: "320",
    note: "+45 this week",
    noteColor: "text-amber-600",
    icon: TriangleAlert,
    iconBg: "bg-amber-50",
    iconColor: "text-amber-600",
  },
];

export default function DashboardShell() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#f6f8ff]">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header onOpenSidebar={() => setMobileOpen(true)} />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1440px] space-y-6">
            <motion.section
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5"
            >
              {stats.map((item) => (
                <StatsCard key={item.title} {...item} />
              ))}
            </motion.section>

            <section className="grid grid-cols-1 gap-6 xl:grid-cols-12">
              <div className="space-y-6 xl:col-span-8">
                <RuleInput />
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <ParsedRuleCard />
                  <ValidationLogicCard />
                </div>
                <ValidationTable />
              </div>

              <div className="space-y-6 xl:col-span-4">
                <UploadCard />
                <SummaryCard />
                <XmlPreview />
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}