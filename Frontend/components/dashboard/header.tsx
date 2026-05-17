/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import { motion } from "framer-motion";
import { Bell, BookOpen, ChevronDown, LibraryBig, Menu } from "lucide-react";

type HeaderProps = {
  onOpenSidebar: () => void;
  title?: string;
  subtitle?: string;
};

export default function Header({
  onOpenSidebar,
  title = "Create / Validate Rule",
  subtitle = "Write rules in plain English. We’ll convert it into validation logic.",
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 px-4 py-4 md:px-6">
        <div className="flex items-center gap-3">
          <button
            className="rounded-lg border border-slate-200 p-2 text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 lg:hidden"
            onClick={onOpenSidebar}
            aria-label="Open sidebar"
          >
            <Menu className="h-4 w-4" />
          </button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-[#07122F] md:text-[30px]">
              {title}
            </h1>
            <p className="text-sm text-slate-500 md:text-[15px]">{subtitle}</p>
          </div>
        </div>

        <div className="hidden items-center gap-2 md:flex md:gap-3">
          <motion.button whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:shadow-sm">
            <BookOpen className="h-4 w-4" />
            Documentation
          </motion.button>
          {/* <motion.button whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:shadow-sm">
            <LibraryBig className="h-4 w-4" />
            Rules Library
          </motion.button> */}
          <button
            className="relative inline-flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:shadow-sm"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute right-2 top-2 h-2.5 w-2.5 rounded-full border-2 border-white bg-rose-500" />
          </button>
          <button className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-sm transition hover:border-slate-300 hover:shadow-sm">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-[#3749ff] to-[#4c2ff1] text-xs font-semibold text-white">
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