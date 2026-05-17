export type ValidationStatus = "PASS" | "FAIL" | "REVIEW";

export type ValidationResult = {
  id: string;
  invoiceId: string;
  date: string;
  rulesChecked: number;
  passed: number;
  failed: number;
  status: ValidationStatus;
  xmlFile?: string;
  failedRules?: { rule: string; severity: string; message?: string }[];
};

export const SAMPLE_RESULTS: ValidationResult[] = [
  {
    id: "VR-001",
    invoiceId: "INV-1001",
    date: "2026-05-15 09:12",
    rulesChecked: 12,
    passed: 11,
    failed: 1,
    status: "FAIL",
    xmlFile: "inv-1001.xml",
    failedRules: [
      { rule: "Seller name is required", severity: "High", message: "Missing seller/name element" },
      { rule: "Tax amount must be 18% of taxable amount", severity: "High", message: "Calculated tax mismatch" },
    ],
  },
  {
    id: "VR-002",
    invoiceId: "INV-1002",
    date: "2026-05-14 14:22",
    rulesChecked: 10,
    passed: 10,
    failed: 0,
    status: "PASS",
    xmlFile: "inv-1002.xml",
    failedRules: [],
  },
  {
    id: "VR-003",
    invoiceId: "INV-1003",
    date: "2026-05-13 07:45",
    rulesChecked: 9,
    passed: 8,
    failed: 1,
    status: "REVIEW",
    xmlFile: "inv-1003.xml",
    failedRules: [{ rule: "Invoice ID must be unique", severity: "Critical", message: "Duplicate invoice reference" }],
  },
];
