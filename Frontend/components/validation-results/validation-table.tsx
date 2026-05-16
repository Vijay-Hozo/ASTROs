"use client";

import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useApiData } from "@/lib/hooks";
import { TableLoadingSkeleton } from "../ui/loading-skeleton";
import { ErrorAlert } from "../ui/error-alert";
import type { ValidationResult } from "@/lib/types";

export default function ValidationTable({
  onView,
  isLoading: parentLoading,
}: {
  onView?: (r: ValidationResult) => void;
  isLoading?: boolean;
}) {
  const [query, setQuery] = useState("");
  const { data: results, isLoading, error, refetch } = useApiData<ValidationResult[]>("/results");
  const resultsList = results || [];

  const filtered = useMemo(() => {
    if (!query || resultsList.length === 0) return resultsList;
    const q = query.toLowerCase();
    return resultsList.filter(
      (r) =>
        r.invoice_id.toString().includes(q) ||
        r.id.toString().includes(q) ||
        r.status.toLowerCase().includes(q)
    );
  }, [resultsList, query]);

  if (isLoading || parentLoading) return <TableLoadingSkeleton />;

  if (error) {
    return (
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <ErrorAlert error={error} onRetry={refetch} />
      </div>
    );
  }

  if (resultsList.length === 0) {
    return (
      <div className="rounded-xl bg-white p-4 shadow-sm text-center py-12">
        <p className="text-slate-500">No validation results yet.</p>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "PASS":
        return "bg-emerald-100 text-emerald-700";
      case "FAIL":
        return "bg-rose-100 text-rose-700";
      case "ERROR":
        return "bg-amber-100 text-amber-700";
      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-semibold">Validation Results ({resultsList.length})</div>
        <div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search"
            className="rounded-md border px-2 py-1 text-sm text-white bg-buttonBlue placeholder:text-white"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="pb-2">Result ID</th>
              <th className="pb-2">Invoice ID</th>
              <th className="pb-2">Rule ID</th>
              <th className="pb-2">Status</th>
              <th className="pb-2">Message</th>
              <th className="pb-2">Date</th>
              <th className="pb-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <motion.tr key={r.id} className="border-t hover:bg-slate-50">
                <td className="py-3 text-xs">{r.id}</td>
                <td className="py-3 text-xs">{r.invoice_id}</td>
                <td className="py-3 text-xs">{r.rule_id}</td>
                <td className="py-3">
                  <span className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${getStatusColor(r.status)}`}>
                    {r.status}
                  </span>
                </td>
                <td className="py-3 text-xs max-w-xs truncate">{r.message}</td>
                <td className="py-3 text-xs">
                  {new Date(r.created_at).toLocaleDateString()}
                </td>
                <td className="py-3">
                  <button
                    onClick={() => onView?.(r)}
                    className="rounded-md bg-slate-50 px-2 py-1 text-xs hover:bg-slate-100"
                  >
                    View Details
                  </button>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
