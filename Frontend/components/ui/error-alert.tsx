/**
 * ErrorAlert and EmptyState components
 */

"use client";

import { AlertCircle, RefreshCw } from "lucide-react";
import type { APIError } from "@/lib/api-client";

export interface ErrorAlertProps {
  error: APIError | string;
  onRetry?: () => void;
  showDetails?: boolean;
}

export function ErrorAlert({ error, onRetry, showDetails = false }: ErrorAlertProps) {
  const message = typeof error === "string" ? error : error.message;
  const status = typeof error === "string" ? undefined : error.status;
  const code = typeof error === "string" ? undefined : error.code;

  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-red-900">Error</h3>
          <p className="text-sm text-red-700 mt-1">{message}</p>
          {showDetails && (code || status) && (
            <p className="text-xs text-red-600 mt-2">
              {code && `Code: ${code}`}
              {code && status && " | "}
              {status && `Status: ${status}`}
            </p>
          )}
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-2 rounded-md bg-red-100 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-200 transition"
            >
              <RefreshCw className="h-4 w-4" />
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({
  title = "No data",
  description = "There's nothing here yet.",
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-12 text-center">
      {icon && <div className="flex justify-center mb-4">{icon}</div>}
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      <p className="text-sm text-slate-500 mt-1">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

export function TimeoutError({ onRetry }: { onRetry?: () => void }) {
  return (
    <ErrorAlert
      error={{
        code: "REQUEST_TIMEOUT",
        message: "Request timeout. The operation took longer than expected. Please try again.",
        status: 504,
      }}
      onRetry={onRetry}
    />
  );
}

export function APIUnavailableError({ onRetry }: { onRetry?: () => void }) {
  return (
    <ErrorAlert
      error={{
        code: "API_UNAVAILABLE",
        message: "The API server is not responding. Check your connection or try again later.",
        status: 0,
      }}
      onRetry={onRetry}
    />
  );
}

export function XMLValidationError({ 
  message = "The XML file is malformed or invalid.",
  onRetry 
}: { 
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <ErrorAlert
      error={{
        code: "INVALID_XML",
        message,
        status: 400,
      }}
      onRetry={onRetry}
    />
  );
}
