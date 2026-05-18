/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  X,
  FileCode2,
  FileText,
  Download,
  CheckCircle2,
  AlertCircle,
  Hash,
} from "lucide-react";
import { loadXsltFile, parseExistingRules } from "@/lib/xslt-manager";
import { apiClient } from "@/lib/api-client";
import type { XsltStorageFile } from "@/lib/types";

interface XsltFileViewModalProps {
  file: XsltStorageFile & { sample_filename?: string | null };
  onClose: () => void;
}

export default function XsltFileViewModal({ file, onClose }: XsltFileViewModalProps) {
  const [rules, setRules] = useState<any[]>([]);
  const [xsltPreviews, setXsltPreviews] = useState<string[]>([]);
  const [xsltContent, setXsltContent] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  // Close on ESC
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = "unset";
    };
  }, [onClose]);

  // Load XSLT content & extract rules
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    Promise.all([
      loadXsltFile(file.id).catch(() => ({ content: "", metadata: null })),
      apiClient.get(`/api/xslt-files/${encodeURIComponent(file.id)}/details`)
        .then((details) => details || null)
        .catch(() => null),
    ])
      .then(([loaded, details]) => {
        if (cancelled) return;
        setXsltContent(loaded.content || "");
        if (details && details.rules) {
          setRules(details.rules);
          setXsltPreviews(details.xslt_previews || []);
        } else {
          const extracted = parseExistingRules(loaded.content || "", loaded.metadata as any);
          setRules(extracted.map((r) => ({ rule_name: r })));
          setXsltPreviews([]);
        }
      })
      .catch((err: any) => {
        if (cancelled) return;
        setError(err?.message || "Failed to load XSLT file details");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [file.id]);

  const handleDownloadPdf = async () => {
    setIsDownloading(true);
    setError(null);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001'}/api/xslt-files/${encodeURIComponent(file.id)}/pdf`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: file.name,
            rules: rules,
            xslt_content: xsltContent,
            xslt_previews: xsltPreviews,
          }),
        }
      );
      if (!response.ok) {
        throw new Error("Failed to generate PDF preview");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${file.name.replace(/\s+/g, "-")}-rules-preview.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err?.message || "Download failed");
    } finally {
      setIsDownloading(false);
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
        className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm cursor-pointer"
      />

      {/* Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.97, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.97, y: 12 }}
        transition={{ type: "spring", stiffness: 300, damping: 28 }}
        className="fixed inset-0 z-50 flex items-center justify-center px-4 pointer-events-none"
      >
        <div
          className="w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl pointer-events-auto flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start justify-between border-b border-slate-100 bg-white px-6 py-5 flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50">
                <FileCode2 className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-900">{file.name}</h2>
                <p className="text-xs text-slate-500 mt-0.5">XSLT Validation File Details</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
            {/* File info card */}
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileCode2 className="h-5 w-5 text-indigo-500 flex-shrink-0" />
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">XSLT Filename</span>
                  <p className="text-sm font-semibold text-slate-800 break-all">{file.name}</p>
                </div>
              </div>
              <span className="rounded-full bg-white border border-slate-200 px-3 py-1 text-xs font-bold text-slate-600 shadow-sm">
                Rule Sheet
              </span>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {/* Rules list */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Hash className="h-4 w-4 text-indigo-500" />
                  <span className="text-sm font-bold text-slate-800">
                    Rules ({isLoading ? "…" : rules.length})
                  </span>
                </div>
                {!isLoading && rules.length > 0 && (
                  <span className="rounded-full bg-indigo-50 border border-indigo-100 px-2.5 py-0.5 text-xs font-bold text-indigo-700">
                    {rules.length} rule{rules.length !== 1 ? "s" : ""}
                  </span>
                )}
              </div>

              {isLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 rounded-xl bg-slate-100 animate-pulse" />
                  ))}
                </div>
              ) : rules.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-200 py-8 text-center bg-slate-50/50">
                  <p className="text-sm text-slate-400">No rules found in this XSLT rule sheet</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                  {rules.map((ruleObj, idx) => {
                    const ruleText = typeof ruleObj === "string" ? ruleObj : ruleObj.rule_name;
                    return (
                      <div
                        key={idx}
                        className="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50/60 px-4 py-3 hover:bg-white hover:border-indigo-100 hover:shadow-sm transition"
                      >
                        <span className="flex-shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-bold text-indigo-700 mt-0.5">
                          {idx + 1}
                        </span>
                        <div className="flex items-start gap-2 flex-1 min-w-0 pt-0.5">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                          <span className="text-sm text-slate-700 leading-snug break-words">{ruleText}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Generated XSLT Preview */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <FileCode2 className="h-4 w-4 text-indigo-500" />
                  <span className="text-sm font-bold text-slate-800">Generated XSLT Preview</span>
                </div>
                <span className="text-[11px] font-medium text-slate-400">Internal scroll only</span>
              </div>
              {isLoading ? (
                <div className="h-36 rounded-xl bg-slate-100 animate-pulse" />
              ) : (!xsltPreviews || xsltPreviews.length === 0) && !xsltContent ? (
                <div className="rounded-xl border border-dashed border-slate-200 py-8 text-center bg-slate-50/50 text-xs text-slate-400">
                  No XSLT preview logic available
                </div>
              ) : (
                <div className="max-h-[200px] overflow-y-auto overflow-x-auto rounded-xl bg-slate-900 p-4 border border-slate-800 shadow-inner">
                  <pre className="text-xs font-mono text-slate-200 leading-relaxed whitespace-pre font-normal">
                    {xsltPreviews && xsltPreviews.length > 0 ? xsltPreviews.join("\n\n") : xsltContent}
                  </pre>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/50 px-6 py-4 flex-shrink-0">
            <p className="text-xs text-slate-400">
              Created {new Date(file.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}
            </p>
            <button
              onClick={handleDownloadPdf}
              disabled={isDownloading || isLoading}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition shadow-sm hover:shadow"
            >
              <Download className="h-4 w-4" />
              {isDownloading ? "Generating PDF…" : "Download as PDF"}
            </button>
          </div>
        </div>
      </motion.div>
    </>
  );
}
