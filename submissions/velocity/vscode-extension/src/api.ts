import { BackendClient, UnauthorizedError, BackendUnreachableError } from "./backend";
import type { PromptShieldSettings } from "./settings";
import type { Logger } from "./utils/logger";
import type {
  Decision,
  PromptContext,
  ScanFilePayload,
  ScanRequestBody,
  ScanResult,
} from "./types";

export { UnauthorizedError, BackendUnreachableError };

/**
 * Higher-level API surface the rest of the extension talks to. Wraps
 * BackendClient with auth-state management and a safe "scan with
 * failure-mode enforcement" helper - this is the ONLY place decisions are
 * made about what happens when the backend can't be reached; every real
 * ALLOW/WARN/REDACT/BLOCK verdict otherwise comes straight from the
 * backend's response, never computed locally.
 */
export class PromptShieldApi {
  readonly backend: BackendClient;

  constructor(
    private readonly settings: PromptShieldSettings,
    private readonly logger: Logger
  ) {
    this.backend = new BackendClient(settings, logger);
  }

  async isAuthenticated(): Promise<boolean> {
    const token = await this.settings.getAccessToken();
    return !!token;
  }

  async login(email: string, password: string): Promise<void> {
    const res = await this.backend.login(email, password);
    await this.settings.setAccessToken(res.access_token);
    this.logger.info(`Signed in as ${res.user.email} (${res.user.role}).`);
  }

  async logout(): Promise<void> {
    await this.settings.clearAccessToken();
    this.logger.info("Signed out.");
  }

  async checkHealth(): Promise<boolean> {
    return this.backend.health();
  }

  buildScanBody(promptText: string, site: string, files: ScanFilePayload[] = []): ScanRequestBody {
    return {
      prompt: promptText,
      site,
      ...(files.length > 0
        ? {
            files: files.map((f) => ({
              filename: f.filename,
              content_base64: f.contentBase64,
              mime_type: f.mimeType,
              size_bytes: f.sizeBytes,
            })),
          }
        : {}),
    };
  }

  /**
   * Scans a prompt (+ optional files). On success, returns the backend's
   * verdict verbatim. On backend-unreachable, applies the configured
   * failureMode: "open" synthesizes an ALLOW result (with a clear
   * `reason` flagging it as UNSCANNED so the UI never confuses this with
   * a real backend ALLOW), "closed" synthesizes a BLOCK. A real
   * server-sent error (e.g. validation 4xx) is surfaced as a thrown
   * error, never silently turned into ALLOW/BLOCK.
   */
  async scanWithFailureMode(
    promptText: string,
    site: string,
    files: ScanFilePayload[] = []
  ): Promise<{ result: ScanResult; wasBackendReachable: boolean }> {
    const body = this.buildScanBody(promptText, site, files);
    try {
      const result = await this.backend.scan(body);
      return { result, wasBackendReachable: true };
    } catch (err) {
      if (err instanceof UnauthorizedError) throw err;
      if (err instanceof BackendUnreachableError) {
        const failureMode = this.settings.failureMode;
        const decision: Decision = failureMode === "closed" ? "BLOCK" : "ALLOW";
        this.logger.warn(
          `Backend unreachable - applying failureMode="${failureMode}" -> ${decision} (unscanned).`
        );
        const result: ScanResult = {
          decision,
          risk: "NONE",
          score: 0,
          reason:
            failureMode === "closed"
              ? "PromptShield backend unreachable - blocked by failureMode=closed. This text was NOT scanned."
              : "PromptShield backend unreachable - allowed by failureMode=open. This text was NOT scanned.",
          sanitized_prompt: promptText,
          findings: [],
          file_findings: [],
        };
        return { result, wasBackendReachable: false };
      }
      throw err;
    }
  }

  async syncPolicySummary() {
    return this.backend.fetchPolicySummary();
  }
}

/** Builds the `site` string sent to the backend from available context -
 * the backend only ever sees a free-text label ("VS Code" / editor +
 * chat participant name), never a real "ChatGPT/Claude/Gemini" value
 * since this client doesn't intercept those sites' network traffic. */
export function siteLabelFor(context: Pick<PromptContext, "workspaceName">): string {
  return context.workspaceName ? `VS Code (${context.workspaceName})` : "VS Code";
}
