"use client";

import { motion } from "framer-motion";
import { Copy, FileCode2, Edit2 } from "lucide-react";
import { useEffect, useState } from "react";
import type { ParseRuleResponse } from "@/lib/types";

type TabKey = "XPath" | "XSLT" | "Python";

interface ValidationLogicCardProps {
  result?: ParseRuleResponse | null;
  isLoading?: boolean;
  onLogicChange?: (logic: { xpath?: string; xslt?: string; python_logic?: string }) => void;
}

export default function ValidationLogicCard({ result, isLoading, onLogicChange }: ValidationLogicCardProps) {
  const [tab, setTab] = useState<TabKey>("XSLT");
  const [editMode, setEditMode] = useState(false);
  const [editedContent, setEditedContent] = useState("");
  const [overrides, setOverrides] = useState<Partial<Record<TabKey, string>>>({});

  const snippets: Record<TabKey, string> = {
    XPath: overrides.XPath || result?.xpath || "//rule_field",
    XSLT: overrides.XSLT || result?.xslt || "<xsl:template />",
    Python: overrides.Python || result?.python_logic || "# validation logic",
  };

  useEffect(() => {
    setOverrides({});
  }, [result?.rule_text]);

  const handleEditTab = (key: TabKey) => {
    setEditMode(true);
    setEditedContent(snippets[key]);
  };

  const handleSaveEdit = () => {
    const updated = { ...snippets, [tab]: editedContent };
    setOverrides((prev) => ({ ...prev, [tab]: editedContent }));
    onLogicChange?.({
      xpath: updated.XPath,
      xslt: updated.XSLT,
      python_logic: updated.Python,
    });
    setEditMode(false);
  };

  async function copySnippet() {
    await navigator.clipboard.writeText(snippets[tab]);
  }

  if (!result && !isLoading) {
    return (
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ y: -2 }}
        transition={{ duration: 0.3 }}
        className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)]"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-[#f2efff] p-2 text-[#4c2ff1]">
              <FileCode2 className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-slate-900">Generated Validation Logic</h2>
              <p className="text-sm text-slate-500">Parse a rule to see generated logic.</p>
            </div>
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 text-center">
          <p className="text-sm text-slate-500">Logic will appear here after parsing</p>
        </div>
      </motion.section>
    );
  }

  if (isLoading) {
    return (
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)]"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-[#f2efff] p-2 text-[#4c2ff1]">
              <FileCode2 className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-slate-900">Generated Validation Logic</h2>
              <p className="text-sm text-slate-500">Generating logic...</p>
            </div>
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 text-center">
          <p className="text-sm text-slate-500">Loading...</p>
        </div>
      </motion.section>
    );
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)]"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-[#f2efff] p-2 text-[#4c2ff1]">
            <FileCode2 className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-slate-900">Generated Validation Logic</h2>
            <p className="text-sm text-slate-500">Tab through the generated runtime logic.</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleEditTab(tab)}
            className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
            aria-label="Edit logic"
          >
            <Edit2 className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={copySnippet}
            className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
            aria-label="Copy generated logic"
          >
            <Copy className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {(["XPath", "XSLT", "Python"] as TabKey[]).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              setTab(key);
              setEditMode(false);
            }}
            className={[
              "rounded-full border px-4 py-2 text-sm font-medium transition",
              tab === key
                ? "border-transparent bg-[#f2efff] text-[#4c2ff1] shadow-[0_8px_20px_rgba(76,47,241,0.12)]"
                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50",
            ].join(" ")}
          >
            {key}
          </button>
        ))}
      </div>

      {editMode ? (
        <div className="space-y-3">
          <textarea
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            className="w-full rounded-2xl border border-slate-200 bg-white p-4 font-mono text-sm leading-6 focus:border-[#4c2ff1] focus:outline-none focus:ring-2 focus:ring-[#4c2ff11f]"
            rows={8}
          />
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setEditMode(false)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveEdit}
              className="rounded-lg bg-[#4c2ff1] px-3 py-2 text-sm text-white hover:bg-[#3a1fd4]"
            >
              Save Changes
            </button>
          </div>
        </div>
      ) : (
        <pre className="overflow-auto rounded-2xl border border-slate-200 bg-[#0b1220] p-4 text-sm leading-6 shadow-inner max-h-[400px]">
          <code className="font-mono text-slate-200">{snippets[tab]}</code>
        </pre>
      )}

      <div className="mt-4 rounded-2xl border border-[#d9d8ff] bg-[#f6f5ff] px-4 py-3 text-sm text-slate-700">
        This rule generates validation logic in multiple formats. Edit to customize if needed.
      </div>
    </motion.section>
  );
}
