import type { FastifyInstance } from "fastify";
import {
  getSession,
  getPages,
  getPage,
  writePage,
  updateSessionStatus,
  updateSourceStatus,
} from "../services/session-manager.js";
import { fetchWithMutex } from "../utils/fetch-mutex.js";
import { validatePagePayload } from "../utils/page-validation.js";

const PAGE_SIZE = 10;
const FETCH_TIMEOUT_MS = 30_000;

// Source client map — lazy-loaded to avoid circular deps
let sourceClientMap: Record<string, any> | null = null;

async function getSourceClientMap() {
  if (sourceClientMap) return sourceClientMap;
  const {
    OpenAlexClient,
    PubMedClient,
    SemanticScholarClient,
    CrossrefClient,
    CoreClient,
    EricClient,
    DoajClient,
    ScopusClient,
  } = await import("@scholarsearch/mcp-sources");

  sourceClientMap = {
    openalex: new OpenAlexClient({ email: process.env.OPENALEX_EMAIL }),
    pubmed: new PubMedClient({ apiKey: process.env.NCBI_API_KEY }),
    semantic_scholar: new SemanticScholarClient({ apiKey: process.env.SEMANTIC_SCHOLAR_API_KEY }),
    crossref: new CrossrefClient({ email: process.env.UNPAYWALL_EMAIL }),
    core: new CoreClient({ apiKey: process.env.CORE_API_KEY }),
    eric: new EricClient(),
    doaj: new DoajClient(),
    scopus: new ScopusClient({ apiKey: process.env.SCOPUS_API_KEY }),
  };
  return sourceClientMap;
}

const SOURCE_CLIENT_KEYS: Record<string, string> = {
  openalex: "openalex",
  pubmed: "pubmed",
  semantic_scholar: "semantic_scholar",
  crossref: "crossref",
  core: "core",
  eric: "eric",
  doaj: "doaj",
  scopus: "scopus",
};

async function fetchSourcePage(
  source: string,
  pageNumber: number,
  rawQuery: string,
  hitCount: number,
): Promise<{ results: any[]; hitCount: number }> {
  const clients = await getSourceClientMap();
  const clientKey = SOURCE_CLIENT_KEYS[source];
  if (!clientKey || !clients[clientKey]) {
    throw new Error(`Unknown source: ${source}`);
  }

  const client = clients[clientKey];
  const maxResults = Math.min(PAGE_SIZE, 100);

  const result = await client.search({
    query: rawQuery,
    maxResults,
  });

  return {
    results: result.raw_results ?? [],
    hitCount: result.results_count ?? hitCount,
  };
}

