import * as vscode from "vscode";
import type { FileFinding } from "../types";

const severityMap: Record<FileFinding["risk"], vscode.DiagnosticSeverity> = {
  CRITICAL: vscode.DiagnosticSeverity.Error,
  HIGH: vscode.DiagnosticSeverity.Error,
  MEDIUM: vscode.DiagnosticSeverity.Warning,
  LOW: vscode.DiagnosticSeverity.Information,
  NONE: vscode.DiagnosticSeverity.Hint,
};

/**
 * Surfaces workspace-monitoring findings in the built-in Problems panel
 * via the VS Code Diagnostics API. Findings are file-level (from
 * ScanResponse.file_findings), so diagnostics are placed on line 1 of the
 * file - the backend's detection pipeline does not currently return
 * character offsets for prompt/file findings, only per-file summaries.
 */
export class DiagnosticsProvider {
  private readonly collection: vscode.DiagnosticCollection;

  constructor() {
    this.collection = vscode.languages.createDiagnosticCollection("promptshield");
  }

  setFindingsForFile(uri: vscode.Uri, findings: FileFinding[], overallReason?: string): void {
    if (findings.length === 0) {
      this.collection.delete(uri);
      return;
    }
    const range = new vscode.Range(0, 0, 0, 1);
    const diagnostics = findings.map((f) => {
      const diag = new vscode.Diagnostic(
        range,
        `PromptShield: ${f.reason} (${f.risk}, action=${f.action})`,
        severityMap[f.risk] ?? vscode.DiagnosticSeverity.Warning
      );
      diag.source = "PromptShield";
      diag.code = f.category;
      return diag;
    });
    if (overallReason) {
      const summary = new vscode.Diagnostic(range, `PromptShield summary: ${overallReason}`, vscode.DiagnosticSeverity.Information);
      summary.source = "PromptShield";
      diagnostics.push(summary);
    }
    this.collection.set(uri, diagnostics);
  }

  clear(uri: vscode.Uri): void {
    this.collection.delete(uri);
  }

  clearAll(): void {
    this.collection.clear();
  }

  dispose(): void {
    this.collection.dispose();
  }
}
