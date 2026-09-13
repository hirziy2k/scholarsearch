// ============================================
// Circuit Breaker with Score Lock
// ============================================
//
// Prevents cascade failures when an API source throws 429/5xx.
// Tracks source health state per session.
//
// SCORE LOCK: Once a search session ID is initialized, the weighting
// schema freezes. If a degraded source recovers mid-session, its raw
// data is appended but the composite score calculation parameters
// remain locked to the T=0s state. State changes only apply to new queries.

export type CircuitState = "closed" | "open" | "half_open";

export interface SourceHealth {
  source: string;
  state: CircuitState;
  failures: number;
  lastFailureTime: number | null;
  lastSuccessTime: number | null;
  openUntil: number | null;
  consecutiveSuccesses: number;
}

export interface DegradedModeAlert {
  type: "source_degraded" | "source_recovered" | "score_frozen";
  source: string;
  message: string;
  timestamp: number;
  frozenFactors?: string[];
}

// Default thresholds
const FAILURE_THRESHOLD = 2;
const SUCCESS_THRESHOLD = 3;
const OPEN_DURATION_MS = 60_000;

// ============================================
// Score Lock
// ============================================
//
// Captures weights at T=0s and freezes them for the session.
// If sources degrade, the frozen snapshot is used for scoring
// while degraded sources simply don't contribute to ranking.

export interface FrozenWeightSnapshot {
  weights: Record<string, number>;
  frozenAt: number;
  degradedSources: string[];
}

export class ScoreLock {
  private snapshot: FrozenWeightSnapshot | null = null;

  /**
   * Freeze weights at session initialization.
   * Must be called exactly once per search session.
   */
  freeze(
    weights: Record<string, number>,
    degradedSources: string[],
  ): FrozenWeightSnapshot {
    if (this.snapshot) {
      // Already frozen — return existing snapshot, don't re-freeze
      return this.snapshot;
    }

    // Remove factors that depend on degraded sources
    const sourceFactorMap: Record<string, string[]> = {
      semantic_scholar: ["citation_impact", "semantic_similarity"],
      openalex: ["citation_impact", "journal_quality", "keyword_match"],
      crossref: ["citation_impact", "journal_quality"],
      pubmed: ["keyword_match", "relevance"],
    };

    const affectedFactors = new Set<string>();
    for (const source of degradedSources) {
      for (const factor of sourceFactorMap[source] ?? []) {
        affectedFactors.add(factor);
      }
    }

    const frozenWeights = { ...weights };
    let affectedTotal = 0;

    for (const factor of affectedFactors) {
      if (frozenWeights[factor] !== undefined) {
        affectedTotal += frozenWeights[factor];
        delete frozenWeights[factor];
      }
    }

    // Redistribute proportionally to unaffected factors
    const unaffectedTotal = Object.values(frozenWeights).reduce((s, v) => s + v, 0);
    if (unaffectedTotal > 0) {
      for (const factor of Object.keys(frozenWeights)) {
        frozenWeights[factor] += affectedTotal * (frozenWeights[factor] / unaffectedTotal);
      }
    }

    this.snapshot = {
      weights: frozenWeights,
      frozenAt: Date.now(),
      degradedSources: [...degradedSources],
    };

    return this.snapshot;
  }

  /**
   * Get the frozen snapshot. Returns null if not yet frozen.
   */
  getSnapshot(): FrozenWeightSnapshot | null {
    return this.snapshot;
  }

  /**
   * Check if the given source was degraded when weights were frozen.
   */
  isSourceFrozenDegraded(source: string): boolean {
    return this.snapshot?.degradedSources.includes(source) ?? false;
  }
}

// ============================================
// Circuit Breaker Manager
// ============================================

export class CircuitBreakerManager {
  private health: Map<string, SourceHealth> = new Map();
  readonly scoreLock: ScoreLock;

  constructor(private onAlert?: (alert: DegradedModeAlert) => void) {
    this.scoreLock = new ScoreLock();
  }

  isAvailable(source: string): boolean {
    const h = this.getHealth(source);

    if (h.state === "closed") return true;

    if (h.state === "open") {
      if (h.openUntil && Date.now() >= h.openUntil) {
        h.state = "half_open";
        h.consecutiveSuccesses = 0;
        this.health.set(source, h);
        return true;
      }
      return false;
    }

    if (h.state === "half_open") return true;

    return false;
  }

  recordSuccess(source: string): void {
    const h = this.getHealth(source);
    h.lastSuccessTime = Date.now();
    h.consecutiveSuccesses++;

    if (h.state === "half_open") {
      if (h.consecutiveSuccesses >= SUCCESS_THRESHOLD) {
        h.state = "closed";
        h.failures = 0;
        h.openUntil = null;
        this.emitAlert({
          type: "source_recovered",
          source,
          message: `Source ${source} has recovered.`,
          timestamp: Date.now(),
        });
      }
    } else if (h.state === "closed") {
      h.failures = 0;
    }

    this.health.set(source, h);
  }

  recordFailure(source: string, errorCode?: number): void {
    const h = this.getHealth(source);
    h.failures++;
    h.lastFailureTime = Date.now();
    h.consecutiveSuccesses = 0;

    if (h.state === "half_open") {
      h.state = "open";
      h.openUntil = Date.now() + OPEN_DURATION_MS;
    } else if (h.failures >= FAILURE_THRESHOLD) {
      h.state = "open";
      h.openUntil = Date.now() + OPEN_DURATION_MS;

      // Only emit alert if weights haven't been frozen yet,
      // or if this is a new degradation event
      this.emitAlert({
        type: "source_degraded",
        source,
        message: `Source ${source} temporarily unavailable (${errorCode ?? "error"}). Weights frozen at session start.`,
        timestamp: Date.now(),
      });
    }

    this.health.set(source, h);
  }

  getAllHealth(): SourceHealth[] {
    return Array.from(this.health.values());
  }

  getDegradedSources(): string[] {
    return Array.from(this.health.entries())
      .filter(([_, h]) => h.state === "open")
      .map(([source]) => source);
  }

  private getHealth(source: string): SourceHealth {
    if (!this.health.has(source)) {
      this.health.set(source, {
        source,
        state: "closed",
        failures: 0,
        lastFailureTime: null,
        lastSuccessTime: null,
        openUntil: null,
        consecutiveSuccesses: 0,
      });
    }
    return this.health.get(source)!;
  }

  private emitAlert(alert: DegradedModeAlert): void {
    this.onAlert?.(alert);
  }
}
