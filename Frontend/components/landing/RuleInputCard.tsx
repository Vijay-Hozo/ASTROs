"use client";

import { useState } from "react";
import {  Zap } from "lucide-react";
import { motion } from "framer-motion";

export default function RuleInputCard() {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);

  function handleSubmit() {
    setLoading(true);
    setTimeout(() => setLoading(false), 900);
  }

  return (
    <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="max-w-4xl mx-auto px-6 py-8">
      <div className="bg-white rounded-2xl shadow-lg border border-border p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-textDarkBlue">Try it Now — Write a Rule in Plain English</h3>
            <p className="text-sm text-textDarkBlue/70 mt-1">Example: If tax category is exempt, tax exemption reason is required.</p>
          </div>
        </div>

        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Example: If tax category is exempt, tax exemption reason is required."
          className="mt-6 w-full h-40 rounded-xl p-4 border border-border focus:outline-none transition resize-none bg-secondaryBackground text-textDarkBlue"
        />

        <div className="flex items-center justify-between mt-4">
          <div className="flex items-center gap-3 text-sm text-textDarkBlue/70">
            <Zap className="w-4 h-4 text-buttonBlue" />
            <span>Tip: Use simple English. Example: Buyer name is required</span>
          </div>

          <div>
            <motion.button whileTap={{ scale: 0.98 }} onClick={handleSubmit} className="inline-flex items-center gap-3 px-5 py-3 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 text-white shadow-lg">
              <Zap className="w-4 h-4" />
              <span>{loading ? "Parsing…" : "Parse & Generate Rule"}</span>
            </motion.button>
          </div>
        </div>
      </div>
    </motion.section>
  );
}
