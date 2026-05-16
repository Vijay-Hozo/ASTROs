"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Upload, Play } from "lucide-react";
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
      <h3 className="font-semibold text-[#07122F] mb-3">Upload Invoice XML</h3>
      <div className="rounded-xl border-2 border-dashed border-slate-300 bg-slate-50/70 p-6 text-center">
        <Upload className="h-7 w-7 mx-auto text-slate-400" />
        <p className="text-xs text-slate-500 mt-2">Drag & drop your XML file here</p>
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
          className="mt-3 text-sm rounded-lg border border-slate-300 px-3 py-1.5 hover:bg-white text-textDarkBlue"
          onClick={() => inputRef.current?.click()}
        >
          Choose File
        </button>
      </div>

      <div className="mt-3 rounded-lg border border-slate-200 p-3 flex items-center justify-between text-sm">
        <span className="text-slate-700 truncate max-w-[70%]">{fileName}</span>
        <span className="text-xs text-slate-400">2.4 KB</span>
      </div>

      <button className="mt-3 w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-white bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] shadow-sm hover:opacity-95 transition">
        <Play className="h-4 w-4" />
        Validate Invoice
      </button>

      <div className="mt-2 text-xs text-emerald-600 inline-flex items-center gap-1">
        <CheckCircle2 className="h-3.5 w-3.5" />
        File ready for validation
      </div>
    </motion.section>
  );
}
