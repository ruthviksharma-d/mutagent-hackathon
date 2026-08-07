import * as vscode from "vscode";
import * as path from "path";
import type { PromptShieldSettings } from "./settings";
import type { Logger } from "./utils/logger";
import { classifyFile, mimeTypeFor } from "./utils/fileTypeUtils";
import type { ScanFilePayload } from "./types";

export interface ExtractionResult {
  ok: boolean;
  payload?: ScanFilePayload;
  skippedReason?: string;
}

/**
 * File scanning orchestration: reads a supported file locally in the
 * extension host, extracts plain text (never sends raw binary except for
 * the already-text-safe base64 wrapping the backend's ScanFileInput
 * expects), and enforces `promptshield.maxFileSizeKb`. Extraction
 * libraries (pdf-parse/mammoth/exceljs) are pure-JS/WASM - no native
 * binaries - so they run fine in the extension host process.
 */
export class FileScanner {
  constructor(
    private readonly settings: PromptShieldSettings,
    private readonly logger: Logger
  ) {}

  async extractFromUri(uri: vscode.Uri): Promise<ExtractionResult> {
    const filename = path.basename(uri.fsPath);
    const kind = classifyFile(filename);
    if (!kind) {
      return { ok: false, skippedReason: `Unsupported file type: ${filename}` };
    }

    let stat: vscode.FileStat;
    try {
      stat = await vscode.workspace.fs.stat(uri);
    } catch (err) {
      return { ok: false, skippedReason: `Could not stat file: ${err instanceof Error ? err.message : err}` };
    }

    const maxBytes = this.settings.maxFileSizeKb * 1024;
    if (stat.size > maxBytes) {
      return {
        ok: false,
        skippedReason: `${filename} is ${(stat.size / 1024).toFixed(0)}KB, exceeds maxFileSizeKb (${this.settings.maxFileSizeKb}KB).`,
      };
    }

    const bytes = await vscode.workspace.fs.readFile(uri);
    const buffer = Buffer.from(bytes);

    let text: string;
    try {
      switch (kind.kind) {
        case "pdf":
          text = await this.extractPdf(buffer);
          break;
        case "docx":
          text = await this.extractDocx(buffer);
          break;
        case "xlsx":
          text = await this.extractXlsx(buffer);
          break;
        case "csv":
        case "text":
        default:
          text = buffer.toString("utf-8");
          break;
      }
    } catch (err) {
      this.logger.warn(`Extraction failed for ${filename}`, err instanceof Error ? err.message : err);
      return { ok: false, skippedReason: `Text extraction failed for ${filename}.` };
    }

    const contentBase64 = Buffer.from(text, "utf-8").toString("base64");
    return {
      ok: true,
      payload: {
        filename,
        contentBase64,
        mimeType: mimeTypeFor(kind.ext),
        sizeBytes: Buffer.byteLength(text, "utf-8"),
      },
    };
  }

  private async extractPdf(buffer: Buffer): Promise<string> {
    // pdf-parse is CommonJS; require() lazily so extension activation
    // isn't slowed down by loading it before it's ever needed.
    const pdfParse = require("pdf-parse") as (b: Buffer) => Promise<{ text: string }>;
    const result = await pdfParse(buffer);
    return result.text;
  }

  private async extractDocx(buffer: Buffer): Promise<string> {
    const mammoth = require("mammoth") as {
      extractRawText: (opts: { buffer: Buffer }) => Promise<{ value: string }>;
    };
    const result = await mammoth.extractRawText({ buffer });
    return result.value;
  }

  private async extractXlsx(buffer: Buffer): Promise<string> {
    const ExcelJS = require("exceljs");
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(buffer);
    const lines: string[] = [];
    workbook.eachSheet((sheet: any) => {
      lines.push(`# Sheet: ${sheet.name}`);
      sheet.eachRow((row: any) => {
        const values = Array.isArray(row.values) ? row.values.slice(1) : [];
        lines.push(values.map((v: unknown) => (v === null || v === undefined ? "" : String(v))).join(","));
      });
    });
    return lines.join("\n");
  }
}
