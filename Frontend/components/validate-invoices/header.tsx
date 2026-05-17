"use client";

import React from "react";

type Props = {
  title?: string;
  subtitle?: string;
};

export default function Header({ title = "Validate Invoices", subtitle = "Upload invoices and run validation rules" }: Props) {
  return (
    <div className="mb-6 flex items-start justify-between">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
      </div>
    </div>
  );
}
