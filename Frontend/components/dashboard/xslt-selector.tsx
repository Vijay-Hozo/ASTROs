"use client";

import { motion } from "framer-motion";
import { Check, Plus, RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createXsltFile, listXsltFiles } from "@/lib/xslt-manager";
import type { XsltFileDraft, XsltSelection, XsltStorageFile } from "@/lib/types";

interface XsltSelectorProps {
  value: XsltSelection;
  onChange: (selection: XsltSelection) => void;
}

export default function XsltSelector({ value, onChange }: XsltSelectorProps) {
  const [files, setFiles] = useState<XsltStorageFile[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredFiles = useMemo(() => {
    const lowered = query.trim().toLowerCase();
    if (!lowered) return files;
    return files.filter((file) => file.name.toLowerCase().includes(lowered) || (file.description ?? "").toLowerCase().includes(lowered));
  }, [files, query]);

  useEffect(() => {
    let mounted = true;

    async function loadFiles() {
      try {
        const nextFiles = await listXsltFiles();
        if (mounted) setFiles(nextFiles);
      } catch (loadError) {
        if (mounted) setError(loadError instanceof Error ? loadError.message : "Unable to load XSLT files");
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    void loadFiles();
    return () => {
      mounted = false;
    };
  }, []);

  const handleCreateNew = async (draft: XsltFileDraft) => {
    setIsCreating(true);
    setError(null);

    try {
      const created = await createXsltFile(draft);
      setFiles((current) => [created, ...current]);
      onChange({ mode: "create", draft, file: created });
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Failed to create XSLT file");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Select XSLT File</h3>
          <p className="text-sm text-slate-500">Choose an existing file or create a new versioned XSLT document.</p>
        </div>
        <button
          type="button"
          onClick={() => {
            setIsLoading(true);
            listXsltFiles()
              .then(setFiles)
              .catch((refreshError) => setError(refreshError instanceof Error ? refreshError.message : "Refresh failed"))
              .finally(() => setIsLoading(false));
          }}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:text-slate-900"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>

      <div className="relative mb-3">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search XSLT files..."
          className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none transition focus:border-indigo-300 focus:bg-white"
        />
      </div>

      {error && <p className="mb-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}

      <div className="space-y-2">
        <button
          type="button"
          onClick={() => onChange({ mode: "create", draft: { name: "invoice-rules", description: "", content: "" } })}
          className={`flex w-full items-center justify-between rounded-xl border px-3 py-3 text-left transition ${value.mode === "create" ? "border-indigo-300 bg-indigo-50" : "border-slate-200 bg-white hover:border-slate-300"}`}
        >
          <div>
            <p className="text-sm font-medium text-slate-900">+ Create New XSLT File</p>
            <p className="text-xs text-slate-500">Create a clean file and attach future rules to it.</p>
          </div>
          {value.mode === "create" && <Check className="h-4 w-4 text-indigo-600" />}
        </button>

        {filteredFiles.map((file) => (
          <button
            key={file.id}
            type="button"
            onClick={() => onChange({ mode: "existing", file })}
            className={`flex w-full items-center justify-between rounded-xl border px-3 py-3 text-left transition ${value.file?.id === file.id ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white hover:border-slate-300"}`}
          >
            <div>
              <p className="text-sm font-medium text-slate-900">{file.name}</p>
              <p className="text-xs text-slate-500">{file.rule_count} rule{file.rule_count === 1 ? "" : "s"} · updated {new Date(file.updated_at).toLocaleDateString()}</p>
            </div>
            {value.file?.id === file.id && <Check className="h-4 w-4 text-emerald-600" />}
          </button>
        ))}
      </div>

      {value.mode === "create" && (
        <CreateXsltForm
          onCreate={handleCreateNew}
          isCreating={isCreating}
          initialName={value.draft?.name ?? "invoice-rules"}
          initialDescription={value.draft?.description ?? ""}
        />
      )}

      {isLoading && <p className="mt-3 text-xs text-slate-500">Loading existing files...</p>}
    </motion.div>
  );
}

function CreateXsltForm({
  onCreate,
  isCreating,
  initialName,
  initialDescription,
}: {
  onCreate: (draft: XsltFileDraft) => void;
  isCreating: boolean;
  initialName: string;
  initialDescription: string;
}) {
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);

  useEffect(() => {
    setName(initialName);
  }, [initialName]);

  useEffect(() => {
    setDescription(initialDescription);
  }, [initialDescription]);

  return (
    <div className="mt-4 rounded-2xl border border-dashed border-indigo-200 bg-indigo-50/40 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-indigo-900">
        <Plus className="h-4 w-4" />
        Create New XSLT File
      </div>
      <div className="space-y-3">
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="XSLT file name"
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
        />
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Optional description"
          className="min-h-20 w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-300"
        />
        <button
          type="button"
          disabled={!name.trim() || isCreating}
          onClick={() =>
            onCreate({
              name: name.trim(),
              description: description.trim(),
            })
          }
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isCreating ? "Creating..." : "Create XSLT File"}
        </button>
      </div>
    </div>
  );
}
