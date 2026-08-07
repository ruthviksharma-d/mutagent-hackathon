import * as vscode from "vscode";
import type { FailureMode } from "./types";

const SECTION = "promptshield";
const SECRET_TOKEN_KEY = "promptshield.apiToken";
const SECRET_APIKEY_KEY = "promptshield.apiKey";

/**
 * Typed accessor over `vscode.workspace.getConfiguration("promptshield")`
 * plus a thin wrapper around `vscode.SecretStorage` for anything
 * sensitive (API key, JWT access token). Nothing sensitive is ever read
 * from or written to settings.json - only SecretStorage.
 */
export class PromptShieldSettings {
  constructor(private readonly secrets: vscode.SecretStorage) {}

  private cfg(): vscode.WorkspaceConfiguration {
    return vscode.workspace.getConfiguration(SECTION);
  }

  get backendUrl(): string {
    const raw = this.cfg().get<string>("backendUrl", "http://localhost:8000");
    return raw.replace(/\/+$/, "");
  }

  get organizationId(): string {
    return this.cfg().get<string>("organizationId", "");
  }

  get enableWorkspaceScan(): boolean {
    return this.cfg().get<boolean>("enableWorkspaceScan", false);
  }

  get enableFileScan(): boolean {
    return this.cfg().get<boolean>("enableFileScan", true);
  }

  get enablePromptScan(): boolean {
    return this.cfg().get<boolean>("enablePromptScan", true);
  }

  get enableConversationContext(): boolean {
    return this.cfg().get<boolean>("enableConversationContext", true);
  }

  get maxFileSizeKb(): number {
    return this.cfg().get<number>("maxFileSizeKb", 2048);
  }

  get autoRedaction(): boolean {
    return this.cfg().get<boolean>("autoRedaction", true);
  }

  get strictMode(): boolean {
    return this.cfg().get<boolean>("strictMode", false);
  }

  get telemetry(): boolean {
    return this.cfg().get<boolean>("telemetry", false);
  }

  get debugMode(): boolean {
    return this.cfg().get<boolean>("debugMode", false);
  }

  get failureMode(): FailureMode {
    return this.cfg().get<FailureMode>("failureMode", "open");
  }

  onDidChange(listener: (e: vscode.ConfigurationChangeEvent) => void): vscode.Disposable {
    return vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration(SECTION)) listener(e);
    });
  }

  // ---- SecretStorage-backed values ----

  async getApiKey(): Promise<string | undefined> {
    return this.secrets.get(SECRET_APIKEY_KEY);
  }

  async setApiKey(value: string): Promise<void> {
    await this.secrets.store(SECRET_APIKEY_KEY, value);
  }

  async clearApiKey(): Promise<void> {
    await this.secrets.delete(SECRET_APIKEY_KEY);
  }

  async getAccessToken(): Promise<string | undefined> {
    return this.secrets.get(SECRET_TOKEN_KEY);
  }

  async setAccessToken(value: string): Promise<void> {
    await this.secrets.store(SECRET_TOKEN_KEY, value);
  }

  async clearAccessToken(): Promise<void> {
    await this.secrets.delete(SECRET_TOKEN_KEY);
  }
}
