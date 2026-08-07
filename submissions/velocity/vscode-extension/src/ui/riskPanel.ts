import * as vscode from "vscode";
import type { ScanHistoryEntry, PolicySummaryItem, BackendConnectionState } from "../types";

/** Settings/risk-summary webview panel: shows connection state, enabled
 * policies (from the cached summary), and recent scan history at a glance. */
export class RiskPanel {
  private panel: vscode.WebviewPanel | undefined;

  constructor(private readonly extensionUri: vscode.Uri) {}

  show(data: {
    connection: BackendConnectionState;
    policies: PolicySummaryItem[];
    history: ScanHistoryEntry[];
    authenticated: boolean;
    backendUrl: string;
  }): void {
    if (!this.panel) {
      this.panel = vscode.window.createWebviewPanel(
        "promptshieldRiskPanel",
        "PromptShield Risk Summary",
        vscode.ViewColumn.Beside,
        { enableScripts: false, retainContextWhenHidden: true }
      );
      this.panel.onDidDispose(() => {
        this.panel = undefined;
      });
    }
    this.panel.webview.html = render(data);
    this.panel.reveal(vscode.ViewColumn.Beside, true);
  }

  dispose(): void {
    this.panel?.dispose();
  }
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function render(data: {
  connection: BackendConnectionState;
  policies: PolicySummaryItem[];
  history: ScanHistoryEntry[];
  authenticated: boolean;
  backendUrl: string;
}): string {
  const connBadge = data.connection.online
    ? `<span class="badge ok">ONLINE</span>`
    : `<span class="badge bad">OFFLINE</span>`;
  const authBadge = data.authenticated
    ? `<span class="badge ok">SIGNED IN</span>`
    : `<span class="badge warn">NOT SIGNED IN</span>`;

  const policyRows = data.policies.length
    ? data.policies
        .map(
          (p) =>
            `<tr><td>${esc(p.name)}</td><td>${esc(p.detection_type)}</td><td><span class="badge ${badgeClass(p.action)}">${esc(p.action)}</span></td><td>${p.priority}</td></tr>`
        )
        .join("")
    : `<tr><td colspan="4">No enabled policies returned (or not yet synced).</td></tr>`;

  const historyRows = data.history.length
    ? data.history
        .slice(0, 20)
        .map(
          (h) =>
            `<tr><td>${new Date(h.timestamp).toLocaleString()}</td><td>${esc(h.site)}</td><td><span class="badge ${badgeClass(h.decision)}">${esc(h.decision)}</span></td><td>${esc(h.risk)}</td><td>${h.score}</td><td>${esc(h.reason)}</td></tr>`
        )
        .join("")
    : `<tr><td colspan="6">No scans recorded yet.</td></tr>`;

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<style>
  body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); padding: 16px; }
  h1 { font-size: 1.3em; }
  h2 { font-size: 1.05em; margin-top: 24px; }
  table { border-collapse: collapse; width: 100%; margin-top: 8px; }
  td, th { border: 1px solid var(--vscode-panel-border); padding: 4px 8px; text-align: left; font-size: 0.9em; }
  .badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 600; }
  .badge.ok { background: #1e7e34; color: white; }
  .badge.bad { background: #a71d2a; color: white; }
  .badge.warn { background: #b58a00; color: white; }
  .meta { opacity: 0.8; font-size: 0.85em; }
</style>
</head>
<body>
  <h1>PromptShield Risk Summary</h1>
  <p>${connBadge} ${authBadge} <span class="meta">Backend: ${esc(data.backendUrl)}</span></p>
  <p class="meta">Last checked: ${data.connection.lastCheckedAt ? new Date(data.connection.lastCheckedAt).toLocaleString() : "never"}${data.connection.lastError ? ` - ${esc(data.connection.lastError)}` : ""}</p>

  <h2>Enabled Policies (cached, display only)</h2>
  <table>
    <tr><th>Name</th><th>Detector</th><th>Action</th><th>Priority</th></tr>
    ${policyRows}
  </table>

  <h2>Recent Scans</h2>
  <table>
    <tr><th>Time</th><th>Site</th><th>Decision</th><th>Risk</th><th>Score</th><th>Reason</th></tr>
    ${historyRows}
  </table>
</body>
</html>`;
}

function badgeClass(decision: string): string {
  if (decision === "BLOCK") return "bad";
  if (decision === "WARN" || decision === "REDACT") return "warn";
  return "ok";
}
