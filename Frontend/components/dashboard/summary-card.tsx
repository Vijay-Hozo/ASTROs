import { AlertCircle } from "lucide-react";

export default function SummaryCard() {
  const rows = [
    ["Invoice ID", "INV_1001"],
    ["Validated On", "20 May 2025 10:30 AM"],
    ["Total Rules", "128"],
    ["Passed", "102"],
    ["Failed", "26"],
    ["Violations", "26"],
  ];

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-[#07122F]">Validation Summary</h3>
        <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">
          <AlertCircle className="h-3 w-3" />
          FAILED
        </span>
      </div>

      <div className="space-y-2 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-center justify-between">
            <span className="text-slate-500">{k}</span>
            <span
              className={[
                "font-medium",
                k === "Passed"
                  ? "text-emerald-600"
                  : k === "Failed" || k === "Violations"
                    ? "text-rose-600"
                    : "text-slate-700",
              ].join(" ")}
            >
              {v}
            </span>
          </div>
        ))}
      </div>

      <button className="mt-4 w-full rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
        View Full Report
      </button>
    </section>
  );
}