"use client";

import React from "react";
import { motion } from "framer-motion";
import { Download } from "lucide-react";
import { useApiData } from "@/lib/hooks";
import { ErrorAlert } from "../ui/error-alert";
import type { ValidationReportDetail, ValidationReportRow } from "@/lib/types";

const formatTimestamp = (value?: string | null) => {
  if (!value) return "-";
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

const getStatusColor = (status: string) => {
  switch (status) {
    case "PASS":
      return "bg-emerald-100 text-emerald-700";
    case "FAIL":
      return "bg-rose-100 text-rose-700";
    case "PARTIAL":
    case "ERROR":
      return "bg-amber-100 text-amber-700";
    default:
      return "bg-slate-100 text-slate-700";
  }
};

export default function ResultDetailDrawer({
  result,
  onClose,
}: {
  result?: ValidationReportRow | null;
  onClose?: () => void;
}) {
  const endpoint = result ? `/reports/${result.invoice_id}/details` : null;
  const { data, isLoading, error, refetch } = useApiData<ValidationReportDetail>(endpoint, {
    skip: !result,
  });

  React.useEffect(() => {
    if (!result) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [result, onClose]);

  if (!result) return null;

  const handleDownload = () => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    window.open(`${apiBase}/reports/${result.invoice_id}/pdf`, "_blank", "noopener,noreferrer");
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm cursor-pointer"
      />
      <motion.aside
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 220 }}
        className="fixed right-0 top-0 z-50 h-full w-[520px] overflow-y-auto bg-white p-6 shadow-2xl border-l border-slate-100 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">Validation Report</h3>
          <p className="text-sm text-slate-500">Invoice: {result.invoice_identifier}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50"
          >
            <span className="inline-flex items-center gap-1">
              <Download className="h-3.5 w-3.5" />
              PDF
            </span>
          </button>
          <button onClick={onClose} className="text-slate-500">
            Close
          </button>
        </div>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading details...</p>}
      {error && <ErrorAlert error={error} onRetry={refetch} />}

      {!isLoading && !error && data && (
        <div className="space-y-5">
          <section>
            <h4 className="text-sm font-medium">Invoice Information</h4>
            <div className="mt-2 space-y-1 text-sm text-slate-700">
              <div>Invoice ID: {data.invoice_identifier}</div>
              <div>Uploaded: {formatTimestamp(data.uploaded_at)}</div>
              <div>Processed: {formatTimestamp(data.processed_at)}</div>
              <div>
                Execution Status:{" "}
                <span className="font-medium">{data.execution_status || "UNKNOWN"}</span>
              </div>
            </div>
          </section>

          <section>
            <h4 className="text-sm font-medium">Overall Status</h4>
            <span
              className={`mt-2 inline-block rounded-full px-3 py-1 text-xs font-medium ${getStatusColor(
                data.overall_status
              )}`}
            >
              {data.overall_status}
            </span>
          </section>

          <section>
            <h4 className="text-sm font-medium">Validation Checklist</h4>
            <div className="mt-2 space-y-2">
              {data.checklist.map((item, idx) => (
                <div key={`${item.rule_id ?? "na"}-${idx}`} className="rounded-md border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-medium text-slate-800">{item.rule_text}</div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${getStatusColor(
                        item.status
                      )}`}
                    >
                      {item.status}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-slate-600">{item.message || "No message"}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    Execution: {item.execution_result} | Time: {formatTimestamp(item.validated_at)}
                  </div>
                </div>
              ))}
              {data.checklist.length === 0 && (
                <div className="rounded-md border border-dashed p-3 text-sm text-slate-500">
                  No checklist items found for this report.
                </div>
              )}
            </div>
          </section>
        </div>
      )}
      </motion.aside>
    </>
  );
}