export async function pollingRoutes(app: FastifyInstance) {
  /**
   * GET /api/search/:searchId/results?page=N&source=...
   * Lazy-loaded polling endpoint. Returns a single page of results.
   * If the page doesn't exist yet, triggers a fetch from the source.
   * Uses in-memory mutex to prevent redundant API calls.
   * Uses immutable insert (no upsert) for provenance integrity.
   */
  app.get<{
    Params: { searchId: string };
    Querystring: { page?: string; source?: string };
  }>("/search/:searchId/results", async (request, reply) => {
    const { searchId } = request.params;
    const pageNumber = Math.max(1, parseInt(request.query.page ?? "1", 10));
    const sourceFilter = request.query.source;

    const session = await getSession(searchId);
    if (!session) {
      return reply.status(404).send({ error: "Session not found" });
    }

    if (session.expiresAt && new Date(session.expiresAt) < new Date()) {
      return reply.status(410).send({ error: "Session expired" });
    }

    // Get source statuses
    const sourceStatuses = JSON.parse(session.sourceStatuses) as any[];
    const sources = sourceFilter
      ? sourceStatuses.filter((s: any) => s.source === sourceFilter)
      : sourceStatuses;

    const results: any[] = [];
    const pageErrors: Array<{ source: string; error: string }> = [];

    for (const sourceStatus of sources) {
      const source = sourceStatus.source;
      const hitCount = sourceStatus.hitCount ?? 0;

      // Check if page already exists (immutable cache)
      const existing = await getPage(session.id, source, pageNumber);
      if (existing) {
        const parsed = JSON.parse(existing.rawResults);
        if (!parsed.error) {
          results.push(...parsed);
        } else {
          pageErrors.push({ source, error: parsed.error });
        }
        continue;
      }

      // Check if this source has more pages to fetch
      const totalPages = Math.ceil(hitCount / PAGE_SIZE);
      if (pageNumber > totalPages && hitCount > 0) {
        continue;
      }

      // Fetch via mutex (prevents redundant API calls)
      const mutexKey = `${session.id}:${source}:${pageNumber}`;

      try {
        const fetched = await fetchWithMutex(mutexKey, () =>
          fetchSourcePage(source, pageNumber, session.rawQuery, hitCount),
        );

        // Validate payload before writing
        const validation = validatePagePayload(
          fetched.results,
          pageNumber,
          fetched.hitCount,
          PAGE_SIZE,
        );

        if (!validation.valid) {
          // Write rejected payload for audit trail
          await writePage(session.id, source, pageNumber, [{ error: validation.reason }], 0);
          pageErrors.push({ source, error: validation.reason! });
          await updateSourceStatus(searchId, source, {
            status: "error",
            error: validation.reason,
          });
          continue;
        }

        // Immutable insert: first write wins
        const wrote = await writePage(
          session.id,
          source,
          pageNumber,
          fetched.results,
          fetched.hitCount,
        );

        if (wrote) {
          results.push(...fetched.results);
          await updateSourceStatus(searchId, source, {
            resultCount: fetched.results.length,
          });
        } else {
          // Another request wrote first — read what they wrote
          const written = await getPage(session.id, source, pageNumber);
          if (written) {
            const parsed = JSON.parse(written.rawResults);
            if (!parsed.error) {
              results.push(...parsed);
            }
          }
        }
      } catch (error) {
        const errMsg = error instanceof Error ? error.message : String(error);
        pageErrors.push({ source, error: errMsg });
        await updateSourceStatus(searchId, source, {
          status: "error",
          error: errMsg,
        });
      }
    }

    // Determine if search is now complete
    const allComplete = sources.every(
      (s: any) => s.status === "complete" || s.status === "error",
    );
    const anyError = pageErrors.length > 0;

    if (allComplete && pageNumber >= Math.max(...sources.map((s: any) => Math.ceil((s.hitCount ?? 0) / PAGE_SIZE)), 1)) {
      await updateSessionStatus(searchId, anyError ? "partial" : "complete");
    }

    return reply.send({
      searchId,
      page: pageNumber,
      results,
      errors: pageErrors.length > 0 ? pageErrors : undefined,
      sourceStatuses: sources.map((s: any) => ({
        source: s.source,
        status: s.status,
        resultCount: s.resultCount,
        hitCount: s.hitCount,
        error: s.error,
      })),
      sessionStatus: (await getSession(searchId))?.status ?? "unknown",
    });
  });

  /**
   * GET /api/search/:searchId/status
   * Lightweight status check — no payload, no fetch triggers.
   */
  app.get<{
    Params: { searchId: string };
  }>("/search/:searchId/status", async (request, reply) => {
    const { searchId } = request.params;
    const session = await getSession(searchId);
    if (!session) {
      return reply.status(404).send({ error: "Session not found" });
    }

    const sourceStatuses = JSON.parse(session.sourceStatuses) as any[];

    return reply.send({
      searchId,
      status: session.status,
      mode: session.mode,
      methodology: session.methodology,
      totalPages: session.totalPages,
      fetchedPages: session.fetchedPages,
      sourceStatuses,
      createdAt: session.createdAt,
      expiresAt: session.expiresAt,
    });
  });
}
