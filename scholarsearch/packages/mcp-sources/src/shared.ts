// ============================================
// Rate Limiter (Token Bucket)
// ============================================

export class RateLimiter {
  private tokens: number;
  private lastRefill: number;
  private readonly maxTokens: number;
  private readonly refillRate: number; // tokens per second

  constructor(ratePerSecond: number) {
    this.maxTokens = ratePerSecond;
    this.tokens = ratePerSecond;
    this.refillRate = ratePerSecond;
    this.lastRefill = Date.now();
  }

  async acquire(): Promise<void> {
    this.refill();

    if (this.tokens >= 1) {
      this.tokens -= 1;
      return;
    }

    // Wait until next token is available
    const waitTime = ((1 - this.tokens) / this.refillRate) * 1000;
    await new Promise((resolve) => setTimeout(resolve, waitTime));

    this.refill();
    this.tokens -= 1;
  }

  private refill(): void {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000;
    this.tokens = Math.min(this.maxTokens, this.tokens + elapsed * this.refillRate);
    this.lastRefill = now;
  }
}

// ============================================
// HTTP Client with Retry
// ============================================

export interface FetchOptions extends RequestInit {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

export async function fetchWithRetry(
  url: string,
  options: FetchOptions = {},
): Promise<Response> {
  const { timeout = 30000, retries = 3, retryDelay = 1000, ...fetchOptions } = options;

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok && response.status >= 500 && attempt < retries) {
        await new Promise((r) => setTimeout(r, retryDelay * attempt));
        continue;
      }

      return response;
    } catch (error) {
      if (attempt === retries) throw error;
      await new Promise((r) => setTimeout(r, retryDelay * attempt));
    }
  }

  throw new Error("Max retries exceeded");
}

// ============================================
// Result Types
// ============================================

export interface SearchContext {
  query: string;
  maxResults: number;
  page?: number;
  filters?: Record<string, string>;
}

export interface SearchResult {
  source: string;
  query_used: string;
  results_count: number;
  raw_results: Record<string, any>[];
  timestamp: string;
  duration_ms: number;
  error?: string | null;
}

export interface SourceClient {
  readonly name: string;
  readonly displayName: string;
  search(ctx: SearchContext): Promise<SearchResult>;
  health(): Promise<boolean>;
}
