import * as vscode from "vscode";
import type { ScanResult } from "../types";

/**
 * WARN/BLOCK/REDACT surfaces as VS Code notifications + modal dialogs.
 * Returns the user's choice for WARN (continue vs cancel enforcement).
 */
export class NotificationController {
  async showBlocked(result: ScanResult): Promise<void> {
    await vscode.window.showErrorMessage(
      `PromptShield BLOCKED this content: ${result.reason}`,
      { modal: true, detail: describeFindings(result) },
      "OK"
    );
  }

  /** Returns true if the user chose to continue anyway. `strictMode`
   * disables the "Continue" choice entirely - only "Cancel" is offered. */
  async showWarning(result: ScanResult, strictMode: boolean): Promise<boolean> {
    if (strictMode) {
      await vscode.window.showWarningMessage(
        `PromptShield WARNING (strict mode - cannot bypass): ${result.reason}`,
        { modal: true, detail: describeFindings(result) },
        "OK"
      );
      return false;
    }
    const choice = await vscode.window.showWarningMessage(
      `PromptShield WARNING: ${result.reason}`,
      { modal: true, detail: describeFindings(result) },
      "Continue Anyway",
      "Cancel"
    );
    return choice === "Continue Anyway";
  }

  showRedacted(result: ScanResult): void {
    void vscode.window.showInformationMessage(
      `PromptShield redacted sensitive content before proceeding: ${result.reason}`
    );
  }

  showAllowed(): void {
    // Deliberately quiet (status bar reflects ALLOW) to avoid notification
    // fatigue on the common path.
  }

  showBackendUnreachable(failureMode: "open" | "closed"): void {
    const message =
      failureMode === "open"
        ? "PromptShield backend is unreachable. Content was allowed through UNSCANNED (failureMode=open)."
        : "PromptShield backend is unreachable. Content was BLOCKED (failureMode=closed).";
    void vscode.window.showWarningMessage(message, "Open Settings").then((choice) => {
      if (choice === "Open Settings") {
        void vscode.commands.executeCommand("workbench.action.openSettings", "promptshield");
      }
    });
  }
}

function describeFindings(result: ScanResult): string {
  const promptFindings = (result.findings ?? []).map((f) => `- [${f.severity}] ${f.detector}: ${f.reason}`);
  const fileFindings = (result.file_findings ?? []).map(
    (f) => `- [${f.risk}] ${f.filename}: ${f.reason}`
  );
  const lines = [...promptFindings, ...fileFindings];
  return lines.length > 0 ? lines.join("\n") : "No individual findings reported.";
}
