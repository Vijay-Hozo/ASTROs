"use client";

import Header from "@/components/rule-engine/header";
import MetadataCard from "@/components/rule-engine/metadata-card";
import ParsedRuleCard from "@/components/rule-engine/parsed-rule-card";
import ProgressSteps from "@/components/rule-engine/progress-steps";
import RuleInputCard from "@/components/rule-engine/rule-input-card";
import RuleTestPanel from "@/components/rule-engine/rule-test-panel";
import ValidationLogicCard from "@/components/rule-engine/validation-logic-card";
import AddRuleCard from "@/components/rule-engine/add-rule-card";
import FieldReferenceCard from "@/components/rule-engine/field-reference-card";
import { DesktopSidebar, MobileSidebar } from "@/components/rule-engine/sidebar";
import { useState } from "react";
import type { ParseRuleResponse } from "@/lib/types";

export default function RuleEnginePage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [ruleText, setRuleText] = useState("");
  const [parsedRule, setParsedRule] = useState<ParseRuleResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleRuleInput = (rule: string) => {
    setRuleText(rule);
  };

  const handleParsed = (result: ParseRuleResponse) => {
    setParsedRule(result);
  };

  const handleLogicChange = (logic: { xpath?: string; xslt?: string; python_logic?: string }) => {
    setParsedRule((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        xpath: logic.xpath ?? prev.xpath,
        xslt: logic.xslt ?? prev.xslt,
        python_logic: logic.python_logic ?? prev.python_logic,
      };
    });
  };

  const handleRuleSaved = (ruleId: number) => {
    console.log("Rule saved:", ruleId);
    // Could reset state here if desired
  };

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
                <RuleInputCard onParsed={handleParsed} onRuleChange={handleRuleInput} />
                <div className="grid gap-6 lg:grid-cols-2">
                  <ParsedRuleCard result={parsedRule} isLoading={isLoading} />
                  <ValidationLogicCard result={parsedRule} isLoading={isLoading} onLogicChange={handleLogicChange} />
                </div>
                <AddRuleCard result={parsedRule} ruleText={ruleText} onSaved={handleRuleSaved} />
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
