"use client";

import { motion } from "framer-motion";

const xmlPreview = `1  <invoice>
2    <invoice_id>INV_1001</invoice_id>
3    <tax_category>EXEMPT</tax_category>
4    <tax_exemption_reason></tax_exemption_reason>
5  </invoice>`;

const validationBehavior = [
  { status: "PASS", text: "When tax_category is not EXEMPT -> Rule ignored", tone: "text-emerald-600" },
  { status: "PASS", text: "When tax_category is EXEMPT and reason exists -> PASS", tone: "text-emerald-600" },
  { status: "FAIL", text: "When tax_category is EXEMPT and reason missing -> FAIL", tone: "text-rose-600" },
];

export default function XmlPreviewCard() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)]"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">Sample XML Context</h2>
          <p className="mt-1 text-sm text-slate-500">Preview the invoice XML and rule behavior.</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <pre className="overflow-auto rounded-2xl border border-slate-200 bg-[#0b1220] p-4 text-sm leading-6 shadow-inner">
          <code className="font-mono text-slate-200">{xmlPreview}</code>
        </pre>

        <div className="space-y-4 rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Validation Behavior</h3>
            <p className="mt-1 text-sm text-slate-500">The engine resolves the rule from the sample XML context.</p>
          </div>

          <div className="space-y-3">
            {validationBehavior.map((item) => (
              <div
                key={item.text}
                className={[
                  "flex items-start gap-3 rounded-xl border bg-white px-3 py-2.5",
                  item.tone === "text-emerald-600" ? "border-emerald-100" : "border-rose-100",
                ].join(" ")}
              >
                <span
                  className={[
                    "mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold",
                    item.status === "PASS" ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600",
                  ].join(" ")}
                >
                  {item.status === "PASS" ? "✓" : "✕"}
                </span>
                <span className={[
                  "text-sm leading-6",
                  item.tone,
                ].join(" ")}>{item.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.section>
  );
}