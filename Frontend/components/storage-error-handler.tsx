"use client";

import { useEffect } from "react";

/**
 * Global handler for Supabase storage errors
 * Prevents unhandled promise rejections from crashing the app
 */
export function StorageErrorHandler() {
  useEffect(() => {
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      // Check if it's a storage error
      if (
        event.reason?.name === "StorageApiError" ||
        event.reason?.message?.includes("Object not found") ||
        event.reason?.message?.includes("404") ||
        event.reason?.message?.includes("400")
      ) {
        console.warn(
          "Handled unhandled storage error:",
          event.reason?.message || event.reason
        );
        // Prevent the error from crashing the app
        event.preventDefault();
      }
    };

    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      window.removeEventListener("unhandledrejection", handleUnhandledRejection);
    };
  }, []);

  return null;
}
