/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import React from "react";
import { motion } from "framer-motion";
import { Download, X, CheckCircle2, XCircle, FileCode2, ChevronUp, ExternalLink } from "lucide-react";
import type { ValidationReportRow } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://astros.onrender.com";

const getStatusColor = (status: string) => {
  switch (status) {
    case "PASS":
      return "bg-emerald-100 text-emerald-700 border-emerald-200";
    case "FAIL":
      return "bg-rose-100 text-rose-700 border-rose-200";
    case "PARTIAL":
    case "ERROR":
      return "bg-amber-100 text-amber-700 border-amber-200";
    default:
      return "bg-slate-100 text-slate-700 border-slate-200";
  }
};

export default function ResultDetailDrawer({
  result,
  onClose,
}: {
  result?: ValidationReportRow | null;
  onClose?: () => void;
}) {
  const [tags, setTags] = React.useState<string[]>([]);
  const [rules, setRules] = React.useState<{ rule_name: string; status: "PASS" | "FAIL" }[] | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // XSLT Inline expansion state
  const [xsltExpanded, setXsltExpanded] = React.useState(false);
  const [xsltDetails, setXsltDetails] = React.useState<any>(null);
  const [xsltLoading, setXsltLoading] = React.useState(false);

  const xsltFilename = result?.xslt_filename ?? "N/A";
  const xsltId = (result as any)?.xslt_id || result?.xslt_filename || "N/A";
  const llmMessage = (result as any)?.llm_message || (result as any)?.parsed_message;

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

  // Fetch drawer tags and rules details on load
  React.useEffect(() => {
    if (!result) return;

    let active = true;
    setIsLoading(true);
    setError(null);
    setTags([]);
    setRules(null);

    const fetchData = async () => {
      try {
        const [tagsRes, rulesRes] = await Promise.all([
          fetch(`${API_BASE}/api/results/${result.id}/tags`)
            .then((r) => r.ok ? r.json() : { tags: [] })
            .catch(() => ({ tags: [] })),
          fetch(`${API_BASE}/api/results/${result.id}/rules`)
            .then((r) => r.ok ? r.json() : { rules: [] })
            .catch(() => ({ rules: [] })),
        ]);

        if (active) {
          setTags(tagsRes.tags || []);
          setRules(rulesRes.rules || []);
          setIsLoading(false);
        }
      } catch (err: any) {
        if (active) {
          // Silent fail — show nothing
          setTags([]);
          setRules([]);
          setIsLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      active = false;
    };
  }, [result]);

  if (!result) return null;

  const handleDownload = () => {
    window.open(`${API_BASE}/api/results/${result.invoice_id}/pdf`, "_blank", "noopener,noreferrer");
  };

  const handleXsltToggle = async () => {
    // If already expanded, just close
    if (xsltExpanded) {
      setXsltExpanded(false);
      return;
    }

    // If already loaded, just open
    if (xsltDetails) {
      setXsltExpanded(true);
      return;
    }

    // Otherwise fetch details
    setXsltLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/xslt-files/${encodeURIComponent(xsltId)}/details`);
      if (!res.ok) throw new Error("Failed to fetch XSLT details");
      const data = await res.json();
      setXsltDetails(data);
      setXsltExpanded(true);
    } catch (err: any) {
      console.error("Failed to load XSLT details:", err);
    } finally {
      setXsltLoading(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm cursor-pointer"
      />

      {/* Drawer */}
      <motion.aside
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 220 }}
        className="fixed right-0 top-0 z-50 h-full w-[540px] overflow-y-auto bg-white shadow-2xl border-l border-slate-100 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="flex items-start justify-between border-b border-slate-100 px-6 py-5 flex-shrink-0 bg-white">
          <div>
            <h3 className="text-base font-bold text-slate-900">Validation Report Details</h3>
            <p className="text-xs text-slate-500 mt-0.5">Invoice ID: {result.invoice_identifier || `#${result.invoice_id}`}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition"
            >
              <Download className="h-3.5 w-3.5" />
              PDF
            </button>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {isLoading && (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
            </div>
          )}

          {!isLoading && (
            <>
              {/* SECTION 1 — Invoice XML Tags */}
              <section>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                  Invoice XML Tags
                </h4>
                <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto pr-1">
                  {tags && tags.length > 0 ? (
                    tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-1 text-xs rounded-md bg-slate-100 text-slate-600 border border-slate-200 font-mono"
                      >
                        {tag}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400 italic">No XML tags found.</span>
                  )}
                </div>
              </section>

              {/* SECTION 2 — LLM Parsed Message (Validation Summary) */}
              {llmMessage && (
                <section>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                    Validation Summary
                  </h4>
                  <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 border border-slate-100 rounded-xl p-4">
                    {llmMessage}
                  </p>
                </section>
              )}

              {/* SECTION 3 — Rules Used with Results */}
              <section>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                  Rules Applied
                </h4>
                <div className="overflow-hidden rounded-xl border border-slate-100">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50">
                        <th className="px-4 py-2.5 text-left text-[10px] font-bold uppercase tracking-wider text-slate-400">
                          Rule Name
                        </th>
                        <th className="px-4 py-2.5 text-right text-[10px] font-bold uppercase tracking-wider text-slate-400 w-24">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {rules && rules.length > 0 ? (
                        rules.map((r, idx) => {
                          const isPass = r.status === "PASS";
                          return (
                            <tr
                              key={idx}
                              className={isPass ? "bg-emerald-50/10 hover:bg-emerald-50/20" : "bg-rose-50/10 hover:bg-rose-50/20"}
                            >
                              <td className="px-4 py-3 text-xs font-medium text-slate-800 leading-snug">
                                {r.rule_name}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <span
                                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold border ${getStatusColor(
                                    r.status
                                  )}`}
                                >
                                  {r.status}
                                </span>
                              </td>
                            </tr>
                          );
                        })
                      ) : (
                        <tr>
                          <td colSpan={2} className="px-4 py-8 text-center text-xs text-slate-400 italic">
                            No rules applied to this validation.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* SECTION 4 — XSLT File Used */}
              <section className="pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  XSLT File Used
                </h4>
                <div className="space-y-2">
                  <button
                    onClick={handleXsltToggle}
                    className="inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-700 transition"
                  >
                    Validated against: {xsltFilename}
                    {xsltLoading 
                      ? <span className="text-xs text-slate-400 ml-1">Loading...</span>
                      : xsltExpanded 
                        ? <ChevronUp className="h-3.5 w-3.5" />
                        : <ExternalLink className="h-3.5 w-3.5" />
                    }
                  </button>

                  {/* Inline expansion — no modal */}
                  {xsltExpanded && xsltDetails && (
                    <div className="mt-3 rounded-xl border border-indigo-100 bg-indigo-50/40 p-4 space-y-3">
                      
                      {/* Header info */}
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                            XSLT File
                          </span>
                          <span className="text-xs font-semibold text-slate-800">
                            {xsltDetails.xslt_filename}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                            Sample XML
                          </span>
                          <span className="text-xs font-semibold text-slate-800">
                            {xsltDetails.sample_filename}
                          </span>
                        </div>
                      </div>

                      {/* Divider */}
                      <div className="border-t border-indigo-100" />

                      {/* Rules list */}
                      <div>
                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                          Rules in this XSLT ({xsltDetails.rules.length})
                        </p>

                        {xsltDetails.rules.length === 0 ? (
                          <p className="text-xs text-slate-400 italic">
                            No rules created yet for this XSLT file.
                          </p>
                        ) : (
                          <ol className="space-y-1.5">
                            {xsltDetails.rules.map((rule: any, idx: number) => (
                              <li
                                key={idx}
                                className="flex items-start gap-2.5 text-xs text-slate-700"
                              >
                                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 font-bold text-[10px] flex items-center justify-center">
                                  {idx + 1}
                                </span>
                                <span className="leading-relaxed pt-0.5">
                                  {rule.rule_name}
                                </span>
                              </li>
                            ))}
                          </ol>
                        )}
                      </div>

                    </div>
                  )}
                </div>
              </section>
            </>
          )}
        </div>

        {/* Drawer Footer */}
        <div className="border-t border-slate-100 bg-slate-50/50 px-6 py-4 flex-shrink-0 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            {rules?.length ?? 0} rule{(rules?.length ?? 0) !== 1 ? "s" : ""} evaluated
          </p>
          <button
            onClick={handleDownload}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition"
          >
            <Download className="h-4 w-4" />
            Download PDF Report
          </button>
        </div>
      </motion.aside>
    </>
  );
}