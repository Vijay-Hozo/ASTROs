/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
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
  { label: "Dashboard", icon: Home, href: "/dashboard" },
  { label: "Rules Library", icon: FileCode2, href: "/rules-library" },
//   { label: "Rule Engine", icon: Sparkles, href: "/rule-engine" },
//   { label: "Validate Invoices", icon: FileCheck2, href: "/validate-invoices" },
//   { label: "Invoices", icon: FileText },
  { label: "Validation Results", icon: ShieldCheck, href: "/validation-results" },
//   { label: "Dataset Generator", icon: Database },
//   { label: "Reports", icon: BarChart3 },
//   { label: "Settings", icon: Settings },
];

function SidebarContent({ onClose }: { onClose?: () => void }) {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col bg-gradient-to-b from-[#031643] via-[#04153a] to-[#04112f] text-white shadow-[0_30px_80px_rgba(3,12,31,0.45)]">
      <div className="px-5 pt-5 pb-6 border-b border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#4c63ff] to-[#5b2ef1] text-white shadow-[0_0_24px_rgba(76,99,255,0.45)]">
              <ShieldCheck className="h-5 w-5" />
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
        {navItems.map(({ label, icon: Icon, href }) => {
          const active = href ? pathname === href || pathname.startsWith(`${href}/`) : false;

          return (
            <motion.div key={label} whileHover={href ? { x: 2 } : undefined} whileTap={href ? { scale: 0.99 } : undefined}>
              {href ? (
                <Link
                  href={href}
                  onClick={onClose}
                  className={[
                    "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-all duration-200",
                    active
                      ? "bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] text-white shadow-[0_0_24px_rgba(76,47,241,0.4)] ring-1 ring-white/10"
                      : "text-white/85 hover:bg-white/10 hover:text-white",
                  ].join(" ")}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{label}</span>
                </Link>
              ) : (
                <button
                  type="button"
                  aria-disabled="true"
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-white/45"
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{label}</span>
                </button>
              )}
            </motion.div>
          );
        })}
      </nav>

      <div className="p-4">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
          <div className="text-xs text-white/70 mb-3">System Status</div>
          <div className="flex items-center gap-2 mb-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-sm">All systems operational</span>
          </div>
          <p className="text-xs text-white/55">v1.0.0</p>
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