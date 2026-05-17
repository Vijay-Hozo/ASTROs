"use client";

import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { MoreHorizontal, Trash2 } from "lucide-react";
import { useApiData, useDelete } from "@/lib/hooks";
import { TableLoadingSkeleton } from "../ui/loading-skeleton";
import { ErrorAlert, EmptyState } from "../ui/error-alert";
import type { Rule } from "@/lib/types";

function getRuleType(rule: Rule): string {
  const parsed = rule.parsed_json as any;
  if (!parsed) return "unknown";
  return parsed.rule_type || parsed.parsed_rule?.rule_type || "unknown";
}

export default function RulesTable({ 
  onSelect,
  onDelete,
  refreshTrigger,
}: { 
  onSelect?: (r: Rule) => void;
  onDelete?: (id: number) => void;
  refreshTrigger?: number;
}) {
  const [query, setQuery] = useState("");
  const { data: rules, isLoading, error, refetch } = useApiData<Rule[]>("/rules");
  const { mutate: deleteRule, isLoading: isDeleting } = useDelete({
    onSuccess: () => {
      onDelete?.(0); // Signal deletion success
      refetch();
    },
  });

  // Refetch when refresh trigger changes
  React.useEffect(() => {
    refetch();
  }, [refreshTrigger, refetch]);

  const filtered = useMemo(() => {
    if (!rules || !query) return rules || [];
    const q = query.toLowerCase();
    return rules.filter((r) =>
      r.rule_text.toLowerCase().includes(q) ||
      r.id.toString().includes(q) ||
      getRuleType(r).toLowerCase().includes(q)
    );
  }, [rules, query]);

  const handleDelete = async (id: number) => {
    if (confirm("Delete this rule? This action cannot be undone.")) {
      try {
        await deleteRule(`/rules/${id}`);
      } catch {
        // Error is handled in the hook
      }
    }
  };

  if (isLoading) return <TableLoadingSkeleton />;

  if (error) {
    return (
      <div className="rounded-2xl bg-white p-4 shadow-sm overflow-hidden">
        <ErrorAlert error={error} onRetry={refetch} />
      </div>
    );
  }

  if (!rules || rules.length === 0) {
    return (
      <div className="rounded-2xl bg-white p-4 shadow-sm overflow-hidden">
        <EmptyState
          title="No rules yet"
          description="Create rules on the dashboard to see them here."
        />
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm overflow-hidden">
      <div className="mb-3 flex items-center justify-between gap-4">
        <div className="text-sm font-semibold">Rules ({rules.length})</div>
        <div className="flex items-center gap-2">
          <input
            placeholder="Search table..."
            className="rounded-md border px-3 py-1 text-sm bg-buttonBlue text-buttonText placeholder:text-buttonText"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="pb-2">Rule ID</th>
              <th className="pb-2">Rule Text</th>
              <th className="pb-2">Type</th>
              <th className="pb-2">Severity</th>
              <th className="pb-2">Created</th>
              <th className="pb-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <motion.tr key={r.id} className="border-t">
                <td className="py-3 w-[60px]">{r.id}</td>
                <td className="py-3 max-w-xs truncate">{r.rule_text}</td>
                <td className="py-3">
                  <span className="inline-block bg-slate-100 px-2 py-1 rounded text-xs">
                    {getRuleType(r)}
                  </span>
                </td>
                <td className="py-3">
                  <span
                    className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                      r.severity === "high"
                        ? "bg-red-100 text-red-700"
                        : r.severity === "medium"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-blue-100 text-blue-700"
                    }`}
                  >
                    {r.severity}
                  </span>
                </td>
                <td className="py-3 text-xs">
                  {new Date(r.created_at).toLocaleDateString()}
                </td>
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onSelect?.(r)}
                      className="rounded-md bg-slate-50 px-2 py-1 text-xs hover:bg-slate-100"
                    >
                      View
                    </button>
                    <button
                      onClick={() => handleDelete(r.id)}
                      disabled={isDeleting}
                      className="rounded-md px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
