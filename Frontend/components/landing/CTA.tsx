"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { resetDatabase } from "../../lib/api-client";

export default function CTA() {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleGetStarted = async (e: React.MouseEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await resetDatabase();
      sessionStorage.clear();
      document.cookie.split(";").forEach(c => {
        document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
      router.push("/dashboard");
    } catch (err) {
      console.error("Failed to reset database:", err);
      sessionStorage.clear();
      router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-12 mt-12">
      <div className="max-w-6xl mx-auto px-6 text-center">
        <h3 className="text-2xl font-semibold mb-3">Ready to get started?</h3>
        <p className="mb-6 text-white/90">Try the rule builder and validate an invoice in seconds.</p>
        <div className="flex justify-center">
          <button onClick={handleGetStarted} disabled={loading} className="px-6 py-3 bg-white/10 rounded-md hover:bg-white/20 transition disabled:opacity-50">
            {loading ? "Starting..." : "Try It Now"}
          </button>
        </div>
      </div>
    </section>
  );
}

