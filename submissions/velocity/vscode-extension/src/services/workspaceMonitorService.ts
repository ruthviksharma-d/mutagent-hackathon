import * as vscode from "vscode";
import * as crypto from "crypto";
import type { PromptShieldSettings } from "../settings";
import type { PromptShieldApi } from "../api";
import type { FileScanner } from "../scanner";
import type { Logger } from "../utils/logger";
import { DiagnosticsProvider } from "../providers/diagnosticsProvider";
import { KeyedDebouncer } from "../utils/debounce";
import { isSupportedExtension } from "../utils/fileTypeUtils";
import { siteLabelFor } from "../api";

const DEBOUNCE_MS = 1500;

/**
 * Optional background scanning of opened/saved/newly-added workspace
 * files. Debounced per-file, skips unchanged files (content-hash cache),
 * never blocks the UI thread (all work is awaited inside async event
 * handlers that VS Code already runs off the render path), and only runs
 * at all when `promptshield.enableWorkspaceScan` is true.
 */
export class WorkspaceMonitorService implements vscode.Disposable {
  private readonly debouncer = new KeyedDebouncer(DEBOUNCE_MS);
  private readonly lastHash = new Map<string, string>();
  private readonly diagnostics = new DiagnosticsProvider();
  private watcher: vscode.FileSystemWatcher | undefined;
  private disposables: vscode.Disposable[] = [];
  private running = false;

  constructor(
    private readonly settings: PromptShieldSettings,
    private readonly api: PromptShieldApi,
    private readonly scanner: FileScanner,
    private readonly logger: Logger,
    private readonly onScanned?: (uri: vscode.Uri, findingCount: number) => void
  ) {}

  start(): void {
    if (this.running) return;
    this.running = true;

    this.disposables.push(
      vscode.workspace.onDidOpenTextDocument((doc) => this.queueScan(doc.uri)),
      vscode.workspace.onDidSaveTextDocument((doc) => this.queueScan(doc.uri))
    );

    this.watcher = vscode.workspace.createFileSystemWatcher("**/*");
    this.disposables.push(
      this.watcher,
      this.watcher.onDidCreate((uri) => this.queueScan(uri)),
      this.watcher.onDidChange((uri) => this.queueScan(uri)),
      this.watcher.onDidDelete((uri) => {
        this.lastHash.delete(uri.toString());
        this.diagnostics.clear(uri);
      })
    );

    this.logger.info("Workspace monitoring started.");
  }

  stop(): void {
    if (!this.running) return;
    this.running = false;
    for (const d of this.disposables) d.dispose();
    this.disposables = [];
    this.watcher = undefined;
    this.diagnostics.clearAll();
    this.logger.info("Workspace monitoring stopped.");
  }

  private queueScan(uri: vscode.Uri): void {
    if (!this.settings.enableWorkspaceScan) return;
    if (uri.scheme !== "file") return;
    if (!isSupportedExtension(uri.fsPath)) return;
    this.debouncer.run(uri.toString(), () => {
      void this.scanFile(uri);
    });
  }

  private async scanFile(uri: vscode.Uri): Promise<void> {
    try {
      const bytes = await vscode.workspace.fs.readFile(uri);
      const hash = crypto.createHash("sha256").update(bytes).digest("hex");
      const key = uri.toString();
      if (this.lastHash.get(key) === hash) {
        return; // unchanged since last scan
      }
      this.lastHash.set(key, hash);

      const extraction = await this.scanner.extractFromUri(uri);
      if (!extraction.ok || !extraction.payload) {
        this.logger.debug(`Workspace scan skipped ${uri.fsPath}: ${extraction.skippedReason}`);
        return;
      }

      const site = siteLabelFor({ workspaceName: vscode.workspace.name });
      const { result } = await this.api.scanWithFailureMode("", site, [extraction.payload]);
      const fileFindings = result.file_findings ?? [];
      this.diagnostics.setFindingsForFile(uri, fileFindings, result.reason);
      this.onScanned?.(uri, fileFindings.length);
    } catch (err) {
      this.logger.warn(`Workspace scan failed for ${uri.fsPath}`, err instanceof Error ? err.message : err);
    }
  }

  dispose(): void {
    this.stop();
    this.debouncer.dispose();
    this.diagnostics.dispose();
  }
}
