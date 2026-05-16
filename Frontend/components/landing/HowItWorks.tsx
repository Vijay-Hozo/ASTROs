"use client"
import { motion } from "framer-motion";
import { FileText, Box, Code, CheckCircle } from "lucide-react";

const steps = [
  { title: "Write Rule", desc: "Enter validation rules in plain English.", icon: FileText },
  { title: "We Structure It", desc: "Our engine understands and structures the rule.", icon: Box },
  { title: "Generate Logic", desc: "We convert it into executable XML validation logic.", icon: Code },
  { title: "Validate Invoices", desc: "Run the rule against XML invoices and get results.", icon: CheckCircle },
];

export default function HowItWorks() {
  return (
    <section id="how" className="max-w-6xl mx-auto py-12 px-6">
      <h3 className="text-center text-2xl font-semibold mb-8 text-textDarkBlue">How It Works</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {steps.map((s, idx) => {
          const Icon = s.icon;
          return (
            <motion.div whileHover={{ y: -6 }} key={s.title} className="bg-secondaryBackground border border-border rounded-2xl p-6 text-left shadow-sm hover:shadow-lg transition">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-primaryBackground text-textDarkBlue font-semibold flex items-center justify-center">{idx + 1}</div>
                <div className="w-10 h-10 rounded-lg bg-white/30 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-buttonBlue" />
                </div>
              </div>
              <h4 className="font-semibold text-textDarkBlue mb-2">{s.title}</h4>
              <p className="text-textDarkBlue/70 text-sm">{s.desc}</p>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
