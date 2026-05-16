"use client";

import React from "react";
import { motion } from "framer-motion";
import { Rule } from "./sample-data";

export default function RuleDetailDrawer({ rule, onClose }: { rule?: Rule | null; onClose?: () => void }) {
  if (!rule) return null;

  return (
    <motion.aside initial={{ x: 300 }} animate={{ x: 0 }} exit={{ x: 300 }} className="fixed right-0 top-0 z-50 h-full w-[480px] bg-white p-6 shadow-xl">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold">{rule.name}</h3>
          <p className="text-sm text-slate-500">{rule.id} • {rule.type}</p>
        </div>
        <button onClick={onClose} className="text-slate-500">Close</button>
      </div>

      <div className="mt-4 space-y-4">
        <div>
          <h4 className="text-sm font-medium">Description</h4>
          <p className="mt-1 text-sm text-slate-600">{rule.text}</p>
        </div>

        <div>
          <h4 className="text-sm font-medium">Structured JSON</h4>
          <pre className="mt-2 max-h-40 overflow-auto rounded-md bg-slate-50 p-3 text-xs">{JSON.stringify(rule, null, 2)}</pre>
        </div>

        <div>
          <h4 className="text-sm font-medium">Metadata</h4>
          <div className="mt-2 text-sm text-slate-600">
            <div>Created by: {rule.createdBy}</div>
            <div>Last modified: {rule.updatedAt}</div>
            <div>Status: {rule.status}</div>
          </div>
        </div>
      </div>
    </motion.aside>
  );
}
