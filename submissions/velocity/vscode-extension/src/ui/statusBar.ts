import * as vscode from "vscode";
import type { Decision } from "../types";

export type ConnectionState = "connected" | "disconnected" | "unauthenticated" | "checking";

/**
 * Status bar item showing PromptShield's current connection state and the
 * most recent scan's risk/decision at a glance.
 */
export class StatusBarController {
  private readonly item: vscode.StatusBarItem;

  constructor() {
    this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    this.item.command = "promptshield.showRiskPanel";
    this.item.text = "$(shield) PromptShield";
    this.item.tooltip = "PromptShield: initializing...";
    this.item.show();
  }

  setConnection(state: ConnectionState): void {
    switch (state) {
      case "connected":
        this.item.text = "$(shield) PromptShield";
        this.item.tooltip = "PromptShield: connected to backend.";
        this.item.backgroundColor = undefined;
        break;
      case "checking":
        this.item.text = "$(sync~spin) PromptShield";
        this.item.tooltip = "PromptShield: checking backend connection...";
        this.item.backgroundColor = undefined;
        break;
      case "unauthenticated":
        this.item.text = "$(shield) PromptShield: sign in";
        this.item.tooltip = "PromptShield: not signed in. Run 'PromptShield: Sign In'.";
        this.item.command = "promptshield.login";
        this.item.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
        break;
      case "disconnected":
        this.item.text = "$(shield) PromptShield: offline";
        this.item.tooltip = "PromptShield: backend unreachable. failureMode setting determines behavior.";
        this.item.command = "promptshield.showRiskPanel";
        this.item.backgroundColor = new vscode.ThemeColor("statusBarItem.errorBackground");
        break;
    }
  }

  setLastDecision(decision: Decision, reason: string): void {
    const icon = iconFor(decision);
    this.item.text = `${icon} PromptShield: ${decision}`;
    this.item.tooltip = `PromptShield last scan: ${decision}\n${reason}`;
    this.item.backgroundColor =
      decision === "BLOCK"
        ? new vscode.ThemeColor("statusBarItem.errorBackground")
        : decision === "WARN"
          ? new vscode.ThemeColor("statusBarItem.warningBackground")
          : undefined;
  }

  dispose(): void {
    this.item.dispose();
  }
}

function iconFor(decision: Decision): string {
  switch (decision) {
    case "ALLOW":
      return "$(check)";
    case "WARN":
      return "$(warning)";
    case "REDACT":
      return "$(eye-closed)";
    case "BLOCK":
      return "$(circle-slash)";
  }
}
