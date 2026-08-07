import * as vscode from "vscode";
import { PromptShieldSettings } from "./settings";
import { PromptShieldApi, siteLabelFor } from "./api";
import { Logger } from "./utils/logger";
import { FileScanner } from "./scanner";
import { PromptInterceptor } from "./interceptor";
import { StatusBarController } from "./ui/statusBar";
import { ScanHistoryTreeProvider } from "./ui/activityBarProvider";
import { RiskPanel } from "./ui/riskPanel";
import { ScanHistoryStore } from "./services/scanHistoryStore";
import { AuditQueueService } from "./services/auditQueueService";
import { PolicyCacheService } from "./services/policyCacheService";
import { WorkspaceMonitorService } from "./services/workspaceMonitorService";
import { isSupportedExtension } from "./utils/fileTypeUtils";

let logger: Logger;
let statusBar: StatusBarController;
let workspaceMonitor: WorkspaceMonitorService | undefined;
let auditQueue: AuditQueueService;
let riskPanel: RiskPanel;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  logger = new Logger("PromptShield");
  context.subscriptions.push({ dispose: () => logger.dispose() });

  const settings = new PromptShieldSettings(context.secrets);
  logger.setDebugEnabled(settings.debugMode);

  const api = new PromptShieldApi(settings, logger);
  const scanner = new FileScanner(settings, logger);
  const history = new ScanHistoryStore(context.globalState, settings);
  auditQueue = new AuditQueueService(context.globalState, api, logger);
  const policyCache = new PolicyCacheService(api, logger);

  statusBar = new StatusBarController();
  context.subscriptions.push(statusBar);

  const treeProvider = new ScanHistoryTreeProvider();
  treeProvider.setEntries(history.getAll());
  context.subscriptions.push(vscode.window.registerTreeDataProvider("promptshield.scanHistory", treeProvider));

  riskPanel = new RiskPanel(context.extensionUri);
  context.subscriptions.push({ dispose: () => riskPanel.dispose() });

  const interceptor = new PromptInterceptor(api, settings, logger, statusBar, history, auditQueue);

  // Chat participant (@promptshield)
  const participant = interceptor.registerChatParticipant(context);
  if (participant) context.subscriptions.push(participant);

  // ---- Connection/auth state on startup ----
  await refreshConnectionState(api, settings, logger);

  // ---- Workspace monitoring (optional) ----
  workspaceMonitor = new WorkspaceMonitorService(settings, api, scanner, logger, (_uri, count) => {
    if (count > 0) treeProvider.refresh();
  });
  context.subscriptions.push(workspaceMonitor);
  if (settings.enableWorkspaceScan) workspaceMonitor.start();

  context.subscriptions.push(
    settings.onDidChange(async () => {
      logger.setDebugEnabled(settings.debugMode);
      api.backend.refreshBaseUrl();
      if (settings.enableWorkspaceScan) workspaceMonitor?.start();
      else workspaceMonitor?.stop();
      await refreshConnectionState(api, settings, logger);
    })
  );

  // ---- Periodic connection re-check (also flushes the audit queue) ----
  const healthTimer = setInterval(() => {
    void refreshConnectionState(api, settings, logger);
    auditQueue.scheduleFlush(0);
  }, 60_000);
  context.subscriptions.push({ dispose: () => clearInterval(healthTimer) });

  // ---- Commands ----
  context.subscriptions.push(
    vscode.commands.registerCommand("promptshield.login", () => loginCommand(api, logger)),
    vscode.commands.registerCommand("promptshield.logout", () => logoutCommand(api, logger)),
    vscode.commands.registerCommand("promptshield.scanSelection", () => interceptor.scanSelectionCommand()),
    vscode.commands.registerCommand("promptshield.scanClipboardPrompt", () => interceptor.scanClipboardCommand()),
    vscode.commands.registerCommand("promptshield.interceptAndSend", () => interceptor.interceptAndSendCommand()),
    vscode.commands.registerCommand("promptshield.scanActiveFile", () => scanActiveFileCommand(api, scanner, treeProvider, history)),
    vscode.commands.registerCommand("promptshield.scanWorkspace", () => scanWorkspaceCommand(api, scanner, settings, treeProvider, history)),
    vscode.commands.registerCommand("promptshield.showOutputChannel", () => logger.show()),
    vscode.commands.registerCommand("promptshield.clearScanHistory", async () => {
      await history.clear();
      treeProvider.setEntries([]);
      void vscode.window.showInformationMessage("PromptShield: scan history cleared.");
    }),
    vscode.commands.registerCommand("promptshield.syncPolicies", async () => {
      const policies = await policyCache.refresh(true);
      void vscode.window.showInformationMessage(`PromptShield: synced ${policies.length} enabled polic${policies.length === 1 ? "y" : "ies"}.`);
    }),
    vscode.commands.registerCommand("promptshield.refreshTreeView", () => treeProvider.setEntries(history.getAll())),
    vscode.commands.registerCommand("promptshield.showRiskPanel", async () => {
      await policyCache.refresh();
      const online = await api.checkHealth();
      riskPanel.show({
        connection: { online, lastCheckedAt: Date.now() },
        policies: policyCache.get(),
        history: history.getAll(),
        authenticated: await api.isAuthenticated(),
        backendUrl: settings.backendUrl,
      });
    })
  );

  logger.info("PromptShield extension activated.");
}

