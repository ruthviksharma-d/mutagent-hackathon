import * as vscode from "vscode";
import type { ScanHistoryEntry } from "../types";

/**
 * Tree View data provider for the Activity Bar's "Recent Scans &
 * Findings" panel. Backed by the persisted scan history
 * (context.globalState via ScanHistoryStore below) - not live network
 * data - so it renders instantly and works offline.
 */
export class ScanHistoryTreeProvider implements vscode.TreeDataProvider<HistoryTreeItem> {
  private readonly _onDidChangeTreeData = new vscode.EventEmitter<HistoryTreeItem | undefined | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private entries: ScanHistoryEntry[] = [];

  setEntries(entries: ScanHistoryEntry[]): void {
    this.entries = entries;
    this._onDidChangeTreeData.fire();
  }

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: HistoryTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: HistoryTreeItem): HistoryTreeItem[] {
    if (element) {
      return element.children ?? [];
    }
    if (this.entries.length === 0) {
      const empty = new HistoryTreeItem("No scans yet", vscode.TreeItemCollapsibleState.None);
      empty.description = "Run 'PromptShield: Scan Selected Text' to get started";
      return [empty];
    }
    return this.entries.map((entry) => {
      const label = `${entry.decision} · ${entry.site}`;
      const item = new HistoryTreeItem(label, vscode.TreeItemCollapsibleState.Collapsed);
      item.description = new Date(entry.timestamp).toLocaleTimeString();
      item.tooltip = `${entry.reason}\nRisk: ${entry.risk} · Score: ${entry.score}`;
      item.iconPath = new vscode.ThemeIcon(iconFor(entry.decision));
      item.children = [
        leaf(`Reason: ${entry.reason}`),
        leaf(`Risk: ${entry.risk} (score ${entry.score})`),
        leaf(`Findings: ${entry.findingCount} prompt / ${entry.fileFindingCount} file`),
        ...(entry.rawPromptPreview ? [leaf(`Preview: ${entry.rawPromptPreview}`)] : []),
      ];
      return item;
    });
  }
}

function leaf(label: string): HistoryTreeItem {
  return new HistoryTreeItem(label, vscode.TreeItemCollapsibleState.None);
}

function iconFor(decision: string): string {
  switch (decision) {
    case "ALLOW":
      return "check";
    case "WARN":
      return "warning";
    case "REDACT":
      return "eye-closed";
    case "BLOCK":
      return "circle-slash";
    default:
      return "circle-outline";
  }
}

export class HistoryTreeItem extends vscode.TreeItem {
  children?: HistoryTreeItem[];
  constructor(label: string, collapsibleState: vscode.TreeItemCollapsibleState) {
    super(label, collapsibleState);
  }
}
