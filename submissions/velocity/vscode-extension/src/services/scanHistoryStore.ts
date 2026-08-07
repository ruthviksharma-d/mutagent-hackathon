import * as vscode from "vscode";
import type { ScanHistoryEntry, ScanResult } from "../types";
import type { PromptShieldSettings } from "../settings";

const HISTORY_KEY = "promptshield.scanHistory";
const MAX_ENTRIES = 100;

/**
 * Persists recent scan history (metadata only, never raw prompts unless
 * the user opts in via `promptshield.telemetry`) in `context.globalState`.
 */
export class ScanHistoryStore {
  private entries: ScanHistoryEntry[];

  constructor(
    private readonly state: vscode.Memento,
    private readonly settings: PromptShieldSettings
  ) {
    this.entries = this.state.get<ScanHistoryEntry[]>(HISTORY_KEY, []);
  }

  getAll(): ScanHistoryEntry[] {
    return this.entries;
  }

  async record(site: string, result: ScanResult, promptText: string): Promise<ScanHistoryEntry> {
    const entry: ScanHistoryEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: Date.now(),
      site,
      decision: result.decision,
      risk: result.risk,
      score: result.score,
      reason: result.reason,
      findingCount: result.findings?.length ?? 0,
      fileFindingCount: result.file_findings?.length ?? 0,
      ...(this.settings.telemetry
        ? { rawPromptPreview: promptText.slice(0, 200) }
        : {}),
    };
    this.entries = [entry, ...this.entries].slice(0, MAX_ENTRIES);
    await this.state.update(HISTORY_KEY, this.entries);
    return entry;
  }

  async clear(): Promise<void> {
    this.entries = [];
    await this.state.update(HISTORY_KEY, this.entries);
  }
}
