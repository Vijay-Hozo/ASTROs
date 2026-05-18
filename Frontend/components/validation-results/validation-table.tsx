"use client";

import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Eye, Trash2 } from "lucide-react";
import { useDelete } from "@/lib/hooks";
import { TableLoadingSkeleton } from "../ui/loading-skeleton";
import { ErrorAlert } from "../ui/error-alert";
import ConfirmDeleteModal from "../ui/confirm-delete-modal";
import type { ValidationReportRow } from "@/lib/types";
import type { APIError } from "@/lib/api-client";

const formatTimestamp = (value: string) => {
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "-";
  return dt.toLocaleString("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export default function ValidationTable({
  onView,
  results,
  isLoading: parentLoading,
  error,
  refetch,
}: {
  onView?: (r: ValidationReportRow) => void;
  results: ValidationReportRow[];
  isLoading?: boolean;
  error?: APIError | null;
  refetch?: () => void;
}) {
  const [query, setQuery] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<ValidationReportRow | null>(null);
  const { mutate: deleteReport, isLoading: isDeleting } = useDelete({
    onSuccess: () => refetch?.(),
  });
  const resultsList = results || [];

  const filtered = useMemo(() => {
    if (!query || resultsList.length === 0) return resultsList;
    const q = query.toLowerCase();
    return resultsList.filter(
      (r) =>
        r.invoice_id.toString().includes(q) ||
        (r.invoice_identifier || "").toLowerCase().includes(q) ||
        r.id.toString().includes(q) ||
        r.overall_status.toLowerCase().includes(q) ||
        (r.xslt_filename || "").toLowerCase().includes(q)
    );
  }, [resultsList, query]);

  if (parentLoading) return <TableLoadingSkeleton />;

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
      case "PARTIAL":
        return "bg-amber-100 text-amber-700";
      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteReport(`/reports/${deleteTarget.invoice_id}`);
      setDeleteTarget(null);
    } catch {
      // Hook handles error.
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
              <th className="pb-2">Rule File</th>
              <th className="pb-2">Overall Status</th>
              <th className="pb-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => {
              const ruleFileDisplay = r.xslt_filename?.toLowerCase().includes("india")
                ? "Indian_rule"
                : r.xslt_filename || "N/A";
              return (
                <motion.tr key={r.id} className="border-t hover:bg-slate-50">
                  <td className="py-3 text-xs">{r.id}</td>
                  <td className="py-3 text-xs">{r.invoice_identifier || "UNKNOWN"}</td>
                  <td className="py-3 text-xs font-medium text-slate-700">{ruleFileDisplay}</td>
                  <td className="py-3">
                    <span className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${getStatusColor(r.overall_status)}`}>
                      {r.overall_status}
                    </span>
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onView?.(r)}
                        className="rounded-md bg-slate-50 px-2 py-1 text-xs hover:bg-slate-100"
                      >
                        <span className="inline-flex items-center gap-1">
                          <Eye className="h-3.5 w-3.5" />
                          View Details
                        </span>
                      </button>
                      <button
                        onClick={() => setDeleteTarget(r)}
                        disabled={isDeleting}
                        className="rounded-md px-2 py-1 text-xs text-rose-600 hover:bg-rose-50 disabled:opacity-50"
                        aria-label={`Delete report for ${r.invoice_identifier}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <ConfirmDeleteModal
        open={deleteTarget !== null}
        message="Are you sure you want to permanently delete this validation report?"
        isDeleting={isDeleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
