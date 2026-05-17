"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { loadXsltFile } from "@/lib/xslt-manager";
import type { ParsedRule, XsltSelection, XsltStorageFile } from "@/lib/types";

const STORAGE_KEY = "astro-active-xslt-workspace";

type XsltWorkspaceState = {
  activeXSLTFile: XsltStorageFile | null;
  activeXSLTFileId: string | null;
  activeXSLTContent: string;
  activeRules: ParsedRule[];
  activeRuleCount: number;
  activeSelection: XsltSelection | null;
  isHydrating: boolean;
  setActiveXSLTSelection: (selection: XsltSelection | null) => Promise<void>;
  updateActiveXSLTWorkspace: (payload: {
    selection: XsltSelection | null;
    file: XsltStorageFile | null;
    content: string;
    rules: ParsedRule[];
  }) => Promise<void>;
  clearActiveXSLTWorkspace: () => void;
};

const XsltWorkspaceContext = createContext<XsltWorkspaceState | undefined>(undefined);

function readStoredSelection(): XsltSelection | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as XsltSelection;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function persistSelection(selection: XsltSelection | null) {
  if (typeof window === "undefined") return;
  if (!selection) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
}

export function XsltWorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [activeSelection, setActiveSelection] = useState<XsltSelection | null>(null);
  const [activeXSLTFile, setActiveXSLTFile] = useState<XsltStorageFile | null>(null);
  const [activeXSLTContent, setActiveXSLTContent] = useState("");
  const [activeRules, setActiveRules] = useState<ParsedRule[]>([]);
  const [activeRuleCount, setActiveRuleCount] = useState(0);
  const [isHydrating, setIsHydrating] = useState(true);

  const syncState = useCallback((payload: {
    selection: XsltSelection | null;
    file: XsltStorageFile | null;
    content: string;
    rules: ParsedRule[];
  }) => {
    setActiveSelection(payload.selection);
    setActiveXSLTFile(payload.file);
    setActiveXSLTContent(payload.content);
    setActiveRules(payload.rules);
    setActiveRuleCount(payload.file?.rule_count ?? payload.rules.length);
    persistSelection(payload.selection);
  }, []);

  const hydrateSelection = useCallback(async (selection: XsltSelection | null) => {
    if (!selection?.file?.id) {
      syncState({ selection, file: null, content: "", rules: [] });
      return;
    }

    const loaded = await loadXsltFile(selection.file.id);
    syncState({
      selection: { ...selection, file: loaded.file },
      file: loaded.file,
      content: loaded.content,
      rules: loaded.metadata?.parsed_rules ?? [],
    });
  }, [syncState]);

  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      const stored = readStoredSelection();
      if (cancelled) return;

      try {
        await hydrateSelection(stored);
      } finally {
        if (!cancelled) setIsHydrating(false);
      }
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, [hydrateSelection]);

  const setActiveXSLTSelection = useCallback(async (selection: XsltSelection | null) => {
    await hydrateSelection(selection);
  }, [hydrateSelection]);

  const updateActiveXSLTWorkspace = useCallback(async (payload: {
    selection: XsltSelection | null;
    file: XsltStorageFile | null;
    content: string;
    rules: ParsedRule[];
  }) => {
    syncState(payload);
  }, [syncState]);

  const clearActiveXSLTWorkspace = useCallback(() => {
    syncState({ selection: null, file: null, content: "", rules: [] });
  }, [syncState]);

  const value = useMemo<XsltWorkspaceState>(() => ({
    activeXSLTFile,
    activeXSLTFileId: activeXSLTFile?.id ?? null,
    activeXSLTContent,
    activeRules,
    activeRuleCount,
    activeSelection,
    isHydrating,
    setActiveXSLTSelection,
    updateActiveXSLTWorkspace,
    clearActiveXSLTWorkspace,
  }), [activeSelection, activeRules, activeRuleCount, activeXSLTContent, activeXSLTFile, isHydrating, setActiveXSLTSelection, updateActiveXSLTWorkspace, clearActiveXSLTWorkspace]);

  return <XsltWorkspaceContext.Provider value={value}>{children}</XsltWorkspaceContext.Provider>;
}

export function useXsltWorkspace() {
  const context = useContext(XsltWorkspaceContext);
  if (!context) {
    throw new Error("useXsltWorkspace must be used within XsltWorkspaceProvider");
  }
  return context;
}