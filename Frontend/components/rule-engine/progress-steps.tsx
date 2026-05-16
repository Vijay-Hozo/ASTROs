"use client";

import { motion } from "framer-motion";

const steps = [
  { step: 1, title: "Write Rule", subtitle: "Enter rule in plain English" },
  { step: 2, title: "Parse & Structure", subtitle: "Extract rule components" },
  { step: 3, title: "Generate Logic", subtitle: "Create validation logic" },
  { step: 4, title: "Validate", subtitle: "Run against invoices" },
];

export default function ProgressSteps() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-slate-200/80 bg-white px-4 py-5 shadow-[0_12px_36px_rgba(15,23,42,0.06)] md:px-6"
    >
      <div className="relative grid gap-4 md:grid-cols-4 md:gap-3">
        {/* <div className="absolute left-0 right-0 top-7 hidden h-px bg-slate-200 md:block" /> */}
        {/* <div className="absolute left-0 top-7 hidden h-px w-[25%] md:block" /> */}
        {steps.map((item) => (
          <motion.div
            key={item.step}
            whileHover={{ y: -2 }}
            className="relative rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:bg-transparent md:p-0"
          >
            <div className="flex items-start gap-3 p-1">
              <div
                className={[
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-full border text-sm font-semibold shadow-sm",
                  item.step === 1
                    ? "border-transparent bg-gradient-to-br from-[#3749ff] to-[#4c2ff1] text-white shadow-[0_10px_24px_rgba(76,47,241,0.32)]"
                    : "border-slate-200 bg-white text-slate-500",
                ].join(" ")}
              >
                {item.step}
              </div>
              <div className="pt-0.5">
                <h3 className="font-semibold text-slate-900">{item.title}</h3>
                <p className="text-sm text-slate-500">{item.subtitle}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.section>
  );
}