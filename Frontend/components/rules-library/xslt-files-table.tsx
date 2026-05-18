/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, Trash2, FileCode2, RefreshCw, AlertTriangle } from "lucide-react";
import { listXsltFiles, deleteXsltFile } from "@/lib/xslt-manager";
import type { XsltStorageFile } from "@/lib/types";
import { TableLoadingSkeleton } from "../ui/loading-skeleton";
import XsltFileViewModal from "./xslt-file-view-modal";

interface XsltFileRow extends XsltStorageFile {
  sample_filename?: string | null;
}

function ConfirmDeleteDialog({
  filename,
  onConfirm,
  onCancel,
  isDeleting,
}: {
  filename: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm px-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50">
            <AlertTriangle className="h-5 w-5 text-rose-600" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Delete XSLT File</h3>
            <p className="text-xs text-slate-500 mt-0.5">This action cannot be undone</p>
          </div>
        </div>
        <p className="text-sm text-slate-700 mb-5">
          Are you sure you want to permanently delete{" "}
          <span className="font-semibold text-slate-900">{filename}</span> and all its linked data?
        </p>
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700 transition disabled:opacity-50"
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export default function XsltFilesTable({ refreshTrigger }: { refreshTrigger?: number }) {
  const [files, setFiles] = useState<XsltFileRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<XsltFileRow | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [viewTarget, setViewTarget] = useState<XsltFileRow | null>(null);

  const loadFiles = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const storageFiles = await listXsltFiles();
      setFiles(storageFiles as XsltFileRow[]);
    } catch (err: any) {
      setError(err?.message || "Failed to load XSLT files");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles, refreshTrigger]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    
    // Confirm deletion before proceeding
    const confirmed = window.confirm(
      `Are you sure you want to delete the rule and its XSLT file "${deleteTarget.name}"? This action cannot be undone.`
    );
    if (!confirmed) return;
    
    setIsDeleting(true);
    try {
      await deleteXsltFile(deleteTarget.id);
      setFiles((prev) => prev.filter((f) => f.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err?.message || "Failed to delete XSLT file");
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) return <TableLoadingSkeleton />;

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        <p className="font-semibold mb-1">Error loading XSLT files</p>
        <p>{error}</p>
        <button
          onClick={loadFiles}
          className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 transition"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Retry
        </button>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-white py-16 text-center shadow-sm">
        <FileCode2 className="h-10 w-10 text-slate-300 mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-500">No XSLT files yet</p>
        <p className="text-xs text-slate-400 mt-1">
          Create an XSLT file from the dashboard setup to get started.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="rounded-2xl bg-white shadow-sm overflow-hidden border border-slate-100">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">XSLT Files</h3>
            <p className="text-xs text-slate-500 mt-0.5">{files.length} file{files.length !== 1 ? "s" : ""} in library</p>
          </div>
          <button
            onClick={loadFiles}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 bg-slate-50/50">
                <th className="px-5 py-3">File ID</th>
                <th className="px-5 py-3">Filename</th>
                <th className="px-5 py-3">Rules Count</th>
                <th className="px-5 py-3">Created Date</th>
                <th className="px-5 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {files.map((file, idx) => (
                <motion.tr
                  key={file.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className="hover:bg-slate-50/60 transition"
                >
                  <td className="px-5 py-3.5">
                    <span className="font-mono text-[10px] text-slate-400 bg-slate-100 rounded px-1.5 py-0.5">
                      {file.id.slice(0, 8)}…
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-50">
                        <FileCode2 className="h-3.5 w-3.5 text-indigo-600" />
                      </div>
                      <span className="font-semibold text-slate-800 text-xs">{file.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="inline-flex items-center rounded-full bg-indigo-50 border border-indigo-100 px-2.5 py-0.5 text-xs font-bold text-indigo-700">
                      {file.rule_count ?? 0}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-xs text-slate-500">
                    {new Date(file.created_at).toLocaleDateString("en-GB", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setViewTarget(file)}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:border-indigo-200 hover:text-indigo-700 transition"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        View
                      </button>
                      <button
                        onClick={() => setDeleteTarget(file)}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50 hover:border-rose-200 transition"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <AnimatePresence>
        {deleteTarget && (
          <ConfirmDeleteDialog
            filename={deleteTarget.name}
            onConfirm={handleDelete}
            onCancel={() => setDeleteTarget(null)}
            isDeleting={isDeleting}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {viewTarget && (
          <XsltFileViewModal
            file={viewTarget}
            onClose={() => setViewTarget(null)}
          />
        )}
      </AnimatePresence>
    </>
  );
}
