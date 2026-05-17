"use client";

export interface PdfSection {
  title: string;
  lines: string[];
}

function escapePdfText(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function wrapLines(lines: string[], maxLength = 88): string[] {
  const wrapped: string[] = [];
  for (const line of lines) {
    const words = line.split(/\s+/).filter(Boolean);
    let current = "";
    for (const word of words) {
      const candidate = current ? `${current} ${word}` : word;
      if (candidate.length > maxLength) {
        if (current) wrapped.push(current);
        current = word;
      } else {
        current = candidate;
      }
    }
    if (current) wrapped.push(current);
    if (words.length === 0) wrapped.push("");
  }
  return wrapped.length > 0 ? wrapped : [""];
}

export function buildSimplePdfBlob(title: string, sections: PdfSection[]): Blob {
  const pageWidth = 595;
  const pageHeight = 842;
  const marginLeft = 40;
  const top = 800;
  const lines: string[] = [title, ""];

  for (const section of sections) {
    lines.push(section.title);
    lines.push(...section.lines.flatMap((line) => wrapLines([line])));
    lines.push("");
  }

  const contentLines: string[] = ["BT", "/F1 10 Tf", `${marginLeft} ${top} Td`, "12 TL"];
  for (let index = 0; index < lines.length; index += 1) {
    const line = escapePdfText(lines[index]);
    if (index === 0) {
      contentLines.push(`(${line}) Tj`);
    } else {
      contentLines.push(`T* (${line}) Tj`);
    }
  }
  contentLines.push("ET");
  const content = contentLines.join("\n");
  const contentBytes = new TextEncoder().encode(content);

  const objects: Uint8Array[] = [
    new TextEncoder().encode("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"),
    new TextEncoder().encode("2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n"),
    new TextEncoder().encode(
      `3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n`,
    ),
    new TextEncoder().encode("4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"),
    new TextEncoder().encode(`5 0 obj << /Length ${contentBytes.length} >> stream\n`),
    contentBytes,
    new TextEncoder().encode("\nendstream endobj\n"),
  ];

  let offset = 0;
  const chunks: BlobPart[] = [];
  const header = new TextEncoder().encode("%PDF-1.4\n");
  chunks.push(header.buffer.slice(header.byteOffset, header.byteOffset + header.byteLength) as ArrayBuffer);
  offset += header.length;

  const offsets: number[] = [0];
  for (const object of objects) {
    offsets.push(offset);
    chunks.push(object.buffer.slice(object.byteOffset, object.byteOffset + object.byteLength) as ArrayBuffer);
    offset += object.length;
  }

  const xrefStart = offset;
  const xrefLines = [`xref`, `0 ${offsets.length}`, `0000000000 65535 f `];
  for (const objectOffset of offsets.slice(1)) {
    xrefLines.push(`${String(objectOffset).padStart(10, "0")} 00000 n `);
  }
  xrefLines.push(`trailer << /Size ${offsets.length} /Root 1 0 R >>`, `startxref`, String(xrefStart), `%%EOF`);
  const xrefBytes = new TextEncoder().encode(`${xrefLines.join("\n")}`);
  chunks.push(xrefBytes.buffer.slice(xrefBytes.byteOffset, xrefBytes.byteOffset + xrefBytes.byteLength) as ArrayBuffer);

  return new Blob(chunks, { type: "application/pdf" });
}

export async function downloadPdfBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
