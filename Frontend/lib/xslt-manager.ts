import { apiClient } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import type { ParseRuleResponse, ParsedRule, XsltFileDraft, XsltStorageFile } from "@/lib/types";
import { buildEmptyXsltDocument } from "@/lib/xslt-generator";
import { splitMultiRuleText } from "@/lib/rule-parser";

const BUCKET_NAME = "xslt-files";

type XsltMetadataRecord = Record<string, unknown> & {
  name?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
  rule_count?: number;
  rule_texts?: string[];
  parsed_rules?: ParsedRule[];
};

function buildDocumentPath(id: string) {
  return `${id}.xslt`;
}

function buildMetadataPath(id: string) {
  return `${id}.json`;
}

function toFileRecord(id: string, metadata: XsltMetadataRecord | null): XsltStorageFile {
  const name = typeof metadata?.name === "string" ? metadata.name : id;
  const description = typeof metadata?.description === "string" ? metadata.description : undefined;
  const created_at = typeof metadata?.created_at === "string" ? metadata.created_at : new Date().toISOString();
  const updated_at = typeof metadata?.updated_at === "string" ? metadata.updated_at : created_at;
  const rule_count = typeof metadata?.rule_count === "number" ? metadata.rule_count : 0;

  return {
    id,
    name,
    description,
    created_at,
    updated_at,
    rule_count,
    documentPath: buildDocumentPath(id),
    metadataPath: buildMetadataPath(id),
  };
}

async function readMetadata(id: string): Promise<XsltMetadataRecord | null> {
  try {
    const supabase = createClient();
    const { data, error } = await supabase.storage.from(BUCKET_NAME).download(buildMetadataPath(id));
    if (error || !data) return null;

    const text = await data.text();
    try {
      return JSON.parse(text) as XsltMetadataRecord;
    } catch {
      return null;
    }
  } catch (err) {
    console.warn(`Error reading metadata for XSLT file ${id}:`, err instanceof Error ? err.message : err);
    return null;
  }
}

function sanitizeWhitespace(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function normalizeRuleClause(clause: string): string {
  return sanitizeWhitespace(clause).replace(/[.,;]+$/, "");
}

function stripTemplateMessage(message: string): string {
  const cleaned = sanitizeWhitespace(message);
  const prefixes = ["Unsupported rule: "];
  for (const prefix of prefixes) {
    if (cleaned.startsWith(prefix)) {
      return normalizeRuleClause(cleaned.slice(prefix.length));
    }
  }

  const suffixPatterns = [
    / is required(?: when .+)?$/i,
    / is present$/i,
    / passes conditional requirement$/i,
    / must be (?:greater than|less than|at least|at most|equal to|greater than or equal to|less than or equal to) .+$/i,
    / must be between .+ and .+$/i,
    / passes numeric comparison$/i,
    / cannot be in the future$/i,
    / is not in the future$/i,
    / requires both date fields$/i,
    / passes date comparison$/i,
    / matches pattern$/i,
    / must match pattern .+$/i,
    / is valid$/i,
    / must be one of .+$/i,
    / passes cross-field check$/i,
    / failed cross-field check$/i,
    / requires both fields$/i,
    / matches calculated amount$/i,
    / must equal .+ of .+$/i,
  ];

  for (const pattern of suffixPatterns) {
    if (pattern.test(cleaned)) {
      return normalizeRuleClause(cleaned.replace(pattern, ""));
    }
  }

  return normalizeRuleClause(cleaned);
}

export function parseExistingRules(document: string, metadata?: XsltMetadataRecord | null): string[] {
  const stored = metadata?.rule_texts;
  if (Array.isArray(stored) && stored.length > 0) {
    return stored.map((item) => normalizeRuleClause(String(item))).filter(Boolean);
  }

  const parsedRules = metadata?.parsed_rules;
  if (Array.isArray(parsedRules) && parsedRules.length > 0) {
    const fromMetadata = parsedRules
      .map((rule) => normalizeRuleClause(String((rule as ParsedRule & { description?: string }).description || rule.field || rule.rule_type || "")))
      .filter(Boolean);
    if (fromMetadata.length > 0) {
      return fromMetadata;
    }
  }

  const templateMatches = [...document.matchAll(/<xsl:template name="rule-\d+">([\s\S]*?)<\/xsl:template>/g)];
  const extracted = templateMatches
    .map((match) => {
      const messageMatch = match[1].match(/<message>([\s\S]*?)<\/message>/);
      if (messageMatch?.[1]) {
        return stripTemplateMessage(messageMatch[1]);
      }
      const fieldMatch = match[1].match(/field="([^"]*)"/);
      return fieldMatch?.[1] ? normalizeRuleClause(fieldMatch[1]) : "";
    })
    .filter(Boolean);

  return extracted;
}

