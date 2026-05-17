"use client";

import React from "react";
import { motion } from "framer-motion";
import type { Rule } from "@/lib/types";

export default function RuleDetailDrawer({ rule, onClose }: { rule?: Rule | null; onClose?: () => void }) {
  React.useEffect(() => {
    if (!rule) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [rule, onClose]);

  if (!rule) return null;

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm cursor-pointer"
      />
      <motion.aside
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 25, stiffness: 220 }}
        className="fixed right-0 top-0 z-50 h-full w-[480px] bg-white p-6 shadow-2xl border-l border-slate-100 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold">Rule #{rule.id}</h3>
          <p className="text-sm text-slate-500">{rule.severity.toUpperCase()} severity</p>
        </div>
        <button onClick={onClose} className="text-slate-500">Close</button>
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <h4 className="text-sm font-medium">Rule Text</h4>
          <p className="mt-1 text-sm text-slate-600">{rule.rule_text}</p>
        </div>

        <div>
          <h4 className="text-sm font-medium">Parsed JSON</h4>
          <pre className="mt-2 max-h-40 overflow-auto rounded-md bg-slate-50 p-3 text-xs">{JSON.stringify(rule.parsed_json, null, 2)}</pre>
        </div>

        <div>
          <h4 className="text-sm font-medium">Metadata</h4>
          <div className="mt-2 text-sm text-slate-600">
            <div>Created: {new Date(rule.created_at).toLocaleDateString()}</div>
            <div>Severity: {rule.severity}</div>
          </div>
        </div>
      </div>
      </motion.aside>
    </>
  );
}
