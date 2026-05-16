"use client";

import { ChevronDown, Search } from "lucide-react";
import { useMemo, useState } from "react";

type Row = {
  id: string;
  rule: string;
  severity: "High" | "Medium";
  status: "PASS" | "FAIL";
  message: string;
};

const allRows: Row[] = [
  {
    id: "R00123",
    rule: "If tax category is exempt, tax exemption reason is required.",
    severity: "High",
    status: "FAIL",
    message: "Tax exemption reason is required when tax category is EXEMPT.",
  },
  {
    id: "R00110",
    rule: "Invoice ID is required.",
    severity: "High",
    status: "PASS",
    message: "-",
  },
  {
    id: "R00105",
    rule: "Issue date cannot be in the future.",
    severity: "Medium",
    status: "PASS",
    message: "-",
  },
  {
    id: "R00102",
    rule: "Tax amount must be greater than or equal to 0.",
    severity: "Medium",
    status: "PASS",
    message: "-",
  },
  {
    id: "R00098",
    rule: "Payable amount must equal taxable amount + tax amount.",
    severity: "High",
    status: "FAIL",
    message: "Payable amount does not match taxable amount + tax amount.",
  },
  {
    id: "R00090",
    rule: "Seller tax number is required.",
    severity: "Medium",
    status: "PASS",
    message: "-",
  },
];

const PAGE_SIZE = 5;

export default function ValidationTable() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"ALL" | "PASS" | "FAIL">("ALL");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return allRows.filter((row) => {
      const matchesFilter = filter === "ALL" ? true : row.status === filter;
      const matchesSearch =
        row.id.toLowerCase().includes(q) ||
        row.rule.toLowerCase().includes(q) ||
        row.message.toLowerCase().includes(q);
      return matchesFilter && matchesSearch;
    });
  }, [query, filter]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageRows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
        <h3 className="font-semibold text-[#07122F]">4. Validation Results (Preview)</h3>
        <div className="flex items-center gap-2">
          <label className="relative">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              placeholder="Search rule..."
              className="h-9 rounded-lg border border-slate-200 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
          </label>
          <select
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value as "ALL" | "PASS" | "FAIL");
              setPage(1);
            }}
            className="h-9 rounded-lg border border-slate-200 px-2 text-sm"
          >
            <option value="ALL">All</option>
            <option value="PASS">Pass</option>
            <option value="FAIL">Fail</option>
          </select>
        </div>
      </div>

      <div className="overflow-auto rounded-xl border border-slate-200">
        <table className="min-w-[900px] w-full text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="text-left px-3 py-2">Rule ID</th>
              <th className="text-left px-3 py-2">Rule</th>
              <th className="text-left px-3 py-2">Severity</th>
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-left px-3 py-2">Message</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row) => (
              <tr key={row.id} className="border-t border-slate-100 hover:bg-slate-50/80 transition">
                <td className="px-3 py-2 font-medium text-slate-700">{row.id}</td>
                <td className="px-3 py-2 text-slate-600">{row.rule}</td>
                <td className="px-3 py-2">
                  <span
                    className={[
                      "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                      row.severity === "High"
                        ? "bg-rose-50 text-rose-700"
                        : "bg-amber-50 text-amber-700",
                    ].join(" ")}
                  >
                    {row.severity}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <span
                    className={[
                      "inline-flex rounded-full px-2 py-0.5 text-xs font-semibold",
                      row.status === "PASS"
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-rose-50 text-rose-700",
                    ].join(" ")}
                  >
                    {row.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-600">{row.message}</td>
                <td className="px-3 py-2 text-right text-slate-400">
                  <ChevronDown className="h-4 w-4 inline" />
                </td>
              </tr>
            ))}
            {pageRows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                  No results found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <button className="text-sm text-[#432EF1] hover:text-[#3223bd]">View All Violations (26)</button>
        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded-lg border border-slate-200 px-3 py-1.5 disabled:opacity-50"
            disabled={safePage === 1}
          >
            Prev
          </button>
          <span className="text-slate-500">
            Page {safePage} of {pageCount}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            className="rounded-lg border border-slate-200 px-3 py-1.5 disabled:opacity-50"
            disabled={safePage === pageCount}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