async function parseWorkspaceRules(ruleTexts: string[]): Promise<ParseRuleResponse> {
  const combined = ruleTexts.map(normalizeRuleClause).filter(Boolean).join("\n");
  return apiClient.post<ParseRuleResponse>("/parse-rule", { rule_text: combined });
}

export async function listXsltFiles(): Promise<XsltStorageFile[]> {
  try {
    // Fetch from backend database endpoint
    const files = await apiClient.get<Array<{
      id: string;
      filename: string;
      description?: string;
      rules_count: number;
      created_at?: string;
    }>>("/api/xslt-files");
    
    if (!Array.isArray(files)) {
      return [];
    }
    
    // Convert DB records to XsltStorageFile format
    return files.map((f) => ({
      id: f.id,
      name: f.filename,
      description: f.description,
      created_at: f.created_at || new Date().toISOString(),
      updated_at: f.created_at || new Date().toISOString(),
      rule_count: f.rules_count,
      documentPath: `${f.id}.xslt`,
      metadataPath: `${f.id}.json`,
    })).sort((left, right) => right.updated_at.localeCompare(left.updated_at));
  } catch (err) {
    console.warn('Failed to list XSLT files:', err instanceof Error ? err.message : err);
    return [];
  }
}

export async function downloadXsltFile(id: string): Promise<string> {
  try {
    const supabase = createClient();
    const { data, error } = await supabase.storage.from(BUCKET_NAME).download(buildDocumentPath(id));
    if (error) {
      console.warn(`Storage error downloading XSLT file ${id}:`, error.message);
      return "";
    }
    if (!data) {
      console.warn(`No data returned when downloading XSLT file ${id}`);
      return "";
    }
    return await data.text();
  } catch (err) {
    console.warn(`Error downloading XSLT file ${id}:`, err instanceof Error ? err.message : err);
    return "";
  }
}

export async function deleteXsltFile(id: string): Promise<void> {
  try {
    console.log(`[DELETE] Deleting XSLT file: ${id} at ${new Date().toISOString()}`);
    const supabase = createClient();
    const { error } = await supabase.storage.from(BUCKET_NAME).remove([buildDocumentPath(id), buildMetadataPath(id)]);
    if (error) {
      console.warn(`Storage error deleting XSLT file ${id}:`, error.message);
      // Don't throw - file may already be deleted or missing
    }
  } catch (err) {
    console.warn(`Error deleting XSLT file ${id}:`, err instanceof Error ? err.message : err);
    // Fail silently for delete operations
  }
}

export async function createXsltFile(draft: XsltFileDraft): Promise<XsltStorageFile> {
  try {
    const supabase = createClient();
    const id = draft.id ?? crypto.randomUUID();
    const now = new Date().toISOString();
    const record = toFileRecord(id, {
      name: draft.name,
      description: draft.description ?? "",
      created_at: now,
      updated_at: now,
      rule_count: draft.rule_count ?? 0,
      rule_texts: draft.rule_texts ?? [],
      parsed_rules: draft.parsed_rules ?? [],
    });

    const document = draft.content ?? buildEmptyXsltDocument(draft.name);
    const documentBlob = new Blob([document], { type: "application/xml" });
    const metadataBlob = new Blob([JSON.stringify(record, null, 2)], { type: "application/json" });

    const [documentResult, metadataResult] = await Promise.all([
      supabase.storage.from(BUCKET_NAME).upload(record.documentPath, documentBlob, { upsert: false, contentType: "application/xml" }),
      supabase.storage.from(BUCKET_NAME).upload(record.metadataPath, metadataBlob, { upsert: false, contentType: "application/json" }),
    ]);

    if (documentResult.error) throw documentResult.error;
    if (metadataResult.error) throw metadataResult.error;

    // Also register in database
    try {
      await apiClient.post("/api/xslt-files", {
        id: id,
        filename: draft.name,
        description: draft.description ?? "",
      });
    } catch (dbErr) {
      console.warn("Failed to register XSLT file in database:", dbErr instanceof Error ? dbErr.message : dbErr);
      // Don't fail completely - file was created in storage
    }

    return record;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("Failed to create XSLT file:", message);
    throw new Error(`Failed to create XSLT file: ${message}`);
  }
}

