import * as vscode from "vscode";
import { PromptShieldApi, siteLabelFor, UnauthorizedError } from "./api";
import type { PromptShieldSettings } from "./settings";
import type { Logger } from "./utils/logger";
import { NotificationController } from "./ui/notifications";
import type { StatusBarController } from "./ui/statusBar";
import type { ScanHistoryStore } from "./services/scanHistoryStore";
import type { AuditQueueService } from "./services/auditQueueService";
import type { ScanResult, PromptContext, Decision } from "./types";

/**
 * Chat participant (`@promptshield`) + the scan/intercept commands. This
 * is the practical prompt-interception mechanism for VS Code: there is no
 * VS Code API that lets an extension transparently intercept another
 * extension's (Copilot Chat, Antigravity's agent, etc.) outbound network
 * traffic to an LLM. Instead PromptShield offers:
 *   1. `@promptshield <text>` in ANY chat panel that supports participants
 *      (Copilot Chat's panel) - scans the message before you'd otherwise
 *      send it to a different participant.
 *   2. Commands (`scanSelection`, `scanClipboardPrompt`, `interceptAndSend`)
 *      a user runs BEFORE pasting text into Copilot/Antigravity/any other
 *      AI chat UI - this is a manual-but-explicit interception step, not
 *      silent network interception.
 * See README.md "Interception model" for the full rationale.
 */
export class PromptInterceptor {
  private readonly notifications = new NotificationController();

  constructor(
    private readonly api: PromptShieldApi,
    private readonly settings: PromptShieldSettings,
    private readonly logger: Logger,
    private readonly statusBar: StatusBarController,
    private readonly history: ScanHistoryStore,
    private readonly auditQueue: AuditQueueService
  ) {}

  registerChatParticipant(context: vscode.ExtensionContext): vscode.ChatParticipant | undefined {
    if (!("chat" in vscode) || typeof (vscode as any).chat?.createChatParticipant !== "function") {
      this.logger.warn("vscode.chat.createChatParticipant is not available in this host - chat participant disabled.");
      return undefined;
    }

    const handler: vscode.ChatRequestHandler = async (request, chatContext, stream, token) => {
      if (!this.settings.enablePromptScan) {
        stream.markdown("Prompt scanning is disabled (`promptshield.enablePromptScan`).");
        return {};
      }

      const conversationHistory = this.settings.enableConversationContext
        ? extractHistory(chatContext)
        : undefined;

      const promptContext: PromptContext = {
        promptText: request.prompt,
        conversationHistory,
        activeFileName: vscode.window.activeTextEditor?.document.fileName,
        languageId: vscode.window.activeTextEditor?.document.languageId,
        workspaceName: vscode.workspace.name,
        workspaceId: vscode.workspace.workspaceFile?.toString() ?? vscode.workspace.name,
        userEmail: undefined,
        timestamp: Date.now(),
        site: siteLabelFor({ workspaceName: vscode.workspace.name }),
      };

      stream.progress("Scanning with PromptShield...");
      const outcome = await this.runScan(promptContext.promptText, promptContext.site, promptContext);
      if (token.isCancellationRequested) return {};

      this.renderScanToChat(stream, outcome.result, outcome.wasBackendReachable);
      return {};
    };

    const participant = (vscode as any).chat.createChatParticipant("promptshield.guardian", handler);
    participant.iconPath = vscode.Uri.joinPath(context.extensionUri, "media", "activity-icon.svg");
    return participant;
  }

  private renderScanToChat(stream: vscode.ChatResponseStream, result: ScanResult, backendReachable: boolean): void {
    stream.markdown(`**Decision: ${result.decision}** (risk: ${result.risk}, score: ${result.score})\n\n`);
    stream.markdown(`${result.reason}\n\n`);
    if (!backendReachable) {
      stream.markdown(`_Note: backend was unreachable; this result was NOT scanned server-side (failureMode=${this.settings.failureMode})._\n\n`);
    }
    if (result.findings.length > 0) {
      stream.markdown(`**Findings:**\n`);
      for (const f of result.findings) {
        stream.markdown(`- [${f.severity}] ${f.detector}: ${f.reason}\n`);
      }
    }
    if (result.decision === "REDACT" || result.decision === "ALLOW") {
      stream.markdown(`\n**Text to use:**\n\n\`\`\`\n${result.sanitized_prompt}\n\`\`\`\n`);
    }
  }

