"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Download, Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import Header from "../dashboard/header";
import { DesktopSidebar, MobileSidebar } from "../dashboard/sidebar";
import { ErrorAlert } from "../ui/error-alert";
import { TableLoadingSkeleton } from "../ui/loading-skeleton";
import { buildSimplePdfBlob, downloadPdfBlob } from "@/lib/pdf-generator";
import { listXsltFiles, loadXsltFile, parseExistingRules } from "@/lib/xslt-manager";
import type { ParsedRule, XsltStorageFile } from "@/lib/types";

function formatTimestamp(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString();
}

export default function XsltFilesClient() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [files, setFiles] = useState<XsltStorageFile[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<{
    file: XsltStorageFile;
    content: string;
    parsedRules: ParsedRule[];
    ruleTexts: string[];
  } | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);

  const filteredFiles = useMemo(() => {
    const lowered = query.trim().toLowerCase();
    if (!lowered) return files;
    return files.filter((file) => {
      return (
        file.name.toLowerCase().includes(lowered) ||
        (file.description ?? "").toLowerCase().includes(lowered) ||
        file.rule_count.toString().includes(lowered)
      );
    });
  }, [files, query]);

  useEffect(() => {
    let mounted = true;

    async function loadFiles() {
      try {
        const nextFiles = await listXsltFiles();
        if (mounted) setFiles(nextFiles);
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : "Unable to load XSLT files");
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    void loadFiles();
    return () => {
      mounted = false;
    };
  }, []);

  const handleView = async (file: XsltStorageFile) => {
    setDrawerLoading(true);
    try {
      const loaded = await loadXsltFile(file.id);
      setSelectedFile({
        file: loaded.file,
        content: loaded.content,
        parsedRules: loaded.metadata?.parsed_rules ?? [],
        ruleTexts: parseExistingRules(loaded.content, loaded.metadata),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load XSLT file");
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!selectedFile) return;

    const blob = buildSimplePdfBlob(`XSLT File: ${selectedFile.file.name}`, [
      {
        title: "Metadata",
        lines: [
          `File Name: ${selectedFile.file.name}`,
          `Description: ${selectedFile.file.description ?? "-"}`,
          `Rule Count: ${selectedFile.file.rule_count}`,
          `Created At: ${formatTimestamp(selectedFile.file.created_at)}`,
          `Updated At: ${formatTimestamp(selectedFile.file.updated_at)}`,
        ],
      },
      {
        title: "Parsed Rules",
        lines:
          selectedFile.parsedRules.length > 0
            ? selectedFile.parsedRules.map((rule, index) => {
                const description = (rule as ParsedRule & { description?: string }).description;
                const suffix = rule.field ? ` (${rule.field})` : "";
                return `${index + 1}. ${rule.rule_type}${suffix}${description ? ` - ${description}` : ""}`;
              })
            : selectedFile.ruleTexts.length > 0
              ? selectedFile.ruleTexts.map((rule, index) => `${index + 1}. ${rule}`)
              : ["No rules parsed yet."],
      },
      {
        title: "XSLT Preview",
        lines: selectedFile.content.split("\n").slice(0, 60),
      },
    ]);

    await downloadPdfBlob(blob, `${selectedFile.file.name}.pdf`);
  };

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8faff_0%,#f4f7ff_42%,#eef3fb_100%)] text-slate-900">
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header
          onOpenSidebar={() => setMobileOpen(true)}
          title="View XSLT Files"
          subtitle="Manage reusable XSLT workspaces and inspect their accumulated rules."
        />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1440px] space-y-6">
            {error && <ErrorAlert error={error} onRetry={() => window.location.reload()} />}

            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">XSLT Files</h3>
                  <p className="text-sm text-slate-500">Select a workspace to review accumulated rules or download a PDF summary.</p>
                </div>
                <div className="relative w-full md:max-w-sm">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search XSLT files..."
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none transition focus:border-indigo-300 focus:bg-white"
                  />
                </div>
              </div>

              {isLoading ? (
                <TableLoadingSkeleton />
              ) : filteredFiles.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-500">
                  No XSLT files found.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs uppercase tracking-[0.18em] text-slate-500">
                        <th className="pb-3">XSLT ID</th>
                        <th className="pb-3">File Name</th>
                        <th className="pb-3">Rule Count</th>
                        <th className="pb-3">Created At</th>
                        <th className="pb-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredFiles.map((file) => (
                        <motion.tr key={file.id} className="border-t border-slate-100 hover:bg-slate-50/70">
                          <td className="py-4 font-mono text-xs font-semibold text-slate-500">{file.id}</td>
                          <td className="py-4 font-medium text-slate-900">{file.name}</td>
                          <td className="py-4 text-slate-700">{file.rule_count}</td>
                          <td className="py-4 text-slate-600">{formatTimestamp(file.created_at)}</td>
                          <td className="py-4">
                            <button
                              type="button"
                              onClick={() => void handleView(file)}
                              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-indigo-300 hover:text-indigo-700"
                            >
                              View
                            </button>
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      <AnimatePresence>
        {selectedFile && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm"
              onClick={() => setSelectedFile(null)}
            />
            <motion.aside
              initial={{ x: 320 }}
              animate={{ x: 0 }}
              exit={{ x: 320 }}
              transition={{ type: "spring", stiffness: 220, damping: 24 }}
              className="fixed right-0 top-0 z-50 flex h-full w-full max-w-[560px] flex-col border-l border-slate-200 bg-white shadow-2xl"
            >
              <div className="flex items-start justify-between border-b border-slate-200 px-6 py-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-600">XSLT Workspace</p>
                  <h3 className="mt-1 text-2xl font-semibold text-slate-950">{selectedFile.file.name}</h3>
                  <p className="mt-1 text-sm text-slate-500">{selectedFile.file.description || "No description provided"}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => void handleDownloadPdf()}
                    className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-3 py-2 text-xs font-semibold text-white transition hover:bg-slate-800"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download PDF
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="rounded-xl border border-slate-200 p-2 text-slate-500 transition hover:text-slate-900"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto px-6 py-5">
                {drawerLoading ? (
                  <p className="text-sm text-slate-500">Loading workspace details...</p>
                ) : (
                  <div className="space-y-6">
                    <section className="grid grid-cols-2 gap-3 text-sm">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Rule Count</div>
                        <div className="mt-1 text-2xl font-semibold text-slate-900">{selectedFile.file.rule_count}</div>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Updated</div>
                        <div className="mt-1 text-sm font-medium text-slate-900">{formatTimestamp(selectedFile.file.updated_at)}</div>
                      </div>
                    </section>

                    <section>
                      <h4 className="mb-2 text-sm font-semibold text-slate-900">Parsed Rules</h4>
                      <div className="space-y-3">
                        {selectedFile.parsedRules.length > 0 ? (
                          selectedFile.parsedRules.map((rule, index) => {
                            const description = (rule as ParsedRule & { description?: string }).description;
                            return (
                              <div key={`${rule.rule_type}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                                <div className="flex items-center justify-between gap-3">
                                  <div className="font-medium text-slate-900">{rule.field || rule.rule_type}</div>
                                  <span className="rounded-full bg-indigo-50 px-2 py-1 text-[11px] font-medium text-indigo-700">{rule.rule_type}</span>
                                </div>
                                <p className="mt-2 text-sm text-slate-600">{description || selectedFile.ruleTexts[index] || "No description"}</p>
                              </div>
                            );
                          })
                        ) : (
                          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                            No parsed rules available yet.
                          </div>
                        )}
                      </div>
                    </section>

                    <section>
                      <h4 className="mb-2 text-sm font-semibold text-slate-900">XSLT Preview</h4>
                      <div className="rounded-2xl border border-slate-200 bg-slate-950 p-4 font-mono text-[11px] leading-5 text-emerald-400">
                        <pre className="max-h-[380px] overflow-auto whitespace-pre-wrap">{selectedFile.content}</pre>
                      </div>
                    </section>
                  </div>
                )}
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
