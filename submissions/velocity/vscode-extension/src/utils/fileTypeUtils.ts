import type { SupportedFileKind } from "../types";

/**
 * Supported extensions per the task spec: txt, md, py, js, ts, java, c,
 * cpp, cs, go, rs, env, json, yaml, yml, xml, sql, pdf, docx, xlsx, csv.
 * Everything except pdf/docx/xlsx/csv is read as plain UTF-8 text.
 */
const TEXT_EXTS = new Set([
  "txt", "md", "py", "js", "ts", "tsx", "jsx", "java", "c", "cpp", "cc", "cs",
  "go", "rs", "env", "json", "yaml", "yml", "xml", "sql",
]);

export function classifyFile(filename: string): SupportedFileKind | null {
  const ext = extOf(filename);
  if (!ext) return null;
  if (ext === "pdf") return { ext, kind: "pdf" };
  if (ext === "docx") return { ext, kind: "docx" };
  if (ext === "xlsx") return { ext, kind: "xlsx" };
  if (ext === "csv") return { ext, kind: "csv" };
  if (TEXT_EXTS.has(ext)) return { ext, kind: "text" };
  return null;
}

export function extOf(filename: string): string {
  const base = filename.replace(/\\/g, "/").split("/").pop() ?? filename;
  // Handle dotfiles like ".env" -> ext "env"
  const dot = base.lastIndexOf(".");
  if (dot <= 0) return base.startsWith(".") ? base.slice(1).toLowerCase() : "";
  return base.slice(dot + 1).toLowerCase();
}

export function isSupportedExtension(filename: string): boolean {
  return classifyFile(filename) !== null;
}

export function mimeTypeFor(ext: string): string {
  const map: Record<string, string> = {
    txt: "text/plain",
    md: "text/markdown",
    py: "text/x-python",
    js: "text/javascript",
    ts: "text/typescript",
    json: "application/json",
    yaml: "application/x-yaml",
    yml: "application/x-yaml",
    xml: "application/xml",
    sql: "application/sql",
    pdf: "application/pdf",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    csv: "text/csv",
  };
  return map[ext] ?? "application/octet-stream";
}
