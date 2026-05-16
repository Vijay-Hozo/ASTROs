"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Play, Upload } from "lucide-react";
import { useRef, useState } from "react";

export default function UploadCard() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState("INV_1001.xml");

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm"
    >
      <h3 className="mb-3 font-semibold text-[#07122F]">Upload Invoice XML</h3>
      <div className="rounded-xl border-2 border-dashed border-slate-300 bg-slate-50/70 p-6 text-center">
        <Upload className="mx-auto h-7 w-7 text-slate-400" />
        <p className="mt-2 text-xs text-slate-500">Drag & drop your XML file here</p>
        <input
          ref={inputRef}
          type="file"
          accept=".xml,text/xml"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              setFileName(file.name);
            }
          }}
        />
        <button
          className="mt-3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-textDarkBlue hover:bg-white"
          onClick={() => inputRef.current?.click()}
        >
          Choose File
        </button>
      </div>

      <div className="mt-3 flex items-center justify-between rounded-lg border border-slate-200 p-3 text-sm">
        <span className="max-w-[70%] truncate text-slate-700">{fileName}</span>
        <span className="text-xs text-slate-400">2.4 KB</span>
      </div>

      <button className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] px-4 py-2.5 text-white shadow-sm transition hover:opacity-95">
        <Play className="h-4 w-4" />
        Validate Invoice
      </button>

      <div className="mt-2 inline-flex items-center gap-1 text-xs text-emerald-600">
        <CheckCircle2 className="h-3.5 w-3.5" />
        File ready for validation
      </div>
    </motion.section>
  );
}