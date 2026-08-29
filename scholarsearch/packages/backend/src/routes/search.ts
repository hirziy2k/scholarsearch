import type { FastifyInstance } from "fastify";
import { orchestrateSearch } from "../services/search-orchestrator.js";
import type { SearchQuery } from "@scholarsearch/shared";

function extractYear(paper: any): number | undefined {
  if (typeof paper.year === "number") return paper.year;
  if (typeof paper.publication_year === "number") return paper.publication_year;
  if (paper.published?.["date-parts"]?.[0]?.[0]) return paper.published["date-parts"][0][0];
  if (paper["published-print"]?.["date-parts"]?.[0]?.[0]) return paper["published-print"]["date-parts"][0][0];
  if (paper["published-online"]?.["date-parts"]?.[0]?.[0]) return paper["published-online"]["date-parts"][0][0];
  if (typeof paper.sortpubdate === "string") {
    const m = paper.sortpubdate.match(/(\d{4})/);
    if (m) return parseInt(m[1], 10);
  }
  if (typeof paper.pubdate === "string") {
    const m = paper.pubdate.match(/(\d{4})/);
    if (m) return parseInt(m[1], 10);
  }
  return undefined;
}

function normalizePaper(paper: any, source: string, degradedSources: string[] = []) {
  let rawTitle = paper.title ?? paper.Title ?? "";
  if (Array.isArray(rawTitle)) rawTitle = rawTitle[0] ?? "";
  if (typeof rawTitle !== "string") rawTitle = String(rawTitle ?? "");

  let authors: string[] = [];
  const rawAuthors = paper.authors ?? paper.authorships ?? paper.author ?? [];
  if (Array.isArray(rawAuthors)) {
    authors = rawAuthors.map((a: any) => {
      if (typeof a === "string") return a;
      if (a.name) return a.name;
      if (a.display_name) return a.display_name;
      if (a.author?.display_name) return a.author.display_name;
      if (a.given && a.family) return `${a.given} ${a.family}`;
      if (a.Name) return a.Name;
      return "Unknown";
    });
  }

  const doi = paper.DOI ?? paper.doi ?? paper.externalIds?.DOI ?? null;
  const journal = paper.source ?? (Array.isArray(paper.container_title) ? paper.container_title[0] : paper.container_title) ?? paper.containerTitle ?? "";
  const citations = paper.cited_by_count ?? paper.citationCount ?? paper.is_referenced_by_count ?? 0;
  const isOa = paper.is_oa ?? !!paper.openAccessPdf ?? paper.open_access?.is_oa ?? false;
  const fullTextUrl = paper.openAccessPdf?.url ?? paper.best_oa_location?.pdf_url ?? null;

  // Granular Watermarking: track which data sources are missing
  const watermarks: Record<string, boolean> = {};
  if (degradedSources.includes("semantic_scholar")) {
    watermarks.s2_citations = true;    // S2 citation count unavailable
    watermarks.s2_embeddings = true;   // S2 SPECTER2 embeddings unavailable
    watermarks.s2_influential = true;  // S2 influential citations unavailable
  }
  if (degradedSources.includes("openalex")) {
    watermarks.oa_concepts = true;     // OpenAlex concept tags unavailable
    watermarks.oa_institutions = true; // OpenAlex institutional affiliations unavailable
    watermarks.oa_citations = true;    // OpenAlex citation count unavailable
  }
  if (degradedSources.includes("crossref")) {
    watermarks.cr_references = true;   // Crossref reference list unavailable
    watermarks.cr_license = true;      // Crossref license metadata unavailable
  }
  if (degradedSources.includes("pubmed")) {
    watermarks.pm_mesh = true;         // PubMed MeSH terms unavailable
    watermarks.pm_abstract = true;     // PubMed structured abstract unavailable
  }

  return {
    _source: source,
    _watermarks: Object.keys(watermarks).length > 0 ? watermarks : undefined,
    title: rawTitle,
    authors,
    year: extractYear(paper),
    doi,
    journal,
    abstract: paper.abstract ?? paper.abstract_inverted_index ?? null,
    citations,
    isOa,
    fullTextUrl,
    type: paper.type ?? paper.publicationType ?? null,
    pmid: paper.uid ?? paper.pmid ?? null,
  };
}

