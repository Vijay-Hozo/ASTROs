/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useState } from "react";
import { DesktopSidebar, MobileSidebar } from "@/components/rule-engine/sidebar";
import Header from "@/components/rule-engine/header";
import StatsCards from "./stats-cards";
import RulesTable from "./rules-table";
import RuleDetailDrawer from "./rule-detail-drawer";
import RuleCard from "./rule-card";
import { useApiData, useMutate } from "@/lib/hooks";
import { ErrorAlert } from "../ui/error-alert";
import type { Rule, CreateRuleRequest, CreateRuleResponse } from "@/lib/types";

interface CreateRuleModalState {
  isOpen: boolean;
  ruleText: string;
  severity: "low" | "medium" | "high";
  isSubmitting: boolean;
}

export default function RulesLibraryClient() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selected, setSelected] = useState<Rule | null>(null);
  const [view, setView] = useState<"table" | "grid">("table");
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Fetch rules
  const { data: rules, isLoading, error, refetch } = useApiData<Rule[]>("/rules");
  const rulesList = rules || [];

  // Create rule mutation
  const { mutate: createRule, isLoading: isCreating, error: createError } = useMutate<CreateRuleResponse>(
    "/rules",
    {
      onSuccess: () => {
        setModalState((s) => ({ ...s, isOpen: false, ruleText: "", severity: "high" }));
        setRefreshTrigger((t) => t + 1);
      },
    }
  );

  const [modalState, setModalState] = useState<CreateRuleModalState>({
    isOpen: false,
    ruleText: "",
    severity: "high",
    isSubmitting: false,
  });

  const handleOpenCreateModal = () => {
    setModalState({
      isOpen: true,
      ruleText: "",
      severity: "high",
      isSubmitting: false,
    });
  };

  const handleSubmitRule = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!modalState.ruleText.trim()) {
      alert("Please enter a rule");
      return;
    }

    try {
      setModalState((s) => ({ ...s, isSubmitting: true }));
      await createRule({
        rule_text: modalState.ruleText,
        severity: modalState.severity,
      } as CreateRuleRequest);
    } catch (err) {
      console.error("Failed to create rule:", err);
    } finally {
      setModalState((s) => ({ ...s, isSubmitting: false }));
    }
  };

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
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center gap-4" />
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setView(view === "table" ? "grid" : "table")}
                  className="rounded-xl border px-3 py-2 text-sm hover:bg-slate-50"
                >
                  {view === "table" ? "Grid View" : "Table View"}
                </button>
                <button
                  onClick={handleOpenCreateModal}
                  className="rounded-xl bg-indigo-600 px-3 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                  disabled={isCreating}
                >
                  {isCreating ? "Creating..." : "Create New Rule"}
                </button>
              </div>
            </div>

            <StatsCards />

            {createError && (
              <ErrorAlert error={createError} onRetry={() => setModalState({ ...modalState, isOpen: true })} />
            )}

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

      {/* Create Rule Modal */}
      {modalState.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="rounded-lg bg-white p-6 shadow-lg max-w-md w-full mx-4">
            <h2 className="text-lg font-semibold mb-4">Create New Rule</h2>

            <form onSubmit={handleSubmitRule} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Rule Text</label>
                <textarea
                  value={modalState.ruleText}
                  onChange={(e) => setModalState((s) => ({ ...s, ruleText: e.target.value }))}
                  placeholder="Describe the rule in natural language..."
                  className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  rows={4}
                  maxLength={500}
                  disabled={isCreating}
                />
                <p className="text-xs text-slate-500 mt-1">
                  {modalState.ruleText.length}/500
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Severity</label>
                <select
                  value={modalState.severity}
                  onChange={(e) => setModalState((s) => ({ ...s, severity: e.target.value as any }))}
                  className="w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  disabled={isCreating}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <div className="flex gap-2 justify-end pt-4">
                <button
                  type="button"
                  onClick={() => setModalState((s) => ({ ...s, isOpen: false }))}
                  className="rounded-md border px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
                  disabled={isCreating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                  disabled={isCreating}
                >
                  {isCreating ? "Creating..." : "Create Rule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
