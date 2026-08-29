import { RateLimiter, fetchWithRetry, type SourceClient, type SearchContext, type SearchResult } from "./shared.js";

const BASE_URL = "https://api.semanticscholar.org/graph/v1";

export class SemanticScholarClient implements SourceClient {
  readonly name = "semantic_scholar";
  readonly displayName = "Semantic Scholar";

  private rateLimiter: RateLimiter;
  private apiKey?: string;

  constructor(opts?: { apiKey?: string }) {
    this.apiKey = opts?.apiKey;
    // Without key: shared 1000 req/s across all users
    // With key: 1 req/s intro rate (higher tiers via partnership)
    this.rateLimiter = new RateLimiter(50); // Conservative limit
  }

  async health(): Promise<boolean> {
    try {
      const res = await fetchWithRetry(`${BASE_URL}/paper/DOI:10.1038/s41586-020-2649-2?fields=title`, {
        timeout: 10000,
      });
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
        limit: String(Math.min(ctx.maxResults, 100)),
        fields: "paperId,externalIds,title,abstract,year,referenceCount,citationCount,fieldsOfStudy,publicationTypes,journal,openAccessPdf,authors,tldr",
      });

      if (this.apiKey) {
        // API key goes in header, but for URL-based approach we note it
      }

      const headers: Record<string, string> = {};
      if (this.apiKey) {
        headers["x-api-key"] = this.apiKey;
      }

      const url = `${BASE_URL}/paper/search?${params.toString()}`;
      const res = await fetchWithRetry(url, { headers });

      if (!res.ok) {
        throw new Error(`Semantic Scholar API error: ${res.status}`);
      }

      const data = await res.json() as any;

      return {
        source: this.name,
        query_used: url,
        results_count: data.total ?? data.data?.length ?? 0,
        raw_results: data.data ?? [],
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
}
