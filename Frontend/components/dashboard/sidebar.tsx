"use client";

import { motion } from "framer-motion";
import {
  BarChart3,
  Database,
  FileCheck2,
  FileCode2,
  FileText,
  Home,
  Settings,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

type SidebarProps = {
  mobileOpen: boolean;
  onClose: () => void;
};

const navItems = [
  { label: "Dashboard", icon: Home },
  { label: "Rule Engine", icon: Sparkles, active: true },
  { label: "Validate Invoices", icon: FileCheck2 },
  { label: "Rules Library", icon: FileCode2 },
  { label: "Invoices", icon: FileText },
  { label: "Validation Results", icon: ShieldCheck },
  { label: "Dataset Generator", icon: Database },
  { label: "Reports", icon: BarChart3 },
  { label: "Settings", icon: Settings },
];

function SidebarContent({ onClose }: { onClose?: () => void }) {
  return (
    <div className="h-full flex flex-col bg-gradient-to-b from-[#031643] to-[#04112f] text-white">
      <div className="px-5 pt-5 pb-6 border-b border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[#4c63ff] to-[#5b2ef1] flex items-center justify-center font-bold">
              IR
            </div>
            <div>
              <h2 className="font-semibold leading-tight">Invoice Rule Engine</h2>
              <p className="text-xs text-white/70">Natural Language to XML Validation</p>
            </div>
          </div>
          {onClose && (
            <button
              className="lg:hidden p-2 rounded-md hover:bg-white/10 transition"
              onClick={onClose}
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <nav className="flex-1 px-4 py-5 space-y-1.5 overflow-y-auto">
        {navItems.map(({ label, icon: Icon, active }) => (
          <button
            key={label}
            className={[
              "w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition",
              active
                ? "bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] shadow-[0_0_20px_rgba(76,47,241,0.35)]"
                : "hover:bg-white/10 text-white/85",
            ].join(" ")}
          >
            <Icon className="h-4 w-4" />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="p-4">
        <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
          <div className="text-xs text-white/70 mb-3">System Status</div>
          <div className="flex items-center gap-2 mb-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-sm">All systems operational</span>
          </div>
          <p className="text-xs text-white/55">Version 1.0.0</p>
        </div>
      </div>
    </div>
  );
}

export function DesktopSidebar() {
  return (
    <aside className="hidden lg:block fixed left-0 top-0 h-screen w-[280px] z-30 border-r border-white/5">
      <SidebarContent />
    </aside>
  );
}

export function MobileSidebar({ mobileOpen, onClose }: SidebarProps) {
  return (
    <>
      {mobileOpen && (
        <button
          className="lg:hidden fixed inset-0 bg-black/40 z-40"
          onClick={onClose}
          aria-label="Close sidebar overlay"
        />
      )}
      <motion.aside
        initial={{ x: -300 }}
        animate={{ x: mobileOpen ? 0 : -300 }}
        transition={{ type: "spring", stiffness: 260, damping: 25 }}
        className="lg:hidden fixed left-0 top-0 h-screen w-[280px] z-50"
      >
        <SidebarContent onClose={onClose} />
      </motion.aside>
    </>
  );
}
