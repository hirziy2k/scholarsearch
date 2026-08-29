import { RateLimiter, fetchWithRetry, type SourceClient, type SearchContext, type SearchResult } from "./shared.js";

const DOAJ_BASE = "https://doaj.org/api/v2";

export class DoajClient implements SourceClient {
  readonly name = "doaj";
  readonly displayName = "DOAJ";

  private rateLimiter: RateLimiter;

  constructor() {
    // DOAJ API: conservative rate limit
    this.rateLimiter = new RateLimiter(5);
  }

  async health(): Promise<boolean> {
    try {
      const res = await fetchWithRetry(`${DOAJ_BASE}/search/articles/test?page=1&pageSize=1`, {
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

      const body = JSON.stringify({
        query: {
          query_string: {
            query: ctx.query,
            default_operator: "AND",
          },
        },
        from: 0,
        size: Math.min(ctx.maxResults, 100),
        sort: [{ _score: { order: "desc" } }],
        _source: [
          "bibjson.title",
          "bibjson.author",
          "bibjson.year",
          "bibjson.identifier",
          "bibjson.journal.title",
          "bibjson.abstract",
          "bibjson.subject",
          "bibjson.link",
          "bibjson.publisher",
          "bibjson.keywords",
        ],
      });

      const searchRes = await fetchWithRetry(
        `${DOAJ_BASE}/search/articles`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
          },
          body,
          timeout: 30000,
        }
      );

      if (!searchRes.ok) {
        throw new Error(`DOAJ search error: ${searchRes.status}`);
      }

      const searchData = await searchRes.json() as any;
      const hits = searchData.hits?.hits ?? [];

      const rawResults = hits.map((hit: any) => normalizeDoajRecord(hit._source));

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

function normalizeDoajRecord(bibjson: any): any {
  const getFirst = (arr: any[]): string | undefined => Array.isArray(arr) && arr.length > 0 ? arr[0] : undefined;

  // Extract DOI from identifiers
  let doi: string | undefined;
  const identifiers = bibjson.identifier ?? [];
  for (const id of identifiers) {
    if (id.type === "doi" && id.id) {
      doi = id.id;
      break;
    }
  }

  // Extract OA URL from links
  let fullTextUrl: string | undefined;
  const links = bibjson.link ?? [];
  for (const link of links) {
    if (link.type === "fulltext" && link.url) {
      fullTextUrl = link.url;
      break;
    }
    if (link.type === "pdf" && link.url) {
      fullTextUrl = link.url;
      break;
    }
  }

  // Extract journal title
  const journalTitle = bibjson.journal?.title ?? bibjson.journal?.name;

  // Extract authors
  const authors = bibjson.author?.map((a: any) => a.name).filter(Boolean) ?? [];

  // Extract subjects
  const subjects = bibjson.subject ?? [];

  return {
    title: bibjson.title,
    authors,
    year: bibjson.year ? parseInt(bibjson.year) : undefined,
    doi,
    journal: journalTitle,
    abstract: bibjson.abstract,
    citations: 0, // DOAJ doesn't provide citation counts
    is_oa: true, // DOAJ is open access by definition
    fullTextUrl,
    type: "article",
    publisher: bibjson.publisher,
    source: "doaj",
    identifiers: {
      doi,
      subjects,
    },
    // DOAJ-specific fields
    subjects,
    keywords: bibjson.keywords ?? [],
  };
}