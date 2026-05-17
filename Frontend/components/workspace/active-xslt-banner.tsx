"use client";

import { AlertTriangle, Database, FileCode2, RefreshCw } from "lucide-react";
import { useXsltWorkspace } from "@/lib/xslt-workspace-context";

type ActiveXsltBannerProps = {
  onRechoose?: () => void;
  compact?: boolean;
};

export default function ActiveXsltBanner({ onRechoose, compact = false }: ActiveXsltBannerProps) {
  const { activeXSLTFile, activeXSLTFileId, activeRuleCount, isHydrating } = useXsltWorkspace();

  if (compact) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
              <FileCode2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Currently Active XSLT</p>
              <p className="text-sm font-semibold text-slate-900">
                {isHydrating ? "Loading workspace..." : activeXSLTFile?.name ?? "No XSLT file selected"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-50 px-2.5 py-1 font-medium text-slate-700">
              <Database className="h-3.5 w-3.5" />
              {activeRuleCount} rules
            </span>
            {onRechoose && (
              <button
                type="button"
                onClick={onRechoose}
                className="inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 font-semibold text-indigo-700 transition hover:border-indigo-300 hover:bg-indigo-100"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Rechoose
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
            <FileCode2 className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Currently Active XSLT</p>
            <p className="mt-1 text-sm font-semibold text-slate-900">
              {isHydrating ? "Loading workspace..." : activeXSLTFile?.name ?? "No XSLT file selected"}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {activeXSLTFileId ? `Workspace ID: ${activeXSLTFileId}` : "Choose or create a workspace to scope validation."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700">
            <Database className="h-3.5 w-3.5" />
            {activeRuleCount} active rules
          </span>
          {onRechoose && (
            <button
              type="button"
              onClick={onRechoose}
              className="inline-flex items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-700 transition hover:border-indigo-300 hover:bg-indigo-100"
            >
              <RefreshCw className="h-4 w-4" />
              Rechoose / Reupload
            </button>
          )}
        </div>
      </div>
      {!activeXSLTFile && !isHydrating && (
        <div className="mt-3 inline-flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
          <AlertTriangle className="h-4 w-4" />
          No active XSLT workspace selected.
        </div>
      )}
    </div>
  );
}