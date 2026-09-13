import { RateLimiter, fetchWithRetry, type SourceClient, type SearchContext, type SearchResult } from "./shared.js";

const EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils";

export class PubMedClient implements SourceClient {
  readonly name = "pubmed";
  readonly displayName = "PubMed/PMC";

  private rateLimiter: RateLimiter;
  private apiKey?: string;

  constructor(opts?: { apiKey?: string }) {
    this.apiKey = opts?.apiKey;
    // 3 req/s without key, 10 req/s with key
    this.rateLimiter = new RateLimiter(opts?.apiKey ? 10 : 3);
  }

  async health(): Promise<boolean> {
    try {
      const res = await fetchWithRetry(`${EUTILS_BASE}/einfo.fcgi?db=pubmed&retmode=json`, { timeout: 10000 });
      return res.ok;
    } catch {
      return false;
    }
  }

  async search(ctx: SearchContext): Promise<SearchResult> {
    const start = Date.now();

    try {
      // Step 1: Search PubMed for IDs
      await this.rateLimiter.acquire();
      const searchParams = new URLSearchParams({
        db: "pubmed",
        term: ctx.query,
        retmax: String(Math.min(ctx.maxResults, 200)),
        retmode: "json",
        sort: "relevance",
      });
      if (this.apiKey) searchParams.set("api_key", this.apiKey);

      const searchRes = await fetchWithRetry(
        `${EUTILS_BASE}/esearch.fcgi?${searchParams.toString()}`,
      );

      if (!searchRes.ok) {
        throw new Error(`PubMed search error: ${searchRes.status}`);
      }

      const searchData = await searchRes.json() as any;
      const ids: string[] = searchData.esearchresult?.idlist ?? [];

      if (ids.length === 0) {
        return {
          source: this.name,
          query_used: ctx.query,
          results_count: 0,
          raw_results: [],
          timestamp: new Date().toISOString(),
          duration_ms: Date.now() - start,
        };
      }

      // Step 2: Fetch summaries for the IDs
      await this.rateLimiter.acquire();
      const summaryParams = new URLSearchParams({
        db: "pubmed",
        id: ids.join(","),
        retmode: "json",
      });
      if (this.apiKey) summaryParams.set("api_key", this.apiKey);

      const summaryRes = await fetchWithRetry(
        `${EUTILS_BASE}/esummary.fcgi?${summaryParams.toString()}`,
      );

      if (!summaryRes.ok) {
        throw new Error(`PubMed summary error: ${summaryRes.status}`);
      }

      const summaryData = await summaryRes.json() as any;
      const results = ids
        .map((id) => ({ id, ...summaryData.result?.[id] }))
        .filter((r) => r.uid);

      return {
        source: this.name,
        query_used: ctx.query,
        results_count: searchData.esearchresult?.count ?? results.length,
        raw_results: results,
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
