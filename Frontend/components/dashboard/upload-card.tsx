"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Play, Upload, X } from "lucide-react";
import { useRef, useState } from "react";
import { useUploadFile, useMutate } from "@/lib/hooks";
import { apiClient } from "@/lib/api-client";
import type { APIError } from "@/lib/api-client";
import { ErrorAlert } from "../ui/error-alert";
import type { UploadInvoiceResponse, InvoiceValidationResponse } from "@/lib/types";

interface UploadCardProps {
  onUploadSuccess?: (invoiceId: number) => void;
  onValidationSuccess?: (result: InvoiceValidationResponse) => void;
}

export default function UploadCard({ onUploadSuccess, onValidationSuccess }: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedInvoice, setUploadedInvoice] = useState<UploadInvoiceResponse | null>(null);
  const [validateError, setValidateError] = useState<APIError | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  // Upload file mutation
  const { mutate: uploadFile, isLoading: isUploading, error: uploadError } = useUploadFile<UploadInvoiceResponse>(
    "/invoices/upload",
    {
      onSuccess: (result) => {
        setUploadedInvoice(result);
        onUploadSuccess?.(result.id);
      },
    }
  );

  const handleFileSelect = (file: File) => {
    // Validate file type
    if (!file.name.toLowerCase().endsWith(".xml")) {
      alert("Please select an XML file");
      return;
    }

    // Validate file size (1MB max)
    if (file.size > 1_000_000) {
      alert("File is too large. Maximum size is 1MB.");
      return;
    }

    setSelectedFile(file);
    setUploadedInvoice(null); // Reset uploaded state if selecting new file
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert("Please select a file");
      return;
    }

    try {
      await uploadFile(selectedFile);
    } catch (err) {
      console.error("Upload failed:", err);
    }
  };

  const handleValidate = async () => {
    if (!uploadedInvoice?.id) {
      alert("Please upload an invoice first");
      return;
    }

    try {
      setIsValidating(true);
      setValidateError(null);
      const result = await apiClient.post<InvoiceValidationResponse>(
        `/invoices/${uploadedInvoice.id}/validate`,
        {}
      );
      onValidationSuccess?.(result);
    } catch (err: unknown) {
      const error = err as APIError;
      setValidateError(error);
      console.error("Validation failed:", error);
    } finally {
      setIsValidating(false);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setUploadedInvoice(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const fileName = selectedFile?.name || uploadedInvoice?.filename || "No file selected";
  const fileSize = selectedFile?.size || uploadedInvoice?.size || 0;
  const fileSizeKB = (fileSize / 1024).toFixed(1);

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm"
    >
      <h3 className="mb-3 font-semibold text-[#07122F]">Upload Invoice XML</h3>

      {(uploadError || validateError) && (
        <div className="mb-3">
          <ErrorAlert error={uploadError || validateError!} />
        </div>
      )}

      {!uploadedInvoice ? (
        <>
          <div
            className="rounded-xl border-2 border-dashed border-slate-300 bg-slate-50/70 p-6 text-center cursor-pointer transition hover:border-indigo-300 hover:bg-indigo-50/30"
            onClick={() => inputRef.current?.click()}
            onDrop={(e) => {
              e.preventDefault();
              const file = e.dataTransfer.files?.[0];
              if (file) handleFileSelect(file);
            }}
            onDragOver={(e) => e.preventDefault()}
          >
            <Upload className="mx-auto h-7 w-7 text-slate-400" />
            <p className="mt-2 text-xs text-slate-500">Drag & drop your XML file here</p>
            <input
              ref={inputRef}
              type="file"
              accept=".xml,text/xml"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileSelect(file);
              }}
              disabled={isUploading}
            />
            <button
              className="mt-3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-indigo-600 hover:bg-white disabled:opacity-50"
              onClick={(e) => {
                e.stopPropagation();
                inputRef.current?.click();
              }}
              disabled={isUploading}
            >
              Choose File
            </button>
          </div>

          {selectedFile && (
            <div className="mt-3 flex items-center justify-between rounded-lg border border-slate-200 p-3 text-sm">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="max-w-[70%] truncate text-slate-700">{fileName}</span>
                <span className="text-xs text-slate-400 flex-shrink-0">{fileSizeKB} KB</span>
              </div>
              <button
                onClick={handleClear}
                disabled={isUploading}
                className="text-slate-400 hover:text-slate-600 disabled:opacity-50"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          {selectedFile && (
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] px-4 py-2.5 text-white shadow-sm transition hover:opacity-95 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Upload className="h-4 w-4" />
              {isUploading ? "Uploading..." : "Upload Invoice"}
            </button>
          )}
        </>
      ) : (
        <>
          <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
              <div className="min-w-0">
                <p className="font-medium text-slate-900 truncate">{uploadedInvoice.filename}</p>
                <p className="text-xs text-slate-500">ID: {uploadedInvoice.id}</p>
              </div>
            </div>
            <button
              onClick={handleClear}
              disabled={isValidating}
              className="text-slate-400 hover:text-slate-600 disabled:opacity-50 flex-shrink-0"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <button
            onClick={handleValidate}
            disabled={isValidating}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] px-4 py-2.5 text-white shadow-sm transition hover:opacity-95 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="h-4 w-4" />
            {isValidating ? "Validating..." : "Validate Invoice"}
          </button>

          <p className="mt-3 inline-flex items-center gap-1 text-xs text-emerald-600">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Ready for validation
          </p>
        </>
      )}
    </motion.section>
  );
}