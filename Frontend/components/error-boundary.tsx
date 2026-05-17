"use client";

import { AlertCircle, RotateCcw } from "lucide-react";
import { useState } from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorState {
  hasError: boolean;
  error: Error | null;
}

export default function ErrorBoundary({ children }: ErrorBoundaryProps) {
  const [state, setState] = useState<ErrorState>({
    hasError: false,
    error: null,
  });

  // Handle uncaught errors
  const handleError = (error: Error) => {
    console.error("Error caught by boundary:", error);
    setState({
      hasError: true,
      error,
    });
  };

  const resetError = () => {
    setState({
      hasError: false,
      error: null,
    });
    window.location.reload();
  };

  // Note: In a real app, you'd use React's error boundary pattern
  // This is a simplified version for demonstration
  if (state.hasError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100 p-4">
        <div className="max-w-md w-full">
          <div className="rounded-xl border border-red-200 bg-white p-6 shadow-lg">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <div className="flex-1">
                <h1 className="text-lg font-semibold text-slate-900">
                  Something went wrong
                </h1>
                <p className="mt-2 text-sm text-slate-600">
                  {state.error?.message || "An unexpected error occurred. Please try again."}
                </p>
                <button
                  onClick={resetError}
                  className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition"
                >
                  <RotateCcw className="h-4 w-4" />
                  Reload Page
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
