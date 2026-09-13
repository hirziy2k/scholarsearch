import { RateLimiter, fetchWithRetry, type SourceClient, type SearchContext, type SearchResult } from "./shared.js";

const CORE_BASE = "https://api.core.ac.uk/v3";

export class CoreClient implements SourceClient {
  readonly name = "core";
  readonly displayName = "CORE";

  private rateLimiter: RateLimiter;
  private apiKey?: string;

  constructor(opts?: { apiKey?: string }) {
    this.apiKey = opts?.apiKey;
    // CORE API: 10 req/s with key
    this.rateLimiter = new RateLimiter(opts?.apiKey ? 10 : 1);
  }

  async health(): Promise<boolean> {
    try {
      const res = await fetchWithRetry(`${CORE_BASE}/search/works?q=test&limit=1`, {
        headers: this.getHeaders(),
        timeout: 10000,
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Accept": "application/json",
      "Content-Type": "application/json",
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  async search(ctx: SearchContext): Promise<SearchResult> {
    const start = Date.now();

    try {
      await this.rateLimiter.acquire();

      const body = JSON.stringify({
        q: ctx.query,
        limit: Math.min(ctx.maxResults, 100),
        scroll: false,
      });

      const searchRes = await fetchWithRetry(
        `${CORE_BASE}/search/works`,
        {
          method: "POST",
          headers: this.getHeaders(),
          body,
          timeout: 30000,
        }
      );

      if (!searchRes.ok) {
        throw new Error(`CORE search error: ${searchRes.status}`);
      }

      const searchData = await searchJson(searchRes);
      const works = searchData.results ?? [];

      const rawResults = works.map((work: any) => normalizeCoreWork(work));

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

async function searchJson(res: Response): Promise<any> {
  const text = await res.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

function normalizeCoreWork(work: any): any {
  return {
    title: work.title,
    authors: work.authors?.map((a: any) => a.name ?? a) ?? [],
    year: work.yearPublished ?? work.createdYear,
    doi: work.doi,
    journal: work.journal?.name,
    abstract: work.abstract,
    citations: work.citationCount ?? 0,
    is_oa: work.openAccess ?? false,
    fullTextUrl: work.downloadUrl ?? work.openAccessPdf?.url,
    type: work.type,
    publisher: work.publisher,
    source: "core",
    identifiers: {
      doi: work.doi,
      core_id: work.id,
    },
  };
}