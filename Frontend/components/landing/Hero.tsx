"use client"
import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { resetDatabase } from "../../lib/api-client";

export default function Hero() {
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
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute -left-40 -top-40 w-72 h-72 rounded-full bg-gradient-to-br from-indigo-200 to-purple-300 opacity-30 blur-3xl" />
        <div className="absolute right-[-120px] bottom-[-80px] w-80 h-80 rounded-full bg-gradient-to-br from-indigo-300 to-purple-400 opacity-20 blur-2xl" />
      </div>

      <div className="max-w-6xl mx-auto px-6 pt-16 pb-12 text-center">
        <motion.p initial={{ y: 8, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.5 }} className="inline-block px-3 py-1 bg-primaryBackground text-sm rounded-full text-textDarkBlue mb-6">
          AI-Powered • Deterministic • Explainable
        </motion.p>

        <motion.h1 initial={{ y: 12, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.05, duration: 0.6 }} className="text-4xl md:text-5xl font-extrabold leading-tight mb-4 text-textDarkBlue">
          Write Invoice Validation Rules
          <br />
          <span className="bg-gradient-to-r from-indigo-500 to-purple-600 bg-clip-text text-transparent">in Plain English</span>
        </motion.h1>

        <motion.p initial={{ y: 16, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.12, duration: 0.6 }} className="text-textDarkBlue/70 mb-8 max-w-3xl mx-auto">
          Convert natural language rules into executable XML validation logic. Validate invoices instantly and ensure tax compliance with confidence.
        </motion.p>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.18 }} className="flex items-center justify-center gap-4">
          <button onClick={handleGetStarted} disabled={loading} className="px-6 py-3 rounded-md bg-gradient-to-br from-indigo-600 to-purple-600 text-white shadow-lg hover:scale-[1.02] transition disabled:opacity-50">
            {loading ? "Starting..." : "Try Rule Engine"}
          </button>
          <button onClick={handleGetStarted} disabled={loading} className="px-5 py-3 rounded-md bg-white border border-border text-textDarkBlue hover:shadow-md transition disabled:opacity-50">
            View Demo
          </button>
        </motion.div>
      </div>
    </section>
  );
}