export function deactivate(): void {
  workspaceMonitor?.dispose();
  auditQueue?.dispose();
  logger?.info("PromptShield extension deactivated.");
}

async function refreshConnectionState(api: PromptShieldApi, settings: PromptShieldSettings, log: Logger): Promise<void> {
  statusBar.setConnection("checking");
  const authenticated = await api.isAuthenticated();
  if (!authenticated) {
    statusBar.setConnection("unauthenticated");
    return;
  }
  try {
    const online = await api.checkHealth();
    statusBar.setConnection(online ? "connected" : "disconnected");
  } catch (err) {
    log.debug("Connection check failed", err instanceof Error ? err.message : err);
    statusBar.setConnection("disconnected");
  }
}

async function loginCommand(api: PromptShieldApi, log: Logger): Promise<void> {
  const email = await vscode.window.showInputBox({ prompt: "PromptShield: email", ignoreFocusOut: true });
  if (!email) return;
  const password = await vscode.window.showInputBox({
    prompt: "PromptShield: password",
    password: true,
    ignoreFocusOut: true,
  });
  if (!password) return;
  try {
    await api.login(email, password);
    statusBar.setConnection("connected");
    void vscode.window.showInformationMessage("PromptShield: signed in.");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    log.error("Login failed", message);
    void vscode.window.showErrorMessage(`PromptShield: sign in failed - ${message}`);
    statusBar.setConnection("unauthenticated");
  }
}

async function logoutCommand(api: PromptShieldApi, log: Logger): Promise<void> {
  await api.logout();
  statusBar.setConnection("unauthenticated");
  log.info("Signed out via command.");
  void vscode.window.showInformationMessage("PromptShield: signed out.");
}

async function scanActiveFileCommand(
  api: PromptShieldApi,
  scanner: FileScanner,
  treeProvider: ScanHistoryTreeProvider,
  history: ScanHistoryStore
): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    void vscode.window.showInformationMessage("PromptShield: no active file.");
    return;
  }
  const uri = editor.document.uri;
  if (!isSupportedExtension(uri.fsPath)) {
    void vscode.window.showInformationMessage("PromptShield: this file type is not supported for scanning.");
    return;
  }
  const extraction = await scanner.extractFromUri(uri);
  if (!extraction.ok || !extraction.payload) {
    void vscode.window.showWarningMessage(`PromptShield: ${extraction.skippedReason ?? "could not extract file content."}`);
    return;
  }
  const site = siteLabelFor({ workspaceName: vscode.workspace.name });
  const { result } = await api.scanWithFailureMode("", site, [extraction.payload]);
  await history.record(site, result, "");
  treeProvider.setEntries(history.getAll());
  void vscode.window.showInformationMessage(
    `PromptShield scanned ${extraction.payload.filename}: ${result.decision} (${result.reason})`
  );
}

async function scanWorkspaceCommand(
  api: PromptShieldApi,
  scanner: FileScanner,
  settings: PromptShieldSettings,
  treeProvider: ScanHistoryTreeProvider,
  history: ScanHistoryStore
): Promise<void> {
  const files = await vscode.workspace.findFiles("**/*", "**/node_modules/**", 200);
  const supported = files.filter((f) => isSupportedExtension(f.fsPath));
  if (supported.length === 0) {
    void vscode.window.showInformationMessage("PromptShield: no supported files found in workspace.");
    return;
  }

  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: "PromptShield: scanning workspace files", cancellable: true },
    async (progress, token) => {
      let scanned = 0;
      let flagged = 0;
      const site = siteLabelFor({ workspaceName: vscode.workspace.name });
      for (const uri of supported) {
        if (token.isCancellationRequested) break;
        progress.report({ message: `${scanned + 1}/${supported.length}`, increment: 100 / supported.length });
        const extraction = await scanner.extractFromUri(uri);
        scanned++;
        if (!extraction.ok || !extraction.payload) continue;
        try {
          const { result } = await api.scanWithFailureMode("", site, [extraction.payload]);
          if (result.decision !== "ALLOW") flagged++;
          await history.record(site, result, "");
        } catch {
          // best-effort; continue scanning remaining files
        }
      }
      treeProvider.setEntries(history.getAll());
      void vscode.window.showInformationMessage(
        `PromptShield: scanned ${scanned} file(s), ${flagged} flagged (WARN/REDACT/BLOCK). See the Recent Scans view for details.`
      );
    }
  );

  void settings; // reserved for future workspace-scan-specific settings
}
