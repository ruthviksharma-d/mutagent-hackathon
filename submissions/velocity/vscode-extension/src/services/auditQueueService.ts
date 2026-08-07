import * as vscode from "vscode";
import type { PromptShieldApi } from "../api";
import type { Logger } from "../utils/logger";
import type { QueuedAuditEvent, ScanRequestBody, Decision } from "../types";

const QUEUE_KEY = "promptshield.auditQueue";
const MAX_QUEUE_SIZE = 200;
const MAX_ATTEMPTS = 8;
const BASE_RETRY_DELAY_MS = 5_000;
const MAX_RETRY_DELAY_MS = 5 * 60_000;

/**
 * Locally queues scan requests that couldn't reach the backend (so the
 * server-side audit trail - AuditLog rows written by services/audit_service.py
 * on every successful /api/scan call - eventually catches up once
 * connectivity is restored). Persisted in `context.globalState` (not a
 * plaintext file) and retried with exponential backoff. Only metadata
 * needed to resubmit the same scan is stored; nothing extra is logged.
 */
export class AuditQueueService {
  private queue: QueuedAuditEvent[] = [];
  private flushTimer: ReturnType<typeof setTimeout> | undefined;
  private flushing = false;

  constructor(
    private readonly state: vscode.Memento,
    private readonly api: PromptShieldApi,
    private readonly logger: Logger
  ) {
    this.queue = this.state.get<QueuedAuditEvent[]>(QUEUE_KEY, []);
  }

  get pendingCount(): number {
    return this.queue.length;
  }

  async enqueue(body: ScanRequestBody, localDecision: Decision): Promise<void> {
    const event: QueuedAuditEvent = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      createdAt: Date.now(),
      attempts: 0,
      nextAttemptAt: Date.now(),
      body,
      localDecision,
    };
    this.queue.push(event);
    if (this.queue.length > MAX_QUEUE_SIZE) {
      this.queue = this.queue.slice(this.queue.length - MAX_QUEUE_SIZE);
    }
    await this.persist();
    this.scheduleFlush(BASE_RETRY_DELAY_MS);
  }

  scheduleFlush(delayMs = BASE_RETRY_DELAY_MS): void {
    if (this.flushTimer) clearTimeout(this.flushTimer);
    this.flushTimer = setTimeout(() => void this.flush(), delayMs);
  }

  async flush(): Promise<void> {
    if (this.flushing || this.queue.length === 0) return;
    this.flushing = true;
    try {
      const now = Date.now();
      const remaining: QueuedAuditEvent[] = [];
      for (const event of this.queue) {
        if (event.nextAttemptAt > now) {
          remaining.push(event);
          continue;
        }
        try {
          await this.api.backend.scan(event.body);
          this.logger.info(`Flushed queued audit event ${event.id} to backend.`);
        } catch {
          event.attempts += 1;
          if (event.attempts < MAX_ATTEMPTS) {
            const delay = Math.min(BASE_RETRY_DELAY_MS * 2 ** event.attempts, MAX_RETRY_DELAY_MS);
            event.nextAttemptAt = Date.now() + delay;
            remaining.push(event);
          } else {
            this.logger.warn(`Dropping queued audit event ${event.id} after ${event.attempts} failed attempts.`);
          }
        }
      }
      this.queue = remaining;
      await this.persist();
    } finally {
      this.flushing = false;
      if (this.queue.length > 0) {
        this.scheduleFlush(MAX_RETRY_DELAY_MS / 4);
      }
    }
  }

  private async persist(): Promise<void> {
    await this.state.update(QUEUE_KEY, this.queue);
  }

  dispose(): void {
    if (this.flushTimer) clearTimeout(this.flushTimer);
  }
}