export async function searchRoutes(app: FastifyInstance) {
  /**
   * POST /api/search — Full search with SSE streaming progress
   */
  app.post<{
    Body: SearchQuery;
  }>("/search", async (request, reply) => {
    const query = request.body as SearchQuery;

    if (!query?.raw_query) {
      return reply.status(400).send({ error: "raw_query is required" });
    }

    // Set SSE headers
    reply.raw.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    });

    const sendEvent = (event: string, data: any) => {
      reply.raw.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
    };

    try {
      // Send initial progress
      sendEvent("progress", { status: "started", query: query.raw_query });

      // Run orchestration with progress callbacks
      const result = await orchestrateSearch(query, (progress) => {
        if (progress.type === "source_progress") {
          sendEvent("source_progress", progress);
        } else if (progress.type === "degraded") {
          sendEvent("degraded", progress.alert);
        } else if (progress.type === "score_frozen") {
          sendEvent("score_frozen", progress.snapshot);
        }
      });

      // Send compiled queries for transparency
      const compiledObj: Record<string, string> = {};
      result.compiledQueries.forEach((v, k) => { compiledObj[k] = v; });
      sendEvent("compiled_queries", compiledObj);

      // Send local intersection info
      if (result.needsLocalIntersection) {
        sendEvent("local_intersection", {
          sources: result.andUnsafeSources,
          message: `AND-unsafe sources (${result.andUnsafeSources.join(", ")}) pulled superset. Exact intersection applied locally.`,
        });
      }

      // Send results summary
      sendEvent("results", {
        searchId: result.searchId,
        totalRaw: result.totalRaw,
        totalDeduplicated: result.totalDeduplicated,
        duplicatesRemoved: result.duplicatesRemoved,
        entityBlockedCount: result.entityBlockedCount,
        durationMs: result.durationMs,
        shadowMergeCount: result.shadowMergeFlags.length,
        degradedSources: result.degradedSources,
        weightsFrozenAt: result.weightsFrozenAt,
        sources: result.sources.map((s) => ({
          source: s.source,
          count: s.results_count,
          error: s.error,
        })),
      });

      // Send shadow merge flags
      for (const flag of result.shadowMergeFlags) {
        sendEvent("shadow_merge", flag);
      }

      // Send deduplicated results
      for (const sourceResult of result.deduplicated) {
        for (const paper of sourceResult.raw_results) {
          sendEvent("paper", {
            _source: sourceResult.source,
            paper,
          });
        }
      }

      // Send completion
      sendEvent("done", {
        searchId: result.searchId,
        totalResults: result.totalDeduplicated,
        durationMs: result.durationMs,
      });
    } catch (error) {
      sendEvent("error", {
        message: error instanceof Error ? error.message : String(error),
      });
    } finally {
      reply.raw.end();
    }
  });

  /**
   * POST /api/search/sync — Synchronous search (no SSE)
   */
  app.post<{
    Body: SearchQuery;
  }>("/search/sync", async (request, reply) => {
    const query = request.body as SearchQuery;

    if (!query?.raw_query) {
      return reply.status(400).send({ error: "raw_query is required" });
    }

    try {
      const result = await orchestrateSearch(query);

      return reply.send({
        searchId: result.searchId,
        totalRaw: result.totalRaw,
        totalDeduplicated: result.totalDeduplicated,
        duplicatesRemoved: result.duplicatesRemoved,
        entityBlockedCount: result.entityBlockedCount,
        durationMs: result.durationMs,
        shadowMergeCount: result.shadowMergeFlags.length,
        shadowMergeFlags: result.shadowMergeFlags,
        degradedSources: result.degradedSources,
        frozenWeights: result.frozenWeights,
        weightsFrozenAt: result.weightsFrozenAt,
        needsLocalIntersection: result.needsLocalIntersection,
        cardinalityPivot: result.cardinalityPivot,
        andUnsafeSources: result.andUnsafeSources,
        compiledQueries: Object.fromEntries(result.compiledQueries),
        results: result.deduplicated.flatMap((s) =>
          s.raw_results.map((paper) => normalizePaper(paper, s.source, result.degradedSources)),
        ),
      });
    } catch (error) {
      return reply.status(500).send({
        error: error instanceof Error ? error.message : String(error),
      });
    }
  });
}