export async function updateXsltFile(id: string, draft: XsltFileDraft, expectedUpdatedAt?: string): Promise<XsltStorageFile> {
  try {
    const supabase = createClient();
    const existingMetadata = await readMetadata(id);

    if (expectedUpdatedAt && existingMetadata?.updated_at && existingMetadata.updated_at !== expectedUpdatedAt) {
      throw new Error("This XSLT file has changed since it was loaded. Reload and try again.");
    }

    const now = new Date().toISOString();
    const record = toFileRecord(id, {
      name: draft.name,
      description: draft.description ?? (existingMetadata?.description as string | undefined) ?? "",
      created_at: (existingMetadata?.created_at as string | undefined) ?? now,
      updated_at: now,
      rule_count: draft.rule_count ?? (existingMetadata?.rule_count as number | undefined) ?? 0,
      rule_texts: draft.rule_texts ?? existingMetadata?.rule_texts ?? [],
      parsed_rules: draft.parsed_rules ?? existingMetadata?.parsed_rules ?? [],
    });

    const document = draft.content ?? buildEmptyXsltDocument(draft.name);
    const documentBlob = new Blob([document], { type: "application/xml" });
    const metadataBlob = new Blob([JSON.stringify(record, null, 2)], { type: "application/json" });

    const [documentResult, metadataResult] = await Promise.all([
      supabase.storage.from(BUCKET_NAME).upload(record.documentPath, documentBlob, { upsert: true, contentType: "application/xml" }),
      supabase.storage.from(BUCKET_NAME).upload(record.metadataPath, metadataBlob, { upsert: true, contentType: "application/json" }),
    ]);

    if (documentResult.error) throw documentResult.error;
    if (metadataResult.error) throw metadataResult.error;

    return record;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("Failed to update XSLT file:", message);
    throw new Error(`Failed to update XSLT file: ${message}`);
  }
}

export async function createOrUpdateXsltFile(draft: XsltFileDraft, expectedUpdatedAt?: string): Promise<XsltStorageFile> {
  if (draft.id) {
    return updateXsltFile(draft.id, draft, expectedUpdatedAt);
  }
  return createXsltFile(draft);
}

export async function loadXsltFile(id: string): Promise<{ file: XsltStorageFile; content: string; metadata: XsltMetadataRecord | null }> {
  try {
    const [file, content, metadata] = await Promise.all([
      (async () => {
        const meta = await readMetadata(id);
        return toFileRecord(id, meta);
      })(),
      downloadXsltFile(id),
      readMetadata(id),
    ]);

    return { file, content, metadata };
  } catch (err) {
    console.warn(`Error loading XSLT file ${id}:`, err instanceof Error ? err.message : err);
    // Return a safe default even if file is missing
    return {
      file: toFileRecord(id, null),
      content: "",
      metadata: null,
    };
  }
}

export async function appendRulesToXSLTFile(
  file: XsltStorageFile,
  newRuleText: string,
): Promise<{ file: XsltStorageFile; parsed: ParseRuleResponse }> {
  const { content, metadata } = await loadXsltFile(file.id);
  const existingRules = parseExistingRules(content, metadata);
  const appendedRules = [...existingRules, ...splitMultiRuleText(newRuleText)];
  const parsed = await parseWorkspaceRules(appendedRules);

  const updated = await updateXsltFile(file.id, {
    name: file.name,
    description: file.description ?? (metadata?.description as string | undefined) ?? "",
    content: parsed.xslt,
    rule_count: parsed.rule_count,
    rule_texts: appendedRules,
    parsed_rules: parsed.parsed_rules,
  }, file.updated_at);

  return { file: updated, parsed };
}