  /** Runs a scan, updates status bar/history/audit-queue, and applies
   * failureMode - the single funnel every command/chat-handler goes through. */
  async runScan(
    promptText: string,
    site: string,
    _context?: PromptContext
  ): Promise<{ result: ScanResult; wasBackendReachable: boolean }> {
    try {
      const outcome = await this.api.scanWithFailureMode(promptText, site);
      this.statusBar.setLastDecision(outcome.result.decision, outcome.result.reason);
      await this.history.record(site, outcome.result, promptText);
      if (!outcome.wasBackendReachable) {
        await this.auditQueue.enqueue(this.api.buildScanBody(promptText, site), outcome.result.decision);
        this.notifications.showBackendUnreachable(this.settings.failureMode);
      }
      return outcome;
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        void vscode.window
          .showWarningMessage("PromptShield session expired. Please sign in again.", "Sign In")
          .then((choice) => {
            if (choice === "Sign In") void vscode.commands.executeCommand("promptshield.login");
          });
      }
      throw err;
    }
  }

  /**
   * Enforces the decision against a body of text the caller intends to
   * use. Returns the text to actually use (redacted or original) or
   * `undefined` if the action should be cancelled (BLOCK, or user chose
   * Cancel on a WARN).
   */
  async enforce(result: ScanResult, backendReachable: boolean): Promise<string | undefined> {
    switch (result.decision) {
      case "ALLOW":
        this.notifications.showAllowed();
        return result.sanitized_prompt;
      case "REDACT":
        this.notifications.showRedacted(result);
        return result.sanitized_prompt;
      case "WARN": {
        const proceed = await this.notifications.showWarning(result, this.settings.strictMode);
        return proceed ? result.sanitized_prompt : undefined;
      }
      case "BLOCK":
        await this.notifications.showBlocked(result);
        return undefined;
    }
  }

  // ---- Commands ----

  async scanSelectionCommand(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.selection.isEmpty) {
      void vscode.window.showInformationMessage("PromptShield: select some text first.");
      return;
    }
    const text = editor.document.getText(editor.selection);
    const site = siteLabelFor({ workspaceName: vscode.workspace.name });
    await this.scanAndEnforceInteractive(text, site);
  }

  async scanClipboardCommand(): Promise<void> {
    const text = await vscode.env.clipboard.readText();
    if (!text.trim()) {
      void vscode.window.showInformationMessage("PromptShield: clipboard is empty.");
      return;
    }
    const site = siteLabelFor({ workspaceName: vscode.workspace.name });
    await this.scanAndEnforceInteractive(text, site);
  }

  async interceptAndSendCommand(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    const text = editor && !editor.selection.isEmpty
      ? editor.document.getText(editor.selection)
      : await vscode.env.clipboard.readText();
    if (!text.trim()) {
      void vscode.window.showInformationMessage("PromptShield: nothing to scan (no selection, empty clipboard).");
      return;
    }
    const site = siteLabelFor({ workspaceName: vscode.workspace.name });
    const finalText = await this.scanAndEnforceInteractive(text, site);
    if (finalText !== undefined) {
      await vscode.env.clipboard.writeText(finalText);
      void vscode.window.showInformationMessage(
        "PromptShield: approved text copied to clipboard. Paste it into Copilot Chat / Antigravity / your AI tool of choice."
      );
    }
  }

  private async scanAndEnforceInteractive(text: string, site: string): Promise<string | undefined> {
    try {
      const outcome = await this.runScan(text, site);
      return this.enforce(outcome.result, outcome.wasBackendReachable);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      void vscode.window.showErrorMessage(`PromptShield scan failed: ${message}`);
      return undefined;
    }
  }
}

function extractHistory(context: vscode.ChatContext): string[] {
  try {
    return context.history
      .map((turn) => {
        if ("prompt" in turn) return `User: ${(turn as vscode.ChatRequestTurn).prompt}`;
        const responseTurn = turn as vscode.ChatResponseTurn;
        const parts = responseTurn.response
          .map((r) => (r instanceof (vscode as any).ChatResponseMarkdownPart ? String((r as any).value?.value ?? "") : ""))
          .filter(Boolean);
        return parts.length ? `Assistant: ${parts.join(" ")}` : "";
      })
      .filter(Boolean)
      .slice(-10);
  } catch {
    return [];
  }
}
