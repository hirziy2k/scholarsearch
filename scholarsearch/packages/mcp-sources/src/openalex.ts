import { RateLimiter, fetchWithRetry, type SourceClient, type SearchContext, type SearchResult } from "./shared.js";

const BASE_URL = "https://api.openalex.org";

export class OpenAlexClient implements SourceClient {
  readonly name = "openalex";
  readonly displayName = "OpenAlex";

  private rateLimiter: RateLimiter;
  private email?: string;

  constructor(opts?: { email?: string; rateLimit?: number }) {
    this.email = opts?.email;
    this.rateLimiter = new RateLimiter(opts?.rateLimit ?? 10);
  }

  async health(): Promise<boolean> {
    try {
      const url = `${BASE_URL}/works?per_page=1`;
      const res = await fetchWithRetry(url, { timeout: 10000 });
      return res.ok;
    } catch {
      return false;
    }
  }

  async search(ctx: SearchContext): Promise<SearchResult> {
    const start = Date.now();
    await this.rateLimiter.acquire();

    try {
      const params = new URLSearchParams({
        "default.search": ctx.query,
        per_page: String(Math.min(ctx.maxResults, 100)),
        page: String(ctx.page ?? 1),
        select: "id,doi,title,authorships,publication_year,primary_location,type,cited_by_count,open_access,abstract_inverted_index,concepts,keywords",
      });

      if (this.email) {
        params.set("mailto", this.email);
      }

      // Apply filters
      if (ctx.filters) {
        const filterParts: string[] = [];
        if (ctx.filters.from_publication_date) {
          filterParts.push(`from_publication_date:${ctx.filters.from_publication_date}`);
        }
        if (ctx.filters.to_publication_date) {
          filterParts.push(`to_publication_date:${ctx.filters.to_publication_date}`);
        }
        if (ctx.filters.is_oa === "true") {
          filterParts.push("is_oa:true");
        }
        if (ctx.filters.language) {
          filterParts.push(`language:${ctx.filters.language}`);
        }
        if (filterParts.length > 0) {
          params.set("filter", filterParts.join(","));
        }
      }

      const url = `${BASE_URL}/works?${params.toString()}`;
      const res = await fetchWithRetry(url);

      if (!res.ok) {
        throw new Error(`OpenAlex API error: ${res.status}`);
      }

      const data = await res.json() as any;

      return {
        source: this.name,
        query_used: url,
        results_count: data.meta?.count ?? 0,
        raw_results: data.results ?? [],
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
   * Batch resolve multiple DOIs via OpenAlex filter API.
   * Returns a map of doi → metadata.
   */
  async batchResolveDois(dois: string[]): Promise<Record<string, Record<string, any>>> {
    const result: Record<string, Record<string, any>> = {};
    if (dois.length === 0) return result;

    try {
      await this.rateLimiter.acquire();

      // OpenAlex supports pipe-separated DOI filters (full URL format)
      const filterDoi = dois.map(d => `doi:https://doi.org/${d}`).join("|");
      const params = new URLSearchParams({
        filter: filterDoi,
        per_page: String(dois.length),
        select: "id,doi,title,open_access,type,publication_year,cited_by_count,abstract_inverted_index",
      });

      if (this.email) {
        params.set("mailto", this.email);
      }

      const url = `${BASE_URL}/works?${params.toString()}`;
      const res = await fetchWithRetry(url);
      if (!res.ok) return result;

      const data = await res.json() as any;
      const items = data.results ?? [];

      for (const item of items) {
        const doi = item.doi?.replace(/^https:\/\/doi\.org\//, "")?.toLowerCase();
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
