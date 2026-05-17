"use client";

import { motion } from "framer-motion";
import { FileUp, Upload, X } from "lucide-react";
import { useRef, useState } from "react";

interface XmlUploaderProps {
  value?: File | null;
  onChange: (file: File | null) => void;
}

export default function XmlUploader({ value, onChange }: XmlUploaderProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const nextFile = Array.from(files).find((file) => file.name.toLowerCase().endsWith(".xml"));
    onChange(nextFile ?? null);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Upload Sample XML</h3>
          <p className="text-sm text-slate-500">Accepts .xml files only.</p>
        </div>
        <FileUp className="h-5 w-5 text-slate-400" />
      </div>

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          handleFiles(event.dataTransfer.files);
        }}
        className={`flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 text-center transition ${isDragging ? "border-indigo-400 bg-indigo-50" : "border-slate-200 bg-slate-50/80 hover:border-slate-300"}`}
      >
        <Upload className="mb-2 h-8 w-8 text-slate-400" />
        <p className="text-sm font-medium text-slate-700">Drag and drop your sample XML here</p>
        <p className="mt-1 text-xs text-slate-500">or click to browse</p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".xml"
        className="hidden"
        onChange={(event) => handleFiles(event.target.files)}
      />

      {value && (
        <div className="mt-3 flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          <div>
            <p className="font-medium">{value.name}</p>
            <p className="text-xs text-slate-500">{(value.size / 1024).toFixed(1)} KB</p>
          </div>
          <button type="button" onClick={() => onChange(null)} className="rounded-lg p-1.5 text-slate-400 transition hover:bg-white hover:text-rose-600">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </motion.div>
  );
}
