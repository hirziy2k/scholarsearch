import { RateLimiter, fetchWithRetry, type SourceClient, type SearchContext, type SearchResult } from "./shared.js";

const ERIC_BASE = "https://api.ies.ed.gov/eric";

export class EricClient implements SourceClient {
  readonly name = "eric";
  readonly displayName = "ERIC";

  private rateLimiter: RateLimiter;

  constructor() {
    // ERIC API: ~10 req/s
    this.rateLimiter = new RateLimiter(10);
  }

  async health(): Promise<boolean> {
    try {
      const res = await fetchWithRetry(`${ERIC_BASE}/search?q=test&rows=1&format=json`, {
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
        q: ctx.query,
        rows: String(Math.min(ctx.maxResults, 100)),
        start: "0",
        format: "json",
        sort: "relevance",
        fields: "id,title,author,publicationyear,abstract,identifier,pubtype,peerreviewed,source,doi,url,subject",
      });

      // Add filters if provided
      if (ctx.filters?.yearFrom) {
        params.set("pubyear", `${ctx.filters.yearFrom}-`);
      }

      const searchRes = await fetchWithRetry(
        `${ERIC_BASE}/search?${params.toString()}`,
        { timeout: 30000 }
      );

      if (!searchRes.ok) {
        throw new Error(`ERIC search error: ${searchRes.status}`);
      }

      const searchData = await searchRes.json() as any;
      const records = searchData.response?.docs ?? [];

      const rawResults = records.map((rec: any) => normalizeEricRecord(rec));

      return {
        source: this.name,
        query_used: ctx.query,
        results_count: rawResults.length,
        raw_results: rawResults,
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

function normalizeEricRecord(rec: any): any {
  // ERIC returns arrays for most fields, take first element
  const getFirst = (arr: any[]): string | undefined => Array.isArray(arr) && arr.length > 0 ? arr[0] : undefined;

  return {
    title: getFirst(rec.title),
    authors: rec.author ?? [],
    year: rec.publicationyear ? parseInt(getFirst(rec.publicationyear) ?? "") : undefined,
    doi: getFirst(rec.doi),
    journal: getFirst(rec.source),
    abstract: getFirst(rec.abstract),
    citations: 0, // ERIC doesn't provide citation counts
    is_oa: rec.peerreviewed ? false : true, // Many ERIC docs are grey literature
    fullTextUrl: getFirst(rec.url),
    type: getFirst(rec.pubtype),
    publisher: getFirst(rec.source),
    source: "eric",
    identifiers: {
      eric_id: getFirst(rec.id),
      doi: getFirst(rec.doi),
    },
    // ERIC-specific fields for tier classification
    peerreviewed: rec.peerreviewed ? getFirst(rec.peerreviewed) === "Y" : false,
    pubtype: rec.pubtype ?? [],
    subject: rec.subject ?? [],
  };
}