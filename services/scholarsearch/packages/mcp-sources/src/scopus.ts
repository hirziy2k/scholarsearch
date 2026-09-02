import { RateLimiter, fetchWithRetry, type SourceClient, type SearchContext, type SearchResult } from './shared.js';

const BASE_URL = 'https://api.elsevier.com/content/search/scopus';

export class ScopusClient implements SourceClient {
  readonly name = 'scopus';
  readonly displayName = 'Scopus';

  private apiKey: string;
  private rateLimiter: RateLimiter;

  constructor(config: { apiKey?: string; rateLimit?: number }) {
    this.apiKey = config.apiKey || process.env.SCOPUS_API_KEY || '';
    this.rateLimiter = new RateLimiter(config.rateLimit ?? 9);
  }

  async health(): Promise<boolean> {
    try {
      const res = await fetchWithRetry(`${BASE_URL}?query=test&count=1`, {
        timeout: 10000,
        headers: { 'X-ELS-APIKey': this.apiKey, Accept: 'application/json' },
      });
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
        query: ctx.query,
        count: String(Math.min(ctx.maxResults, 25)),
        field: 'dc:identifier,dc:title,dc:creator,dc:description,prism:doi,prism:coverDate,prism:publicationName,citedby-count,link',
      });

      const res = await fetchWithRetry(`${BASE_URL}?${params}`, {
        timeout: 15000,
        headers: { 'X-ELS-APIKey': this.apiKey, Accept: 'application/json' },
      });

      if (!res.ok) {
        return {
          source: 'scopus',
          query_used: ctx.query,
          results_count: 0,
          raw_results: [],
          timestamp: new Date().toISOString(),
          duration_ms: Date.now() - start,
          error: `Scopus API error: ${res.status}`,
        };
      }

      const data = (await res.json()) as Record<string, any>;
      const searchResults = data['search-results'];
      const entries: any[] = searchResults?.entry ?? [];

      return {
        source: 'scopus',
        query_used: ctx.query,
        results_count: parseInt(searchResults?.['opensearch:totalResults'] ?? '0', 10),
        raw_results: entries.map((entry: Record<string, any>) => ({
          id: entry['dc:identifier'],
          title: entry['dc:title'],
          authors: entry['dc:creator'],
          abstract: entry['dc:description'],
          doi: entry['prism:doi'],
          publicationDate: entry['prism:coverDate'],
          journal: entry['prism:publicationName'],
          citationCount: entry['citedby-count'],
          url: entry['link']?.[0]?.['@href'],
        })),
        timestamp: new Date().toISOString(),
        duration_ms: Date.now() - start,
      };
    } catch (err) {
      return {
        source: 'scopus',
        query_used: ctx.query,
        results_count: 0,
        raw_results: [],
        timestamp: new Date().toISOString(),
        duration_ms: Date.now() - start,
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }
}
