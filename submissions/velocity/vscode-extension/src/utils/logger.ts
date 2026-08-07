import * as vscode from "vscode";

/**
 * Patterns for common secret/PII shapes so the Output Channel never leaks
 * anything sensitive even in debugMode. This is a defensive, best-effort
 * client-side scrub for LOGGING ONLY - it is NOT the security boundary
 * (that's the backend's detection pipeline) and must never be treated as
 * one.
 */
const SANITIZE_PATTERNS: RegExp[] = [
  /sk-[a-zA-Z0-9]{20,}/g, // OpenAI-style API keys
  /ghp_[a-zA-Z0-9]{20,}/g, // GitHub tokens
  /AKIA[0-9A-Z]{16}/g, // AWS access key ids
  /eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}/g, // JWTs
  /Bearer\s+[a-zA-Z0-9._-]{10,}/gi,
  /\b\d{3}-\d{2}-\d{4}\b/g, // SSN-like
  /\b(?:\d[ -]*?){13,16}\b/g, // credit-card-like digit runs
  /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, // emails
  /"?(password|passwd|secret|api[_-]?key|token)"?\s*[:=]\s*"?[^\s,"]{4,}"?/gi,
];

export function sanitizeForLog(input: string): string {
  let out = input;
  for (const pattern of SANITIZE_PATTERNS) {
    out = out.replace(pattern, "[REDACTED]");
  }
  return out;
}

export type LogLevel = "info" | "warn" | "error" | "debug";

export class Logger {
  private readonly channel: vscode.OutputChannel;
  private debugEnabled = false;

  constructor(name = "PromptShield") {
    this.channel = vscode.window.createOutputChannel(name);
  }

  setDebugEnabled(enabled: boolean): void {
    this.debugEnabled = enabled;
  }

  private write(level: LogLevel, message: string, extra?: unknown): void {
    if (level === "debug" && !this.debugEnabled) return;
    const ts = new Date().toISOString();
    let line = `[${ts}] [${level.toUpperCase()}] ${sanitizeForLog(message)}`;
    if (extra !== undefined) {
      const extraStr = typeof extra === "string" ? extra : safeStringify(extra);
      line += ` ${sanitizeForLog(extraStr)}`;
    }
    this.channel.appendLine(line);
  }

  info(message: string, extra?: unknown): void {
    this.write("info", message, extra);
  }

  warn(message: string, extra?: unknown): void {
    this.write("warn", message, extra);
  }

  error(message: string, extra?: unknown): void {
    this.write("error", message, extra);
  }

  debug(message: string, extra?: unknown): void {
    this.write("debug", message, extra);
  }

  show(): void {
    this.channel.show(true);
  }

  dispose(): void {
    this.channel.dispose();
  }
}

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
