import { RateLimiter, fetchWithRetry, type SourceClient, type SearchContext, type SearchResult } from "./shared.js";

const BASE_URL = "https://api.crossref.org";

export class CrossrefClient implements SourceClient {
  readonly name = "crossref";
  readonly displayName = "Crossref";

  private rateLimiter: RateLimiter;
  private email?: string;

  constructor(opts?: { email?: string }) {
    this.email = opts?.email;
    this.rateLimiter = new RateLimiter(50); // Polite pool
  }

  async health(): Promise<boolean> {
    try {
      const res = await fetchWithRetry(`${BASE_URL}/works?rows=1`, { timeout: 10000 });
      return res.ok;
    } catch {
      return false;
    }
  }

  async search(ctx: SearchContext): Promise<SearchResult> {
    const start = Date.now();

    try {
      await this.rateLimiter.acquire();

      const params = new URLSearchParams({
        query: ctx.query,
        rows: String(Math.min(ctx.maxResults, 100)),
        sort: "relevance",
        order: "desc",
        select: "DOI,title,author,published-print,published-online,container-title,type,abstract,is-referenced-by-count,link,license,subject,ISSN,publisher",
      });

      if (this.email) {
        params.set("mailto", this.email);
      }

      const url = `${BASE_URL}/works?${params.toString()}`;
      const res = await fetchWithRetry(url);

      if (!res.ok) {
        throw new Error(`Crossref API error: ${res.status}`);
      }

      const data = await res.json() as any;

      return {
        source: this.name,
        query_used: url,
        results_count: data.message?.["total-results"] ?? 0,
        raw_results: data.message?.items ?? [],
        timestamp: new Date().toISOString(),
        duration_ms: Date.now() - start,
      };
    } catch (error) {
      return {
        source: this.name,
        query_used: ctx.query,
        results_count: 0,
        raw_results: [],
        timestamp: new Date().toISOString(),
        duration_ms: Date.now() - start,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Resolve a DOI to full metadata.
   */
  async resolveDoi(doi: string): Promise<Record<string, any> | null> {
    try {
      await this.rateLimiter.acquire();
      const res = await fetchWithRetry(`${BASE_URL}/works/${encodeURIComponent(doi)}`);
      if (!res.ok) return null;
      const data = await res.json() as any;
      return data.message ?? null;
    } catch {
      return null;
    }
  }
}
