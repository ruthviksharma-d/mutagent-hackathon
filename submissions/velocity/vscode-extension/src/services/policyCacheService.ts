import type { PromptShieldApi } from "../api";
import type { Logger } from "../utils/logger";
import type { PolicySummaryItem } from "../types";

const DEFAULT_TTL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * In-memory cache of the (display-only) policy summary, with a TTL so
 * that showing policy info in the risk panel/status bar doesn't hit the
 * network on every render. This never influences ALLOW/WARN/REDACT/BLOCK
 * decisions - those always come fresh from POST /api/scan - it's purely
 * for the "what's currently enforced" display surfaces.
 */
export class PolicyCacheService {
  private cached: PolicySummaryItem[] = [];
  private lastFetchedAt = 0;
  private inFlight: Promise<PolicySummaryItem[]> | null = null;

  constructor(
    private readonly api: PromptShieldApi,
    private readonly logger: Logger,
    private readonly ttlMs = DEFAULT_TTL_MS
  ) {}

  get(): PolicySummaryItem[] {
    return this.cached;
  }

  get lastSynced(): number {
    return this.lastFetchedAt;
  }

  async refresh(force = false): Promise<PolicySummaryItem[]> {
    const isFresh = Date.now() - this.lastFetchedAt < this.ttlMs;
    if (!force && isFresh) return this.cached;
    if (this.inFlight) return this.inFlight;

    this.inFlight = this.api
      .syncPolicySummary()
      .then((res) => {
        this.cached = res.policies;
        this.lastFetchedAt = Date.now();
        this.logger.debug(`Policy summary synced: ${res.policies.length} enabled polic${res.policies.length === 1 ? "y" : "ies"}.`);
        return this.cached;
      })
      .catch((err) => {
        this.logger.debug("Policy summary sync failed (non-fatal)", err instanceof Error ? err.message : err);
        return this.cached;
      })
      .finally(() => {
        this.inFlight = null;
      });

    return this.inFlight;
  }
}
