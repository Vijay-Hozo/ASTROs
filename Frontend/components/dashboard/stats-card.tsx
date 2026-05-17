"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

type StatsCardProps = {
  title: string;
  value: string;
  note: string;
  noteColor: string;
  icon: LucideIcon;
  iconBg: string;
  iconColor: string;
};

export default function StatsCard({
  title,
  value,
  note,
  noteColor,
  icon: Icon,
  iconBg,
  iconColor,
}: StatsCardProps) {
  return (
    <motion.div whileHover={{ y: -4 }} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs text-slate-500">{title}</p>
          <p className="mt-1 text-3xl font-bold text-[#07122F]">{value}</p>
          <p className={"mt-1 text-xs " + noteColor}>{note}</p>
        </div>
        <div className={"flex h-10 w-10 items-center justify-center rounded-xl " + iconBg}>
          <Icon className={"h-5 w-5 " + iconColor} />
        </div>
      </div>
    </motion.div>
  );
}