import axios, { AxiosInstance, AxiosError } from "axios";
import type {
  LoginResponse,
  PolicySummaryResponse,
  ScanRequestBody,
  ScanResult,
} from "./types";
import type { PromptShieldSettings } from "./settings";
import type { Logger } from "./utils/logger";

/** Thrown for a 401 from a token-bearing call, mirroring the browser
 * extension's ScanUnauthorizedError (services/api.ts) so callers can tell
 * "session expired" apart from "backend unreachable" or "malformed request". */
export class UnauthorizedError extends Error {
  constructor() {
    super("Session expired or invalid. Please sign in again.");
    this.name = "UnauthorizedError";
  }
}

export class BackendUnreachableError extends Error {
  constructor(cause?: unknown) {
    super(`PromptShield backend is unreachable: ${cause instanceof Error ? cause.message : String(cause ?? "")}`);
    this.name = "BackendUnreachableError";
  }
}

/**
 * Low-level HTTP client to the PromptShield backend. Mirrors the request
 * shapes used by browser-extension/src/services/api.ts (same JSON body
 * field names, same endpoints) so this client is a drop-in fourth caller
 * of an unmodified backend contract.
 */
export class BackendClient {
  private client: AxiosInstance;

  constructor(
    private readonly settings: PromptShieldSettings,
    private readonly logger: Logger
  ) {
    this.client = axios.create({ baseURL: this.settings.backendUrl, timeout: 15000 });
  }

  /** Call after backendUrl setting changes so subsequent requests use the new base URL. */
  refreshBaseUrl(): void {
    this.client = axios.create({ baseURL: this.settings.backendUrl, timeout: 15000 });
  }

  private async authHeaders(): Promise<Record<string, string>> {
    const token = await this.settings.getAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const org = this.settings.organizationId;
    if (org) headers["X-Organization-Id"] = org;
    return headers;
  }

  async health(): Promise<boolean> {
    try {
      const res = await this.client.get("/api/health", { timeout: 5000 });
      return res.status === 200;
    } catch (err) {
      this.logger.debug("Health check failed", err instanceof Error ? err.message : err);
      return false;
    }
  }

  async login(email: string, password: string): Promise<LoginResponse> {
    try {
      const res = await this.client.post<LoginResponse>("/api/auth/login", { email, password });
      return res.data;
    } catch (err) {
      throw this.translateError(err);
    }
  }

  async fetchCurrentUser(): Promise<LoginResponse["user"]> {
    try {
      const res = await this.client.get("/api/auth/me", { headers: await this.authHeaders() });
      return res.data;
    } catch (err) {
      if (isAxiosStatus(err, 401)) throw new UnauthorizedError();
      throw this.translateError(err);
    }
  }

  /**
   * POST /api/scan - identical endpoint and body shape used by the
   * browser extension. Retries transient network failures (3 attempts,
   * exponential backoff) before giving up, same as
   * browser-extension/src/services/api.ts fetchWithRetry. A response the
   * server actually returned (including 4xx) is never retried.
   */
  async scan(body: ScanRequestBody, attempts = 3, baseDelayMs = 400): Promise<ScanResult> {
    const headers = { ...(await this.authHeaders()), "Content-Type": "application/json" };
    const timeout = body.files && body.files.length > 0 ? 30000 : 15000;

    let lastErr: unknown;
    for (let attempt = 0; attempt < attempts; attempt++) {
      try {
        const res = await this.client.post<ScanResult>("/api/scan", body, { headers, timeout });
        return res.data;
      } catch (err) {
        if (isAxiosStatus(err, 401)) throw new UnauthorizedError();
        if (isAxiosResponseError(err)) {
          // Server responded (4xx/5xx) - do not retry, surface as-is.
          throw this.translateError(err);
        }
        lastErr = err;
        if (attempt < attempts - 1) {
          await sleep(baseDelayMs * 2 ** attempt);
        }
      }
    }
    throw new BackendUnreachableError(lastErr);
  }

  async fetchPolicySummary(): Promise<PolicySummaryResponse> {
    try {
      const res = await this.client.get<PolicySummaryResponse>("/api/policies/summary", {
        headers: await this.authHeaders(),
      });
      return res.data;
    } catch (err) {
      if (isAxiosStatus(err, 401)) throw new UnauthorizedError();
      throw this.translateError(err);
    }
  }

  private translateError(err: unknown): Error {
    if (isAxiosResponseError(err)) {
      const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
      return new Error(detail ?? `Request failed with status ${err.response?.status}`);
    }
    return new BackendUnreachableError(err);
  }
}

function isAxiosResponseError(err: unknown): err is AxiosError {
  return axios.isAxiosError(err) && err.response !== undefined;
}

function isAxiosStatus(err: unknown, status: number): boolean {
  return axios.isAxiosError(err) && err.response?.status === status;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
