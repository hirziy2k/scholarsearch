// ============================================
// Post-Dedup OA Resolution Pipeline
// ============================================
//
// Resolves open access status AFTER deduplication to avoid burning
// API limits on duplicate papers. Batches updates to prevent DOM
// reconciliation overhead (500ms or 20 DOIs per batch).
//
// Design:
//   Phase A: Collect DOIs from deduplicated results
//   Phase B: Resolve OA in batches of 20
//   Phase C: Stream paper_update_batch events every 500ms

export interface OAResolution {
  doi: string;
  isOa: boolean;
  oaStatus: "gold" | "green" | "hybrid" | "bronze" | "closed" | "unknown";
  oaUrl?: string;
  license?: string;
  repository?: string;
  version?: string;
  resolvedAt: number;
}

export interface OAResolverConfig {
  /** Maximum DOIs per batch */
  batchSize: number;
  /** Maximum milliseconds between batch flushes */
  flushIntervalMs: number;
  /** Timeout per individual DOI resolution (ms) */
  timeoutMs: number;
  /** Whether to use Unpaywall */
  useUnpaywall: boolean;
  /** Whether to use CORE */
  useCore: boolean;
}

export const DEFAULT_OA_CONFIG: OAResolverConfig = {
  batchSize: 20,
  flushIntervalMs: 500,
  timeoutMs: 10000,
  useUnpaywall: true,
  useCore: true,
};

// ============================================
// Batched OA Resolver
// ============================================

export class OAResolver {
  private config: OAResolverConfig;
  private unpaywallEmail?: string;

  constructor(config?: Partial<OAResolverConfig>) {
    this.config = { ...DEFAULT_OA_CONFIG, ...config };
    this.unpaywallEmail = process.env.UNPAYWALL_EMAIL;
  }

  /**
   * Resolve OA status for a batch of papers.
   * Returns a Map<doi, OAResolution> and batches the updates.
   *
   * @param papers - Array of papers with DOIs
   * @param onBatch - Callback for each batch of resolved papers
   * @returns All resolutions
   */
  async resolveBatch(
    papers: Array<{ doi?: string; _source?: string }>,
    onBatch?: (batch: OAResolution[]) => void,
  ): Promise<Map<string, OAResolution>> {
    const resolutions = new Map<string, OAResolution>();
    const doisToResolve = papers
      .filter(p => p.doi && p.doi.length > 0)
      .map(p => p.doi!);

    if (doisToResolve.length === 0) return resolutions;

    // Process in batches
    for (let i = 0; i < doisToResolve.length; i += this.config.batchSize) {
      const batch = doisToResolve.slice(i, i + this.config.batchSize);

      const batchResolutions = await this.resolveDOI_batch(batch);
      for (const [doi, resolution] of batchResolutions) {
        resolutions.set(doi, resolution);
      }

      // Emit batch callback
      if (onBatch) {
        onBatch(Array.from(batchResolutions.values()));
      }

      // Rate limit: wait between batches
      if (i + this.config.batchSize < doisToResolve.length) {
        await this.sleep(this.config.flushIntervalMs);
      }
    }

    return resolutions;
  }

  /**
   * Resolve a batch of DOIs concurrently.
   */
  private async resolveDOI_batch(
    dois: string[],
  ): Promise<Map<string, OAResolution>> {
    const results = new Map<string, OAResolution>();

    const promises = dois.map(async (doi) => {
      try {
        const resolution = await this.resolveDOI(doi);
        results.set(doi.toLowerCase(), resolution);
      } catch {
        // Mark as unknown on failure
        results.set(doi.toLowerCase(), {
          doi,
          isOa: false,
          oaStatus: "unknown",
          resolvedAt: Date.now(),
        });
      }
    });

    await Promise.allSettled(promises);
    return results;
  }

  /**
   * Resolve a single DOI via Unpaywall.
   */
  private async resolveDOI(doi: string): Promise<OAResolution> {
    if (!this.config.useUnpaywall || !this.unpaywallEmail) {
      return {
        doi,
        isOa: false,
        oaStatus: "unknown",
        resolvedAt: Date.now(),
      };
    }

    const url = `https://api.unpaywall.org/v2/${encodeURIComponent(doi)}?email=${this.unpaywallEmail}`;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.config.timeoutMs);

    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) {
        throw new Error(`Unpaywall returned ${response.status}`);
      }

      const data = await response.json() as any;

      return {
        doi,
        isOa: data.is_oa ?? false,
        oaStatus: data.oa_status ?? "unknown",
        oaUrl: data.best_oa_location?.url_for_pdf ?? data.best_oa_location?.url ?? undefined,
        license: data.best_oa_location?.license ?? undefined,
        repository: data.best_oa_location?.repository_institution ?? undefined,
        version: data.best_oa_location?.version ?? undefined,
        resolvedAt: Date.now(),
      };
    } finally {
      clearTimeout(timeout);
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// ============================================
// OA Status Watermark Integration
// ============================================

/**
 * Apply OA resolution results to a paper's watermark object.
 * Called after each batch resolves.
 */
export function applyOAResolution(
  paper: any,
  resolution: OAResolution,
): any {
  return {
    ...paper,
    isOa: resolution.isOa,
    oaStatus: resolution.oaStatus,
    fullTextUrl: resolution.oaUrl ?? paper.fullTextUrl,
    oaLicense: resolution.license,
    oaRepository: resolution.repository,
    oaVersion: resolution.version,
    _watermarks: {
      ...paper._watermarks,
      oa_resolved: true,
    },
  };
}
