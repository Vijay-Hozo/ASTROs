/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Copy,
  FileCode2,
  FileText,
  Lightbulb,
  Pencil,
  Play,
  Sparkles,
  ShieldCheck,
  TriangleAlert,
  Upload,
  X,
  RefreshCw,
  Tag,
  Plus,
} from "lucide-react";
import { useState, useMemo, useEffect, useRef } from "react";
import Header from "./header";
import StatsCard from "./stats-card";
import { DesktopSidebar, MobileSidebar } from "./sidebar";
import { useApiData } from "@/lib/hooks";
import { apiClient } from "@/lib/api-client";
import { ErrorAlert } from "../ui/error-alert";
import { StatsCardLoadingSkeleton } from "../ui/loading-skeleton";
import type { ActiveWorkspaceSession, DashboardStats, ParseRuleResponse, XsltSelection, XsltStorageFile } from "@/lib/types";
import SetupModal, { hasSetupCompleted } from "./setup-modal";
import { appendRulesToXSLTFile } from "@/lib/xslt-manager";
import { useXsltWorkspace } from "@/lib/xslt-workspace-context";

export default function DashboardShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [currentSampleFilename, setCurrentSampleFilename] = useState<string | null>(null);
  const [currentXsltFilename, setCurrentXsltFilename] = useState<string | null>(null);
  const [currentSampleId, setCurrentSampleId] = useState<number | null>(null);
  const [setupModalMode, setSetupModalMode] = useState<'initial' | 'reupload' | 'rechoose'>('initial');
  const [setupModalInitialXsltSelection, setSetupModalInitialXsltSelection] = useState<XsltSelection | null>(null);
  const [activeSession, setActiveSession] = useState<ActiveWorkspaceSession>({
    sample_id: null,
    sample_filename: null,
    xslt_id: null,
    xslt_filename: null,
    extracted_tags: [],
    status: "default",
  });

  // --- Strict Local State as requested ---
  const [ruleText, setRuleText] = useState("");
  const [parsedRule, setParsedRule] = useState<any | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[] | null>(null);
  const [isDragOverBatch, setIsDragOverBatch] = useState(false);
  const [validationResults, setValidationResults] = useState<any[]>([]);
  const [isValidating, setIsValidating] = useState(false);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [setupSampleFile, setSetupSampleFile] = useState<File | null>(null);

  const [parseLoading, setParseLoading] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [severity, setSeverity] = useState<"low" | "medium" | "high">("high");
  const [progressText, setProgressText] = useState("");
  const [randomPreviewIndex, setRandomPreviewIndex] = useState(0);
  const [previewXmlContent, setPreviewXmlContent] = useState("");
  const [copiedIndex, setCopiedIndex] = useState(false);
  const [expandedFiles, setExpandedFiles] = useState<Record<string, boolean>>({});
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const ruleTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const {
    activeXSLTFile,
    activeXSLTFileId,
    activeXSLTContent,
    activeRules,
    activeSelection,
    setActiveXSLTSelection,
    updateActiveXSLTWorkspace,
  } = useXsltWorkspace();

  // Memoize options to prevent infinite loops
  const dashboardOptions = useMemo(() => ({
    refetchInterval: 60000, // Refetch every 60 seconds
  }), []);

  const { data: dashboardStats, isLoading: statsLoading, error: statsError, refetch: refetchStats } =
    useApiData<DashboardStats>("/dashboard/stats", dashboardOptions);

  // Read XML file whenever previewFile changes
  useEffect(() => {
    if (previewFile) {
      previewFile.text()
        .then((text) => setPreviewXmlContent(text))
        .catch((err) => {
          console.error("Error reading preview file:", err);
          setPreviewXmlContent("");
        });
    } else {
      setPreviewXmlContent("");
    }
  }, [previewFile]);

  // Auto-dismiss toast notifications
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Fetch current active workspace session from backend and keep activeSession in sync
  useEffect(() => {
    const restoreSession = async () => {
      try {
        const data = await apiClient.get<ActiveWorkspaceSession>("/api/workspace/active");
        setActiveSession(data);
        if (data.sample_id) setCurrentSampleId(data.sample_id);
        if (data.sample_filename) setCurrentSampleFilename(data.sample_filename);
        if (data.xslt_id) {
          setCurrentXsltFilename(data.xslt_filename);
        }
      } catch (err: any) {
        console.warn("Failed to restore active workspace session (using defaults):", err?.message || err);
        // Keep using the default empty session state if fetch fails
      }
    };
    restoreSession();
  }, []);

  const selectedSampleXmlName = currentSampleFilename || activeSession.sample_filename || "No sample XML selected";
  const selectedXsltName = activeXSLTFile?.name || currentXsltFilename || activeSession.xslt_filename || "No XSLT file selected";
  const validatedAgainstName = activeXSLTFile?.name || currentXsltFilename || activeSession.xslt_filename || "No XSLT file selected";

  // Parse XML Helper for Preview Card
  const parsedPreviewData = useMemo(() => {
    if (!previewXmlContent) return null;
    try {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(previewXmlContent, "text/xml");
      
      const parserError = xmlDoc.getElementsByTagName("parsererror");
      if (parserError.length > 0) return null;

      const getVal = (tagName: string) => {
        const el = xmlDoc.getElementsByTagName(tagName)[0];
        return el ? el.textContent : "N/A";
      };

      const lineItemsCount =
        xmlDoc.getElementsByTagName("invoice_line").length ||
        xmlDoc.getElementsByTagName("line_item").length ||
        xmlDoc.getElementsByTagName("item").length ||
        0;

      return {
        invoiceId: getVal("invoice_id") || getVal("id") || getVal("ID"),
        sellerName: getVal("seller_name") || getVal("seller") || getVal("SellerName"),
        buyerName: getVal("buyer_name") || getVal("buyer") || getVal("BuyerName"),
        issueDate: getVal("issue_date") || getVal("date") || getVal("IssueDate"),
        currency: getVal("currency") || getVal("CurrencyCode") || getVal("document_currency_code") || "N/A",
        taxableAmount: getVal("taxable_amount") || getVal("TaxableAmount") || "N/A",
        taxAmount: getVal("tax_amount") || getVal("TaxAmount") || "N/A",
        payableAmount: getVal("payable_amount") || getVal("PayableAmount") || "N/A",
        taxCategory: getVal("tax_category") || getVal("TaxCategory") || "N/A",
        lineItemsCount,
      };
    } catch (e) {
      console.error("XML parse error:", e);
      return null;
    }
  }, [previewXmlContent]);

  // Stats definition
  const stats = useMemo(() => {
    if (!dashboardStats) {
      return [
        {
          title: "Total Rules",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: ShieldCheck,
          iconBg: "bg-indigo-50",
          iconColor: "text-indigo-600",
        },
        {
          title: "Invoices Validated",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: FileText,
          iconBg: "bg-emerald-50",
          iconColor: "text-emerald-600",
        },
        {
          title: "Passed Invoices",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: CheckCircle2,
          iconBg: "bg-emerald-50",
          iconColor: "text-emerald-600",
        },
        {
          title: "Failed Invoices",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: AlertTriangle,
          iconBg: "bg-rose-50",
          iconColor: "text-rose-600",
        },
        {
          title: "Total Validations",
          value: "-",
          note: "Loading...",
          noteColor: "text-slate-400",
          icon: TriangleAlert,
          iconBg: "bg-amber-50",
          iconColor: "text-amber-600",
        },
      ];
    }

    const passRate = dashboardStats.pass_rate.toFixed(1);
    const passedCount = dashboardStats.passed_validations ?? dashboardStats.total_passed ?? 0;
    const failedCount = dashboardStats.failed_validations ?? dashboardStats.total_failed ?? (dashboardStats.total_validations - passedCount);

    return [
      {
        title: "Total Rules",
        value: String(dashboardStats.total_rules),
        note: "Active rules",
        noteColor: "text-indigo-600",
        icon: ShieldCheck,
        iconBg: "bg-indigo-50",
        iconColor: "text-indigo-600",
      },
      {
        title: "Invoices Validated",
        value: String(dashboardStats.total_invoices),
        note: `${dashboardStats.total_validations} validations`,
        noteColor: "text-emerald-600",
        icon: FileText,
        iconBg: "bg-emerald-50",
        iconColor: "text-emerald-600",
      },
      {
        title: "Passed Invoices",
        value: String(passedCount),
        note: `${passRate}% Pass Rate`,
        noteColor: "text-emerald-600",
        icon: CheckCircle2,
        iconBg: "bg-emerald-50",
        iconColor: "text-emerald-600",
      },
      {
        title: "Failed Invoices",
        value: String(failedCount),
        note: `${(100 - parseFloat(passRate)).toFixed(1)}% Fail Rate`,
        noteColor: "text-rose-600",
        icon: AlertTriangle,
        iconBg: "bg-rose-50",
        iconColor: "text-rose-600",
      },
      {
        title: "Total Validations",
        value: String(dashboardStats.total_validations),
        note: "All validations",
        noteColor: "text-amber-600",
        icon: TriangleAlert,
        iconBg: "bg-amber-50",
        iconColor: "text-amber-600",
      },
    ];
  }, [dashboardStats]);

  // --- Step 2 Actions ---
  const handleParseRule = async () => {
    if (!ruleText.trim()) return;
    setParseLoading(true);
    setParseError(null);
    try {
      const response = await apiClient.post<ParseRuleResponse>("/parse-rule", {
        rule_text: ruleText,
      });
      setParsedRule(response);
    } catch (err: any) {
      setParseError(err.message || "Failed to parse the rule. Please check format.");
      console.error(err);
    } finally {
      setParseLoading(false);
    }
  };

  const handleSaveRule = async () => {
    if (!ruleText.trim()) {
      setToast({ message: "Rule text cannot be empty", type: "error" });
      return;
    }
    if (!parsedRule) {
      setToast({ message: "Please parse the rule first", type: "error" });
      return;
    }
    if (!parsedRule.xslt) {
      setToast({ message: "Generated XSLT logic is missing", type: "error" });
      return;
    }
    if (!activeSession.xslt_id) {
      setToast({ message: "Select an XSLT workspace before saving the rule", type: "error" });
      return;
    }
    setSaveLoading(true);
    try {
      const workspaceFile: XsltStorageFile = activeXSLTFile ?? {
        id: activeSession.xslt_id,
        name: activeSession.xslt_filename || "xslt",
        description: "",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        rule_count: 0,
        documentPath: `${activeSession.xslt_id}.xslt`,
        metadataPath: `${activeSession.xslt_id}.json`,
      };

      const appendedWorkspace = await appendRulesToXSLTFile(
        workspaceFile,
        ruleText
      );
      await apiClient.post("/rules", {
        rule_text: ruleText,
        severity: severity,
        xslt_id: activeSession.xslt_id,
      });
      setSaveSuccess(true);
      setToast({ message: `Rule saved and synced to ${activeSession.xslt_filename ?? "XSLT"}`, type: "success" });
      await updateActiveXSLTWorkspace({
        selection: activeSelection ? { ...activeSelection, file: appendedWorkspace.file } : { mode: "existing", file: appendedWorkspace.file },
        file: appendedWorkspace.file,
        content: appendedWorkspace.parsed.xslt,
        rules: appendedWorkspace.parsed.parsed_rules,
      });
      
      // Safe reset on success
      setRuleText("");
      setParsedRule(null);
      setParseError(null);
      refetchStats();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      console.error("Save rule failed:", err);
      setToast({ message: err.message || "Failed to save validation rule", type: "error" });
    } finally {
      setSaveLoading(false);
    }
  };

  const handleEditRule = () => {
    // Keeps ruleText in textarea for re-editing, hides parsed logic
    setParsedRule(null);
  };

  const handleClearRule = () => {
    setRuleText("");
    setParsedRule(null);
    setParseError(null);
  };

  const handleTagClick = (tag: string) => {
    setRuleText((prev) => {
      if (!prev) return tag + " ";
      return prev.endsWith(" ") ? prev + tag + " " : prev + " " + tag + " ";
    });
    setTimeout(() => {
      if (ruleTextareaRef.current) {
        ruleTextareaRef.current.focus();
        const len = ruleTextareaRef.current.value.length;
        ruleTextareaRef.current.setSelectionRange(len, len);
      }
    }, 50);
  };

  // --- Step 3 Actions ---
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const filesArray = Array.from(e.target.files);
    const nonEmptyFiles = filesArray.filter((file) => file.size > 0);

    if (nonEmptyFiles.length === 0) {
      setToast({
        message: "Empty XML files are not accepted. Please upload at least one non-empty XML file.",
        type: "error",
      });
      return;
    }

    setUploadedFiles(nonEmptyFiles);
    setToast({
      message:
        nonEmptyFiles.length === filesArray.length
          ? `${nonEmptyFiles.length} XML file${nonEmptyFiles.length === 1 ? "" : "s"} uploaded successfully`
          : `${nonEmptyFiles.length} XML file${nonEmptyFiles.length === 1 ? "" : "s"} uploaded successfully; skipped ${filesArray.length - nonEmptyFiles.length} empty file${filesArray.length - nonEmptyFiles.length === 1 ? "" : "s"}`,
      type: "success",
    });
    
    // Set initial preview file
    if (filesArray.length > 1) {
      const randIdx = Math.floor(Math.random() * filesArray.length);
      setRandomPreviewIndex(randIdx);
      setPreviewFile(filesArray[randIdx]);
    } else {
      setRandomPreviewIndex(0);
      setPreviewFile(filesArray[0]);
    }
  };

  const handleEditFiles = () => {
    fileInputRef.current?.click();
  };

  const handleClearFiles = () => {
    setUploadedFiles(null);
    setPreviewFile(null);
    setValidationResults([]);
    setExpandedFiles({});
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleShowAnother = () => {
    if (!uploadedFiles || uploadedFiles.length <= 1) return;
    let nextIdx = randomPreviewIndex;
    while (nextIdx === randomPreviewIndex) {
      nextIdx = Math.floor(Math.random() * uploadedFiles.length);
    }
    setRandomPreviewIndex(nextIdx);
    setPreviewFile(uploadedFiles[nextIdx]);
  };

  const handleDragOverBatch = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOverBatch(true);
  };

  const handleDragLeaveBatch = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOverBatch(false);
  };

  const handleDropBatch = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOverBatch(false);

    const droppedFiles = e.dataTransfer?.files;
    if (droppedFiles && droppedFiles.length > 0) {
      const filesArray = Array.from(droppedFiles).filter((file) => file.type === "application/xml" || file.name.endsWith(".xml"));
      if (filesArray.length === 0) {
        setToast({ message: "Please drop XML files only", type: "error" });
        return;
      }

      const nonEmptyFiles = filesArray.filter((file) => file.size > 0);
      if (nonEmptyFiles.length === 0) {
        setToast({ message: "Empty XML files are not accepted", type: "error" });
        return;
      }

      setUploadedFiles(nonEmptyFiles);
      setToast({
        message: `${nonEmptyFiles.length} XML file${nonEmptyFiles.length === 1 ? "" : "s"} dropped and ready to validate`,
        type: "success",
      });

      if (nonEmptyFiles.length > 0) {
        const randIdx = Math.floor(Math.random() * nonEmptyFiles.length);
        setRandomPreviewIndex(randIdx);
        setPreviewFile(nonEmptyFiles[randIdx]);
      }
    }
  };

  const handleValidateBulk = async () => {
    if (!uploadedFiles || uploadedFiles.length === 0) return;
    if (!activeXSLTFile?.id || !activeXSLTContent) {
      setToast({ message: "Choose an XSLT file before validating XML", type: "error" });
      setShowSetupModal(true);
      return;
    }
    setIsValidating(true);
    setValidationResults([]);
    setExpandedFiles({});
    let skippedEmptyFiles = 0;
    let validatedFiles = 0;
    
    try {
      for (let i = 0; i < uploadedFiles.length; i++) {
        const file = uploadedFiles[i];
        setProgressText(`Validating ${i + 1} of ${uploadedFiles.length}...`);
        
        const xmlText = await file.text();
        if (!xmlText.trim()) {
          skippedEmptyFiles += 1;
          continue;
        }

        validatedFiles += 1;
        const response = await apiClient.post<any>("/validate/workspace", {
          xml_content: xmlText,
          xslt_content: activeXSLTContent,
          xslt_name: activeXSLTFile.name,
        });

        const newResult = {
          filename: file.name,
          validatedAgainst: activeXSLTFile?.name ?? null,
          results: response.results || [],
        };

        setValidationResults((prev) => [...prev, newResult]);
        // Expand the first file validation by default
        if (i === 0) {
          setExpandedFiles((prev) => ({ ...prev, [file.name]: true }));
        }
      }
      refetchStats();

      if (skippedEmptyFiles > 0) {
        setToast({
          message:
            validatedFiles > 0
              ? `Validated ${validatedFiles} file${validatedFiles === 1 ? "" : "s"}; skipped ${skippedEmptyFiles} empty file${skippedEmptyFiles === 1 ? "" : "s"}`
              : "No non-empty XML files were found to validate.",
          type: validatedFiles > 0 ? "success" : "error",
        });
      }
      
      // Clean UI reset once upload + validation completes successfully
      setUploadedFiles(null);
      setPreviewFile(null);
      setValidationResults([]);
      setExpandedFiles({});
      if (fileInputRef.current) fileInputRef.current.value = "";
      
    } catch (err) {
      console.error("Bulk validation failed:", err);
    } finally {
      setIsValidating(false);
      setProgressText("");
    }
  };

  const toggleFileExpansion = (filename: string) => {
    setExpandedFiles((prev) => ({
      ...prev,
      [filename]: !prev[filename],
    }));
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(true);
    setTimeout(() => setCopiedIndex(false), 2000);
  };

  const handleSetupComplete = async (payload: { xmlFile: File | null; xsltSelection: XsltSelection; sampleId: number | null }) => {
    // 1. Set extracted_tags = [] immediately (clears old chips from UI)
    setActiveSession((prev) => ({ ...prev, extracted_tags: [] }));

    if (typeof window !== "undefined") {
      window.localStorage.setItem(
        "astro-dashboard-setup-config",
        JSON.stringify({
          xmlFileName: payload.xmlFile?.name ?? null,
          xsltMode: payload.xsltSelection.mode,
          xsltFileId: payload.xsltSelection.file?.id ?? null,
          xsltName: payload.xsltSelection.file?.name ?? payload.xsltSelection.draft?.name ?? null,
        }),
      );
    }
    setShowSetupModal(false);

    // 2. Call PUT /api/workspace/active
    try {
      const freshData = await apiClient.put<ActiveWorkspaceSession>("/api/workspace/active", {
        sample_id: payload.sampleId,
        xslt_id: payload.xsltSelection.file?.id ?? null,
        xslt_filename: payload.xsltSelection.file?.name ?? payload.xsltSelection.draft?.name ?? null,
      });
      // 3. On response, set full activeSession with new data
      setActiveSession(freshData);
      setCurrentSampleId(freshData.sample_id);
      setCurrentSampleFilename(freshData.sample_filename);
      setCurrentXsltFilename(freshData.xslt_filename);
    } catch (err) {
      console.error("Failed to update active workspace session:", err);
    }

    setToast({ message: "Workspace setup completed", type: "success" });
    setSetupSampleFile(payload.xmlFile ?? null);
    if (payload.xmlFile) setPreviewFile(payload.xmlFile);
    await setActiveXSLTSelection(payload.xsltSelection);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <SetupModal
        open={showSetupModal}
        onComplete={handleSetupComplete}
        onClose={() => setShowSetupModal(false)}
        initialSampleId={currentSampleId}
        initialXsltSelection={activeSelection}
        skipMarkSetupComplete={setupModalMode !== 'initial'}
      />
      <DesktopSidebar />
      <MobileSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="lg:pl-[280px]">
        <Header onOpenSidebar={() => setMobileOpen(true)} />

        <main className="p-4 md:p-6">
          <div className="mx-auto max-w-[1440px] space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Selected Sample XML</p>
                    <div className="mt-1 flex items-center gap-2">
                      <p className="truncate text-sm font-semibold text-slate-900">{selectedSampleXmlName}</p>
                      {activeSession.status === "default" && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                          default
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Selected XSLT File</p>
                    <div className="mt-1 flex items-center gap-2">
                      <p className="truncate text-sm font-semibold text-slate-900">{selectedXsltName}</p>
                      {activeSession.status === "default" && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                          default
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <button
                    type="button"
                    onClick={() => {
                      setSetupModalMode('initial');
                      setSetupModalInitialXsltSelection(activeSelection);
                      setShowSetupModal(true);
                    }}
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2.5 text-sm font-semibold text-indigo-700 transition hover:border-indigo-300 hover:bg-indigo-100"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Reselect Sample + XSLT
                  </button>
                </div>
              </div>
            </div>
            
            {/* Stats Section */}
            {statsError && <ErrorAlert error={statsError} onRetry={refetchStats} />}

            {statsLoading ? (
              <StatsCardLoadingSkeleton />
            ) : (
              <motion.section
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5"
              >
                {stats.map((item) => (
                  <StatsCard key={item.title} {...item} />
                ))}
              </motion.section>
            )}

            {/* Step 2 and Step 3 Cards Row */}
            <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">

              {/* STEP 3: XML Upload & Validate Card */}
              <motion.section
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm min-h-[500px]"
              >
                <div className="mb-4">
                  <h3 className="text-lg font-bold tracking-tight text-slate-900">Step 1: Upload Invoices & Validate</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Upload single or bulk XML files to run real-time schemas & templates.</p>
                </div>

                {uploadedFiles ? (
                  // Files Selected / Uploaded state
                  <div className="flex-1 flex flex-col justify-between">
                    <div className="space-y-4">
                      {/* Selection Box Header */}
                      <div className="flex items-center justify-between rounded-xl bg-indigo-50/50 border border-indigo-100 p-3">
                        <div className="flex-1 min-w-0 pr-3">
                          <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider block mb-0.5">Uploaded XML files</span>
                          <p className="text-sm font-semibold text-slate-800 truncate">
                            {uploadedFiles.length === 1 ? uploadedFiles[0].name : `${uploadedFiles.length} XML files selected`}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <button
                            onClick={handleEditFiles}
                            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-white rounded-lg border border-slate-100 transition shadow-sm animate-none"
                            title="Replace File"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={handleClearFiles}
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-white rounded-lg border border-slate-100 transition shadow-sm"
                            title="Clear Files"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Display file item list */}
                      <div className="max-h-[220px] overflow-y-auto border border-slate-100 rounded-xl divide-y divide-slate-50 bg-slate-50/50 p-2">
                        {uploadedFiles.map((file, idx) => (
                          <div key={idx} className="flex items-center justify-between py-2 px-3 text-xs text-slate-700">
                            <span className="font-semibold truncate max-w-[80%]">{file.name}</span>
                            <span className="text-slate-400">{(file.size / 1024).toFixed(1)} KB</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Progress Indicator */}
                    <div className="mt-4 pt-3 border-t border-slate-100">
                      {isValidating ? (
                        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-3 text-center mb-3 animate-pulse">
                          <span className="text-sm font-bold text-indigo-700 block">{progressText}</span>
                          <span className="text-xs text-indigo-500">Executing sequential pipeline parser...</span>
                        </div>
                      ) : (
                        validationResults.length > 0 && (
                          <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-3 text-center mb-3 flex items-center justify-center gap-2">
                            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                            <span className="text-xs font-bold text-emerald-800">Sequential Validation Complete!</span>
                          </div>
                        )
                      )}

                      <button
                        onClick={handleValidateBulk}
                        disabled={isValidating}
                        className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] py-3 text-sm font-semibold text-white shadow-md disabled:opacity-50 transition"
                      >
                        <Play className="h-4 w-4" />
                        {isValidating ? "Running validation pipeline..." : "Validate Selected XSLT"}
                      </button>
                    </div>
                  </div>
                ) : (
                  // Upload prompting State
                  <div className="flex-1 flex flex-col justify-between">
                    <div
                      className={`flex-1 flex flex-col items-center justify-center border-2 border-dashed rounded-2xl p-6 cursor-pointer transition ${
                        isDragOverBatch
                          ? "border-indigo-400 bg-indigo-50"
                          : "border-slate-200 bg-slate-50/50 hover:bg-slate-50"
                      }`}
                      onClick={() => fileInputRef.current?.click()}
                      onDragOver={handleDragOverBatch}
                      onDragLeave={handleDragLeaveBatch}
                      onDrop={handleDropBatch}
                    >
                      <Upload className={`h-10 w-10 mb-2 transition ${isDragOverBatch ? "text-indigo-500" : "text-slate-400"}`} />
                      <p className="text-sm font-semibold text-slate-700 text-center">Drag and drop XML files here, or click to choose files</p>
                      <p className="text-xs text-slate-400 text-center mt-1">Accepts multiple files. Maximum size per file is 1MB.</p>
                    </div>

                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".xml"
                      multiple
                      className="hidden"
                      onChange={handleFileSelect}
                    />

                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full mt-4 inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 py-3 text-sm font-semibold text-slate-700 transition"
                    >
                      <Upload className="h-4 w-4" />
                      Choose XML Invoices
                    </button>
                  </div>
                )}
              </motion.section>

              {/* STEP 2: Write/Parse Rule Card */}
              <motion.section
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm min-h-[500px]"
              >
                <div className="mb-4">
                  <h3 className="text-lg font-bold tracking-tight text-slate-900">Step 2: Write Rule in Natural Language</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Author standard compliance validation templates in plain English.</p>
                </div>

                {parseError && (
                  <div className="mb-3 space-y-2 animate-fadeIn">
                    <ErrorAlert error={{ message: parseError } as any} />
                    <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-3.5 text-xs text-indigo-800">
                      <div className="flex items-center gap-2 mb-1.5 font-bold">
                        <Lightbulb className="h-4 w-4 text-indigo-600" />
                        Supported Invoice Fields Guide
                      </div>
                      <p className="mb-2 leading-relaxed">
                        To prevent LLM hallucinations and ensure deterministic validation, the rule engine strictly verifies assertions against these 12 standard invoice fields:
                      </p>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-[10px] bg-white/60 p-2 rounded-lg border border-indigo-100/30">
                        <div>• tax_amount (Tax amount)</div>
                        <div>• taxable_amount (Taxable amount)</div>
                        <div>• payable_amount (Total amount)</div>
                        <div>• invoice_id (Invoice id)</div>
                        <div>• seller_name (Seller name)</div>
                        <div>• buyer_name (Buyer name)</div>
                        <div>• issue_date (Issue date)</div>
                        <div>• currency_code (Currency)</div>
                        <div>• tax_category (Tax category)</div>
                        <div>• tax_exemption_reason</div>
                        <div>• buyer_vat (Buyer vat)</div>
                        <div>• purchase_order (Purchase order)</div>
                      </div>
                      <p className="mt-2 text-indigo-700 leading-relaxed">
                        💡 **Try rewriting as:** <code className="bg-white/80 px-1 py-0.5 rounded font-mono font-bold">Tax amount must be between 0 and 28</code>
                      </p>
                    </div>
                  </div>
                )}

                <div className="flex-1 flex flex-col justify-between space-y-4">
                  {/* Always visible input area */}
                  <div className="space-y-4">
                    {activeSession.extracted_tags && activeSession.extracted_tags.length > 0 && (
                      <div className="mb-3 space-y-1.5">
                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                          <Tag className="h-3 w-3 text-indigo-500" />
                          Extracted Invoice Tags (Click to insert)
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {activeSession.extracted_tags.map(tag => (
                            <button
                              key={tag}
                              type="button"
                              onClick={() => handleTagClick(tag)}
                              className="px-2.5 py-1 text-xs rounded-lg bg-indigo-50/80 hover:bg-indigo-100 text-indigo-700 border border-indigo-200/60 font-mono transition shadow-sm hover:shadow active:scale-95 flex items-center gap-1 cursor-pointer"
                              title={`Insert ${tag} into rule`}
                            >
                              <span>{tag}</span>
                              <Plus className="h-3 w-3 opacity-60" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    <textarea
                      ref={ruleTextareaRef}
                      value={ruleText}
                      onChange={(e) => setRuleText(e.target.value)}
                      disabled={parseLoading}
                      className="h-28 w-full resize-none rounded-xl border border-slate-200 p-4 text-sm text-slate-900 bg-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 disabled:bg-slate-50 transition"
                      placeholder="Example: If tax category is exempt, tax exemption reason is required."
                      maxLength={500}
                    />
                    <div className="flex justify-between items-center text-[11px] text-slate-400">
                      <span className="inline-flex items-center gap-1.5">
                        <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
                        Tip: Use standard invoice fields (e.g. tax_amount, buyer_name)
                      </span>
                      <span>{ruleText.length}/500</span>
                    </div>

                    <button
                      onClick={handleParseRule}
                      disabled={parseLoading || !ruleText.trim()}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3749ff] to-[#4c2ff1] py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-100 hover:opacity-95 disabled:opacity-50 transition"
                    >
                      <Sparkles className="h-4 w-4" />
                      {parseLoading ? "Parsing rule..." : "Parse Rule"}
                    </button>
                  </div>

                  {/* Display Key Parsed Fields (Dynamically generated after parse click, otherwise empty) */}
                  <div className="grid grid-cols-3 gap-2 bg-slate-50 p-3 rounded-xl border border-slate-100 text-xs">
                    <div>
                      <span className="text-slate-400 block font-medium">Rule Type</span>
                      <span className="font-bold text-slate-800 capitalize truncate block">
                        {parseLoading ? (
                          <span className="inline-block h-3.5 w-16 bg-slate-200 rounded animate-pulse" />
                        ) : parsedRule ? (
                          (parsedRule.parsed_rule?.rule_type || parsedRule.rule_type || "N/A").replace(/_/g, " ")
                        ) : (
                          "-"
                        )}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block font-medium">Field</span>
                      <span className="font-bold text-slate-800 truncate block">
                        {parseLoading ? (
                          <span className="inline-block h-3.5 w-16 bg-slate-200 rounded animate-pulse" />
                        ) : parsedRule ? (
                          parsedRule.parsed_rule?.field || parsedRule.field || "N/A"
                        ) : (
                          "-"
                        )}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block font-medium">Operation</span>
                      <span className="font-bold text-slate-800 capitalize truncate block">
                        {parseLoading ? (
                          <span className="inline-block h-3.5 w-16 bg-slate-200 rounded animate-pulse" />
                        ) : parsedRule ? (
                          parsedRule.parsed_rule?.operation || parsedRule.operation || "N/A"
                        ) : (
                          "-"
                        )}
                      </span>
                    </div>
                  </div>

                  {parsedRule?.parsed_rules && parsedRule.parsed_rules.length > 1 && (
                    <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 px-3 py-2 text-xs text-indigo-800">
                      Parsed {parsedRule.parsed_rules.length} intents from a single input.
                    </div>
                  )}

                  {/* Parser Logic (Structured JSON) Block */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-slate-600">Parser Logic (Structured JSON)</span>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            JSON.stringify(
                              parsedRule?.parsed_rules?.length ? parsedRule.parsed_rules : parsedRule?.parsed_rule || {},
                              null,
                              2,
                            ),
                          )
                        }
                        disabled={!parsedRule}
                        className="inline-flex items-center gap-1 text-[10px] text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed px-2 py-0.5 rounded transition"
                      >
                        <Copy className="h-3 w-3" />
                        {copiedIndex ? "Copied" : "Copy"}
                      </button>
                    </div>
                    <div className="relative border border-slate-200 rounded-xl bg-slate-900 p-3 h-[110px] overflow-y-auto font-mono text-[11px] leading-5 text-indigo-400">
                      <pre className="whitespace-pre-wrap">
                        {parseLoading ? (
                          "// Extracting structured parser logic..."
                        ) : parsedRule ? (
                          JSON.stringify(
                            parsedRule.parsed_rules?.length ? parsedRule.parsed_rules : parsedRule.parsed_rule,
                            null,
                            2,
                          ) || "// No parsed rule"
                        ) : (
                          "// Structured parser JSON will be shown here"
                        )}
                      </pre>
                    </div>
                  </div>

                  {/* XSLT Monospace Scrollable Block */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-slate-600">XSLT Logic</span>
                      <button
                        onClick={() => copyToClipboard(parsedRule?.xslt || "")}
                        disabled={!parsedRule}
                        className="inline-flex items-center gap-1 text-[10px] text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed px-2 py-0.5 rounded transition"
                      >
                        <Copy className="h-3 w-3" />
                        {copiedIndex ? "Copied" : "Copy"}
                      </button>
                    </div>
                    <div className="relative border border-slate-200 rounded-xl bg-slate-950 p-3 h-[110px] overflow-y-auto font-mono text-[11px] leading-5 text-emerald-400">
                      <pre className="whitespace-pre-wrap">
                        {parseLoading ? (
                          "<!-- Generating XSLT validation template... -->"
                        ) : parsedRule ? (
                          parsedRule.xslt || "<!-- No XSLT parsed -->"
                        ) : (
                          "<!-- XSLT validation logic will be generated here -->"
                        )}
                      </pre>
                    </div>
                  </div>

                  {/* Optional XPath & Python Logic */}
                  {parsedRule && (parsedRule.parsed_rule?.xpath || parsedRule.xpath) && (
                    <div className="animate-fadeIn">
                      <span className="text-xs font-semibold text-slate-600 block mb-1">XPath Logic</span>
                      <div className="border border-slate-200 rounded-xl bg-slate-50 p-2 font-mono text-[10px] text-slate-700 break-all">
                        {parsedRule.parsed_rule?.xpath || parsedRule.xpath}
                      </div>
                    </div>
                  )}

                  {parsedRule && (parsedRule.parsed_rule?.python_logic || parsedRule.python_logic) && (
                    <div className="animate-fadeIn">
                      <span className="text-xs font-semibold text-slate-600 block mb-1">Python Logic</span>
                      <div className="border border-slate-200 rounded-xl bg-slate-50 p-2 font-mono text-[10px] text-slate-700 whitespace-pre-wrap max-h-[60px] overflow-y-auto">
                        {parsedRule.parsed_rule?.python_logic || parsedRule.python_logic}
                      </div>
                    </div>
                  )}

                  {/* Implement / Save Rule Section inside card */}
                  <div className="border-t border-slate-100 pt-4 mt-auto space-y-3">
                    <div className="flex items-center justify-between gap-3 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-600">Severity:</span>
                        <select
                          value={severity}
                          onChange={(e: any) => setSeverity(e.target.value)}
                          className={`rounded-lg border px-2.5 py-1 focus:outline-none transition-all duration-200 cursor-pointer font-bold text-xs ${
                            severity === "high"
                              ? "border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100 hover:border-rose-300 focus:ring-2 focus:ring-rose-100"
                              : severity === "medium"
                              ? "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 hover:border-amber-300 focus:ring-2 focus:ring-amber-100"
                              : "border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100 hover:border-sky-300 focus:ring-2 focus:ring-sky-100"
                          }`}
                        >
                          <option value="low" className="bg-white text-slate-800 font-normal">Low</option>
                          <option value="medium" className="bg-white text-slate-800 font-normal">Medium</option>
                          <option value="high" className="bg-white text-slate-800 font-normal">High</option>
                        </select>
                      </div>
                      {saveSuccess && (
                        <span className="inline-flex items-center gap-1 text-emerald-600 font-bold animate-pulse">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Rule Saved!
                        </span>
                      )}
                    </div>

                    <button
                      onClick={handleSaveRule}
                      disabled={saveLoading || !parsedRule}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 py-2.5 text-sm font-semibold text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                      <Sparkles className="h-4 w-4" />
                      {saveLoading ? "Saving..." : "Save Rule to Library"}
                    </button>
                  </div>
                </div>
              </motion.section>

            </section>

            {/* XML PREVIEW CARD (Moved ABOVE validation results) */}
            <motion.section
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-50 pb-3">
                <div>
                  <h3 className="text-lg font-bold tracking-tight text-slate-900">Invoice Metadata Preview</h3>
                  <p className="text-xs text-slate-500">Live parsed values of the active XML invoice layout.</p>
                </div>
                {uploadedFiles && uploadedFiles.length > 1 && (
                  <div className="flex items-center gap-2.5">
                    <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 border border-indigo-100 rounded-full px-3 py-1">
                      Previewing {randomPreviewIndex + 1} of {uploadedFiles.length} uploaded files
                    </span>
                    <button
                      onClick={handleShowAnother}
                      className="text-xs font-bold text-slate-700 hover:text-indigo-600 bg-white hover:bg-slate-50 border border-slate-200 px-3 py-1 rounded-lg transition"
                    >
                      Show another
                    </button>
                  </div>
                )}
              </div>

              {!previewFile ? (
                // Empty state
                <div className="py-10 text-center border border-dashed border-slate-100 rounded-xl">
                  <FileCode2 className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-slate-500">Upload an XML to preview</p>
                </div>
              ) : (
                // Loaded preview details
                parsedPreviewData ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                    {[
                      { label: "Invoice ID", value: parsedPreviewData.invoiceId },
                      { label: "Issue Date", value: parsedPreviewData.issueDate },
                      { label: "Seller Name", value: parsedPreviewData.sellerName },
                      { label: "Buyer Name", value: parsedPreviewData.buyerName },
                      { label: "Currency", value: parsedPreviewData.currency },
                      { label: "Taxable Amount", value: parsedPreviewData.taxableAmount },
                      { label: "Tax Amount", value: parsedPreviewData.taxAmount },
                      { label: "Payable Amount", value: parsedPreviewData.payableAmount },
                      { label: "Tax Category", value: parsedPreviewData.taxCategory },
                      { label: "Line Items Count", value: parsedPreviewData.lineItemsCount },
                    ].map(({ label, value }) => (
                      <div key={label} className="bg-slate-50/50 border border-slate-100/80 rounded-xl p-3 hover:bg-white hover:shadow-sm hover:border-indigo-100/50 transition">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-0.5">{label}</span>
                        <span className="text-sm font-bold text-slate-800 block truncate">{value}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-8 text-center border border-dashed border-slate-100 rounded-xl">
                    <p className="text-sm font-semibold text-rose-500">Failed to parse preview metadata. Invalid XML.</p>
                  </div>
                )
              )}
            </motion.section>

            {/* VALIDATION RESULTS SECTION (Grouped by Filename, Collapsible) */}
            {validationResults.length > 0 && (
              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                <div>
                  <h3 className="text-lg font-bold tracking-tight text-slate-900">Validation Results</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Results of executing rules sequentially against your upload.</p>
                  <p className="mt-1 text-xs font-semibold text-indigo-700">Validated Against: {validatedAgainstName}</p>
                </div>

                <div className="space-y-3">
                  {validationResults.map((fileRes) => {
                    const { filename, results } = fileRes;
                    const passed = results.filter((r: any) => r.status === "PASS").length;
                    const failed = results.filter((r: any) => r.status === "FAIL").length;
                    const errors = results.filter((r: any) => r.status === "ERROR").length;
                    const isExpanded = !!expandedFiles[filename];

                    return (
                      <div
                        key={filename}
                        className="border border-slate-200 rounded-2xl overflow-hidden bg-white shadow-sm hover:shadow transition duration-200"
                      >
                        {/* Collapsible Accordion Header */}
                        <button
                          onClick={() => toggleFileExpansion(filename)}
                          className="w-full flex items-center justify-between p-4 bg-slate-50/50 hover:bg-slate-50/80 transition duration-200"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            {isExpanded ? (
                              <ChevronDown className="h-5 w-5 text-slate-400 flex-shrink-0" />
                            ) : (
                              <ChevronRight className="h-5 w-5 text-slate-400 flex-shrink-0" />
                            )}
                            <span className="font-bold text-slate-800 text-sm truncate">{filename}</span>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-100">
                              {passed} PASS
                            </span>
                            <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-700 border border-rose-100">
                              {failed + errors} FAIL
                            </span>
                          </div>
                        </button>

                        {/* Collapsible content */}
                        {isExpanded && (
                          <div className="border-t border-slate-100 p-4 overflow-x-auto">
                            <table className="w-full text-xs md:text-sm text-left border-collapse">
                              <thead>
                                <tr className="text-slate-500 uppercase tracking-wider text-[10px] font-bold border-b border-slate-200 pb-2">
                                  <th className="pb-2 font-semibold pl-2">Rule Text</th>
                                  <th className="pb-2 font-semibold">Status</th>
                                  <th className="pb-2 font-semibold pr-2">Message</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                {results.map((r: any, rIdx: number) => {
                                  const isPass = r.status === "PASS";
                                  return (
                                    <tr
                                      key={rIdx}
                                      className={
                                        isPass
                                          ? "bg-emerald-50/20 hover:bg-emerald-50/40 transition duration-150"
                                          : "bg-rose-50/20 hover:bg-rose-50/40 transition duration-150"
                                      }
                                    >
                                      <td className="py-2.5 px-2 text-slate-700 font-semibold max-w-sm truncate">{r.rule_text}</td>
                                      <td className="py-2.5 px-2">
                                        <span
                                          className={
                                            isPass
                                              ? "inline-block rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800"
                                              : "inline-block rounded-full bg-rose-100 px-2.5 py-0.5 text-[10px] font-bold text-rose-800"
                                          }
                                        >
                                          {r.status}
                                        </span>
                                      </td>
                                      <td className="py-2.5 px-2 text-slate-600 italic max-w-xs truncate">{r.message || "-"}</td>
                                    </tr>
                                  );
                                })}
                                {results.length === 0 && (
                                  <tr>
                                    <td colSpan={3} className="py-4 text-center text-slate-400 text-xs">
                                      No rules validated against this file.
                                    </td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </motion.section>
            )}

          </div>
        </main>
      </div>

      {/* Sleek, premium, animated Toast Notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="fixed bottom-5 right-5 z-50 flex items-center gap-3 rounded-2xl border border-slate-100 bg-white/95 p-4 pr-5 shadow-[0_20px_50px_rgba(0,0,0,0.15)] backdrop-blur-md"
          >
            {toast.type === "success" ? (
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <CheckCircle2 className="h-5 w-5" />
              </div>
            ) : (
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 text-rose-600">
                <AlertCircle className="h-5 w-5" />
              </div>
            )}
            <div className="min-w-[180px]">
              <h4 className="text-sm font-bold text-slate-800">
                {toast.type === "success" ? "Success" : "Error"}
              </h4>
              <p className="text-xs text-slate-500">{toast.message}</p>
            </div>
            <button
              onClick={() => setToast(null)}
              className="ml-4 p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-50 transition"
              aria-label="Close notification"
            >
              <X className="h-4 w-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
