"use client";

import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

interface HealthStatus {
  status: "idle" | "checking" | "healthy" | "unhealthy";
  message?: string;
}

export default function HealthCheck() {
  const [health, setHealth] = useState<HealthStatus>({ status: "idle" });

  useEffect(() => {
    const checkHealth = async () => {
      setHealth({ status: "checking" });

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

      try {
        const response = await fetch(`${apiUrl}/health`, {
          method: "GET",
          signal: AbortSignal.timeout(5000),
        });

        if (response.ok) {
          setHealth({ status: "healthy" });
        } else {
          setHealth({
            status: "unhealthy",
            message: `Server returned status ${response.status}`,
          });
        }
      } catch (error) {
        const errorMsg =
          error instanceof DOMException && error.name === "TimeoutError"
            ? "Request timed out. Server may be slow."
            : "Cannot connect to backend. Make sure it's running at " + apiUrl;

        setHealth({
          status: "unhealthy",
          message: errorMsg,
        });
      }
    };

    // Check health on mount and every 30 seconds
    checkHealth();
    const interval = setInterval(checkHealth, 30000);

    return () => clearInterval(interval);
  }, []);

  // Only show if unhealthy
  if (health.status !== "unhealthy") {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 max-w-sm z-50">
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-amber-900">Backend Connection Issue</h3>
            <p className="mt-1 text-sm text-amber-800">{health.message}</p>
            <p className="mt-2 text-xs text-amber-700">
              💡 Tip: Run the backend with:
              <br />
              <code className="font-mono bg-amber-100 px-2 py-1 rounded">
                cd backend && uvicorn main:app --reload
              </code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
