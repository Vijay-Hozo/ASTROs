"use client";

import { useState, useRef } from "react";
import { XmlTag, uploadSampleXml } from "@/lib/api-client";

interface XmlTagChipsProps {
  onTagClick: (tag: string) => void;
}

export function XmlTagChips({ onTagClick }: XmlTagChipsProps) {
  const [knownTags, setKnownTags] = useState<XmlTag[]>([]);
  const [unknownTags, setUnknownTags] = useState<XmlTag[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploaded, setUploaded] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) {
      console.log("[chips] no file selected");
      return;
    }
    console.log("[chips] uploading:", file.name);
    setLoading(true);
    setError(null);
    try {
      const result = await uploadSampleXml(file);
      console.log("[chips] result:", result);
      setKnownTags(result.known_tags);
      setUnknownTags(result.unknown_tags);
      setUploaded(true);
      console.log("[chips] state updated, uploaded=true");
    } catch (err: any) {
      console.log("[chips] error:", err.message);
      setError(err.message || "Failed to parse XML.");
    } finally {
      setLoading(false);
    }
  }

  if (!uploaded) {
    return (
      <div className="mb-3">
        <p className="text-xs text-muted-foreground mb-2">
          Upload a sample XML to see available tags you can use in your rule.
        </p>
        <label
          className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-md border border-dashed border-border cursor-pointer hover:bg-muted transition-colors"
          onClick={() => fileRef.current?.click()}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          {loading ? "Parsing XML..." : "Upload sample XML"}
        </label>
        <input
          ref={fileRef}
          type="file"
          accept=".xml"
          className="hidden"
          onChange={handleFile}
        />
        {error && (
          <p className="text-xs text-destructive mt-1">{error}</p>
        )}
      </div>
    );
  }

  return (
    <div className="mb-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Tags from your XML — click to insert into rule
        </p>
        <button
          className="text-xs text-muted-foreground underline"
          onClick={() => {
            setUploaded(false);
            setKnownTags([]);
            setUnknownTags([]);
            if (fileRef.current) fileRef.current.value = "";
          }}
        >
          clear
        </button>
      </div>

      {/* Known tags — green */}
      {knownTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {knownTags.map((t) => (
            <button
              key={t.tag}
              type="button"
              title={`${t.xpath} · ${t.inferred_type} · sample: ${t.sample_value}`}
              onClick={() => onTagClick(t.tag)}
              className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-800 border border-green-200 hover:bg-green-100 transition-colors dark:bg-green-950 dark:text-green-200 dark:border-green-800"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0" />
              {t.tag}
            </button>
          ))}
        </div>
      )}

      {/* Unknown tags — amber */}
      {unknownTags.length > 0 && (
        <div>
          <p className="text-xs text-amber-600 dark:text-amber-400 mb-1">
            ⚠ Non-standard tags — XSLT will query these directly from your XML
          </p>
          <div className="flex flex-wrap gap-1.5">
            {unknownTags.map((t) => (
              <button
                key={t.tag}
                type="button"
                title={`${t.xpath} · ${t.inferred_type} · sample: ${t.sample_value}\nNot in standard schema. Will be queried directly.`}
                onClick={() => onTagClick(t.tag)}
                className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 hover:bg-amber-100 transition-colors dark:bg-amber-950 dark:text-amber-200 dark:border-amber-800"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0" />
                {t.tag}
              </button>
            ))}
          </div>
        </div>
      )}

      <input
        ref={fileRef}
        type="file"
        accept=".xml"
        className="hidden"
        onChange={handleFile}
      />
    </div>
  );
}
