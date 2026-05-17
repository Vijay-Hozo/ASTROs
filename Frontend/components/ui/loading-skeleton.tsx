/**
 * LoadingSkeletons component for data tables and cards
 */

"use client";

import { motion } from "framer-motion";

export function TableLoadingSkeleton() {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm overflow-hidden">
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <motion.div
            key={i}
            className="h-12 bg-gradient-to-r from-slate-200 to-slate-100 rounded-lg"
            animate={{ opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        ))}
      </div>
    </div>
  );
}

export function CardLoadingSkeleton() {
  return (
    <motion.div
      className="h-32 bg-gradient-to-r from-slate-200 to-slate-100 rounded-2xl"
      animate={{ opacity: [0.6, 1, 0.6] }}
      transition={{ duration: 1.5, repeat: Infinity }}
    />
  );
}

export function StatsCardLoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {[...Array(5)].map((_, i) => (
        <motion.div
          key={i}
          className="h-24 bg-gradient-to-r from-slate-200 to-slate-100 rounded-2xl"
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      ))}
    </div>
  );
}
