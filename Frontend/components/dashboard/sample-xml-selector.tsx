"use client";

import { motion } from "framer-motion";
import { Check, FileUp, Plus, RefreshCw, Search, Upload, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";

interface SampleXml {
  id: number;
  filename: string;
  created_at: string;
}

interface SampleXmlSelectorProps {
  value: File | null;
  selectedSampleId: number | null;
  onChange: (file: File | null, sampleId: number | null) => void;
}

export default function SampleXmlSelector({ value, selectedSampleId, onChange }: SampleXmlSelectorProps) {
  const [samples, setSamples] = useState<SampleXml[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const inputRef = useRef<HTMLInputElement | null>(null);

  const filteredSamples = useMemo(() => {
    const lowered = query.trim().toLowerCase();
    if (!lowered) return samples;
    return samples.filter((s) => s.filename.toLowerCase().includes(lowered));
  }, [samples, query]);

  const loadSamples = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get("/api/samples");
      setSamples(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load samples");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadSamples();
  }, []);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const nextFile = Array.from(files).find((file) => file.name.toLowerCase().endsWith(".xml"));
    if (nextFile) {
      onChange(nextFile, null);
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
          <h3 className="text-base font-semibold text-slate-900">Select Sample XML</h3>
          <p className="text-sm text-slate-500">Choose an existing sample or upload a new one.</p>
        </div>
        <button
          type="button"
          onClick={loadSamples}
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
          placeholder="Search sample XMLs..."
          className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-3 text-sm text-slate-900 outline-none transition focus:border-indigo-300 focus:bg-white"
        />
      </div>

      {error && <p className="mb-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}

      <div className="space-y-2 max-h-[350px] overflow-y-auto pr-1">
        {value && !selectedSampleId ? (
          <div className="flex w-full items-center justify-between rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-3 text-left shadow-sm transition">
            <div>
              <p className="text-sm font-medium text-slate-900">{value.name}</p>
              <p className="text-xs text-slate-500">New upload · {(value.size / 1024).toFixed(1)} KB</p>
            </div>
            <div className="flex flex-row items-center gap-2">
              <Check className="h-4 w-4 text-emerald-600" />
              <button type="button" onClick={() => onChange(null, null)} className="rounded-lg p-1 text-slate-400 transition hover:bg-white hover:text-rose-600">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-3 text-left transition hover:border-slate-300 hover:bg-slate-50"
          >
            <div>
              <p className="text-sm font-medium text-slate-900">+ Upload New XML</p>
              <p className="text-xs text-slate-500">Select a local .xml file from your computer.</p>
            </div>
            <Upload className="h-4 w-4 text-slate-400" />
          </button>
        )}

        <input
          ref={inputRef}
          type="file"
          accept=".xml"
          className="hidden"
          onChange={(event) => handleFiles(event.target.files)}
        />

        {filteredSamples.map((sample) => (
          <button
            key={sample.id}
            type="button"
            onClick={() => onChange(null, sample.id)}
            className={`flex w-full items-center justify-between rounded-xl border px-3 py-3 text-left transition ${selectedSampleId === sample.id ? "border-emerald-300 bg-emerald-50 shadow-sm" : "border-slate-200 bg-white hover:border-slate-300"}`}
          >
            <div className="truncate pr-2">
              <p className="truncate text-sm font-medium text-slate-900">{sample.filename}</p>
              <p className="text-xs text-slate-500">Uploaded {new Date(sample.created_at).toLocaleDateString()}</p>
            </div>
            {selectedSampleId === sample.id && <Check className="h-4 w-4 shrink-0 text-emerald-600" />}
          </button>
        ))}
      </div>

      {isLoading && <p className="mt-3 text-xs text-slate-500">Loading existing samples...</p>}
    </motion.div>
  );
}
