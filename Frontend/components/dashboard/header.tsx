"use client";

import { motion } from "framer-motion";
import { BookOpen, ChevronDown, Menu, Upload } from "lucide-react";

type HeaderProps = {
  onOpenSidebar: () => void;
};

export default function Header({ onOpenSidebar }: HeaderProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/85 backdrop-blur">
      <div className="px-4 md:px-6 py-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            className="lg:hidden p-2 rounded-lg border border-slate-200 text-slate-700"
            onClick={onOpenSidebar}
            aria-label="Open sidebar"
          >
            <Menu className="h-4 w-4" />
          </button>
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-[#07122F]">Create / Validate Rule</h1>
            <p className="text-sm text-slate-500">
              Write rules in plain English. We&apos;ll convert it into validation logic.
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2 md:gap-3">
          <motion.button whileHover={{ y: -1 }} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:shadow-sm transition">
            <BookOpen className="h-4 w-4" />
            Documentation
          </motion.button>
          <motion.button whileHover={{ y: -1 }} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:shadow-sm transition">
            <Upload className="h-4 w-4" />
            Upload Invoice
          </motion.button>
          <button className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-sm hover:shadow-sm transition">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-[#3749ff] to-[#4c2ff1] text-white text-xs font-semibold">
              AD
            </span>
            <span className="hidden md:inline text-slate-700">Admin User</span>
            <ChevronDown className="h-4 w-4 text-slate-500" />
          </button>
        </div>
      </div>
    </header>
  );
}
