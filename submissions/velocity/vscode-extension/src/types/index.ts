/**
 * Shared TypeScript interfaces for the PromptShield VS Code extension.
 * Mirrors (does not duplicate the logic behind) the backend's
 * schemas/scan.py ScanRequest/ScanResponse and browser-extension's
 * src/types/messages.ts, so this client speaks the exact same wire
 * protocol as the existing browser extension and CLI.
 */

export type Decision = "ALLOW" | "WARN" | "REDACT" | "BLOCK";

export type Severity = "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Finding {
  detector: string;
  severity: Severity;
  score: number;
  reason: string;
}

export interface ScanFilePayload {
  filename: string;
  contentBase64: string;
  mimeType?: string;
  sizeBytes: number;
}

export interface FileFinding {
  filename: string;
  extension: string;
  category: string;
  size_bytes: number | null;
  mime_type: string | null;
  risk: Severity;
  score: number;
  action: Decision;
  reason: string;
  extracted: boolean;
  extraction_note: string | null;
}

/** Body sent to POST /api/scan - matches backend ScanRequest exactly. */
export interface ScanRequestBody {
  prompt: string;
  site: string;
  files?: {
    filename: string;
    content_base64: string;
    mime_type?: string;
    size_bytes?: number;
  }[];
}

/** Response from POST /api/scan - matches backend ScanResponse exactly. */
export interface ScanResult {
  decision: Decision;
  risk: Severity;
  score: number;
  reason: string;
  sanitized_prompt: string;
  findings: Finding[];
  file_findings?: FileFinding[];
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface PolicySummaryItem {
  name: string;
  detection_type: string;
  action: Decision;
  priority: number;
}

export interface PolicySummaryResponse {
  policies: PolicySummaryItem[];
}

/**
 * Extra context PromptShield's backend doesn't currently require but the
 * VS Code client captures anyway for local audit-trail / UX purposes
 * (shown in the risk panel, written to the sanitized output channel, and
 * used to build the effective `site` string). None of this is sent to
 * /api/scan beyond the existing `site`/`prompt`/`files` fields, since the
 * backend contract must stay exactly what browser-extension/cli rely on.
 */
export interface PromptContext {
  promptText: string;
  conversationHistory?: string[];
  selectedCode?: string;
  activeFileName?: string;
  languageId?: string;
  workspaceName?: string;
  workspaceId?: string;
  userEmail?: string;
  timestamp: number;
  site: string;
}

export interface ScanHistoryEntry {
  id: string;
  timestamp: number;
  site: string;
  decision: Decision;
  risk: Severity;
  score: number;
  reason: string;
  findingCount: number;
  fileFindingCount: number;
  /** Only populated when promptshield.telemetry is enabled by the user. */
  rawPromptPreview?: string;
}

export interface QueuedAuditEvent {
  id: string;
  createdAt: number;
  attempts: number;
  nextAttemptAt: number;
  body: ScanRequestBody;
  /** Decision made locally (fail-open/closed) while the backend was unreachable. */
  localDecision: Decision;
}

export interface BackendConnectionState {
  online: boolean;
  lastCheckedAt: number | null;
  lastError?: string;
}

export type FailureMode = "open" | "closed";

export interface SupportedFileKind {
  ext: string;
  kind: "text" | "pdf" | "docx" | "xlsx" | "csv";
}
