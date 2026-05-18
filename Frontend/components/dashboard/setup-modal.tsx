"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import SampleXmlSelector from "./sample-xml-selector";
import XsltSelector from "./xslt-selector";
import type { XsltSelection } from "@/lib/types";
import { apiClient } from "@/lib/api-client";

interface SetupModalProps {
  open: boolean;
  onComplete: (payload: { xmlFile: File | null; xsltSelection: XsltSelection; sampleId: number | null }) => void;
  onClose?: () => void;
  initialSampleId?: number | null;
  initialXsltSelection?: XsltSelection | null;
  skipMarkSetupComplete?: boolean;
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

export default function SetupModal({
  open,
  onComplete,
  onClose,
  initialSampleId = null,
  initialXsltSelection = null,
  skipMarkSetupComplete = false,
}: SetupModalProps) {
  const [xmlFile, setXmlFile] = useState<File | null>(null);
  const [sampleId, setSampleId] = useState<number | null>(initialSampleId);
  const [xsltSelection, setXsltSelection] = useState<XsltSelection>(
    initialXsltSelection || {
      mode: "create",
      draft: { name: "invoice-rules", description: "" },
    }
  );
  const [step, setStep] = useState<1 | 2>(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canGoToStep2 = useMemo(() => Boolean(xmlFile || sampleId), [xmlFile, sampleId]);
  const canProceed = useMemo(() => Boolean((xmlFile || sampleId) && xsltSelection && (xsltSelection.file?.id || xsltSelection.draft?.name)), [xmlFile, sampleId, xsltSelection]);

  useEffect(() => {
    if (open) {
      setStep(1);
      setSampleId(initialSampleId);
      setXmlFile(null);
      setXsltSelection(
        initialXsltSelection || {
          mode: "create",
          draft: { name: "invoice-rules", description: "" },
        }
      );
      setError(null);
    }
  }, [open, initialSampleId, initialXsltSelection]);

  // Handle ESC key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onClose?.();
      }
    };

    if (open) {
      document.addEventListener("keydown", handleEsc);
      return () => document.removeEventListener("keydown", handleEsc);
    }
  }, [open, onClose]);

  const handleFinish = async () => {
    setIsProcessing(true);
    setError(null);

    try {
      let finalSampleId = sampleId;

      // 1. If we have a new xmlFile, upload it first
      if (xmlFile) {
        const formData = new FormData();
        formData.append("file", xmlFile);

        const uploadRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://astros.onrender.com'}/api/sample-upload`, {
          method: "POST",
          body: formData,
        });

        if (!uploadRes.ok) {
          throw new Error("Failed to upload sample XML");
        }

        const data = await uploadRes.json();
        finalSampleId = data.sample_id;
      }

      if (!finalSampleId) {
        throw new Error("Sample ID missing");
      }

      // 2. If the user creates a new XSLT, that's already handled by XsltSelector and returns a file.id
      // but if the mode is 'create' and it hasn't been created yet, they must click 'Create' in the selector first.
      // So the XsltSelector ensures xsltSelection.file.id is set before they can proceed.
      if (!xsltSelection.file?.id) {
        throw new Error("Please select or create an XSLT file first");
      }

      if (!skipMarkSetupComplete) {
        markSetupComplete();
      }
      onComplete({ xmlFile, xsltSelection, sampleId: finalSampleId });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup failed");
    } finally {
      setIsProcessing(false);
    }
  };

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
          className="w-full max-w-5xl overflow-hidden rounded-[28px] border border-white/10 bg-slate-50 shadow-[0_30px_120px_rgba(15,23,42,0.45)]"
        >
          <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-indigo-600">Workspace setup — Step {step} of 2</p>
              <h2 className="mt-1 text-2xl font-semibold text-slate-950">
                {step === 1 ? "Choose Sample XML" : "Choose XSLT Document"}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {step === 1
                  ? "Select or upload an XML invoice file to derive structural schema tags."
                  : "Associate an existing XSLT stylesheet or create a new rules package."
                }
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
              aria-label="Close modal"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="px-6 py-6 min-h-[380px] bg-slate-50">
            {error && (
              <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                <p className="font-medium">Error</p>
                <p>{error}</p>
              </div>
            )}
            
            {step === 1 ? (
              <div className="space-y-4 max-w-2xl mx-auto bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <SampleXmlSelector
                  value={xmlFile}
                  selectedSampleId={sampleId}
                  onChange={(file, sId) => {
                    setXmlFile(file);
                    setSampleId(sId);
                  }}
                />
              </div>
            ) : (
              <div className="space-y-4 max-w-2xl mx-auto bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <XsltSelector value={xsltSelection} onChange={setXsltSelection} />
              </div>
            )}
          </div>

          <div className="flex items-center justify-between border-t border-slate-200 bg-white px-6 py-4">
            {step === 2 ? (
              <button
                type="button"
                onClick={() => setStep(1)}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                Back
              </button>
            ) : (
              <div />
            )}
            
            <div>
              {step === 1 ? (
                <button
                  type="button"
                  disabled={!canGoToStep2}
                  onClick={() => setStep(2)}
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next: Select XSLT
                  <ArrowRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  type="button"
                  disabled={!canProceed || isProcessing}
                  onClick={handleFinish}
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isProcessing ? "Saving Workspace..." : "Save & Continue"}
                  {!isProcessing && <ArrowRight className="h-4 w-4" />}
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
