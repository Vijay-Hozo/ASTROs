"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, FileCode2, Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import XmlUploader from "./xml-uploader";
import XsltSelector from "./xslt-selector";
import type { XsltSelection } from "@/lib/types";

interface SetupModalProps {
  open: boolean;
  onComplete: (payload: { xmlFile: File | null; xsltSelection: XsltSelection }) => void;
}

const STORAGE_KEY = "astro-dashboard-setup-complete";

export function markSetupComplete() {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, "true");
  }
}

export function hasSetupCompleted() {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(STORAGE_KEY) === "true";
}

export default function SetupModal({ open, onComplete }: SetupModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [xmlFile, setXmlFile] = useState<File | null>(null);
  const [xsltSelection, setXsltSelection] = useState<XsltSelection>({
    mode: "create",
    draft: { name: "invoice-rules", description: "" },
  });

  const canProceed = useMemo(() => Boolean(xmlFile && xsltSelection), [xmlFile, xsltSelection]);

  useEffect(() => {
    if (open) {
      setStep(1);
    }
  }, [open]);

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4 py-6 backdrop-blur-sm"
      >
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 16, scale: 0.98 }}
          className="w-full max-w-4xl overflow-hidden rounded-[28px] border border-white/10 bg-slate-50 shadow-[0_30px_120px_rgba(15,23,42,0.45)]"
        >
          <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-indigo-600">Dashboard setup</p>
              <h2 className="mt-1 text-2xl font-semibold text-slate-950">Prepare your validation workspace</h2>
              <p className="mt-1 text-sm text-slate-500">Upload a sample XML file, then choose the XSLT file that will receive the parsed rules.</p>
            </div>
            <div className="hidden rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 md:block">
              Step {step} of 2
            </div>
          </div>

          <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-6">
              {step === 1 ? (
                <XmlUploader value={xmlFile} onChange={setXmlFile} />
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
                    <FileCode2 className="h-4 w-4 text-indigo-600" />
                    Ready to bind rules to XSLT
                  </div>
                  <p className="text-sm text-slate-500">Choose a destination file for new validation templates, or keep using the selected file for version-safe updates.</p>
                  <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                    <p className="font-medium">XML file</p>
                    <p>{xmlFile?.name ?? "No file selected"}</p>
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-6">
              <XsltSelector value={xsltSelection} onChange={setXsltSelection} />
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-slate-200 bg-white px-6 py-4">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:text-slate-900"
            >
              <Upload className="h-4 w-4" />
              Review upload
            </button>

            {step === 1 ? (
              <button
                type="button"
                disabled={!xmlFile}
                onClick={() => setStep(2)}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Continue
                <ArrowRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button"
                disabled={!canProceed}
                onClick={() => {
                  markSetupComplete();
                  onComplete({ xmlFile, xsltSelection });
                }}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Finish Setup
                <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
