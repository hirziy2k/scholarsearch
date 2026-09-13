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

  /**
   * Batch resolve multiple DOIs via Crossref filter API.
   * Returns a map of doi → metadata.
   */
  async batchResolveDois(dois: string[]): Promise<Record<string, Record<string, any>>> {
    const result: Record<string, Record<string, any>> = {};
    if (dois.length === 0) return result;

    try {
      await this.rateLimiter.acquire();

      // Crossref supports pipe-separated DOI filters
      const filterDoi = dois.map(d => `doi:${d}`).join("|");
      const params = new URLSearchParams({
        filter: filterDoi,
        rows: String(dois.length),
        select: "DOI,title,abstract,is-referenced-by-count,link,license,type,author,published-print,published-online,container-title",
      });

      if (this.email) {
        params.set("mailto", this.email);
      }

      const url = `${BASE_URL}/works?${params.toString()}`;
      const res = await fetchWithRetry(url);
      if (!res.ok) return result;

      const data = await res.json() as any;
      const items = data.message?.items ?? [];

      for (const item of items) {
        const doi = item.DOI?.toLowerCase();
        if (doi) {
          result[doi] = item;
        }
      }
    } catch {
      // Return partial results
    }

    return result;
  }
}
