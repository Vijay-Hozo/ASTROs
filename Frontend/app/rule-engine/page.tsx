"use client";

import Header from "@/components/rule-engine/header";
import MetadataCard from "@/components/rule-engine/metadata-card";
import ParsedRuleCard from "@/components/rule-engine/parsed-rule-card";
import ProgressSteps from "@/components/rule-engine/progress-steps";
import RuleInputCard from "@/components/rule-engine/rule-input-card";
import RuleTestPanel from "@/components/rule-engine/rule-test-panel";
import ValidationLogicCard from "@/components/rule-engine/validation-logic-card";
import FieldReferenceCard from "@/components/rule-engine/field-reference-card";
import XmlPreviewCard from "@/components/rule-engine/xml-preview-card";
import { DesktopSidebar, MobileSidebar } from "@/components/rule-engine/sidebar";
import { useState } from "react";

export default function RuleEnginePage() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8faff_0%,#f4f7ff_42%,#eef3fb_100%)] text-slate-900">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header
          onOpenSidebar={() => setMobileOpen(true)}
          title="Rule Engine"
          subtitle="Create, parse and manage invoice validation rules in plain English."
        />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1600px] space-y-6">
            <ProgressSteps />

            <section className="grid gap-6 xl:grid-cols-12">
              <div className="space-y-6 xl:col-span-8">
                <RuleInputCard />
                <div className="grid gap-6 lg:grid-cols-2">
                  <ParsedRuleCard />
                  <ValidationLogicCard />
                </div>
                <XmlPreviewCard />
              </div>

              <div className="space-y-6 xl:col-span-4">
                <MetadataCard />
                <FieldReferenceCard />
                <RuleTestPanel />
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}