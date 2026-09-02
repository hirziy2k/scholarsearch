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

function decodeAbstract(abstract: any): string | null {
  if (!abstract) return null;
  if (typeof abstract === "string") return abstract;
  // OpenAlex inverted index: { word: [positions] }
  if (typeof abstract === "object" && !Array.isArray(abstract)) {
    const entries: [string, number[]][] = Object.entries(abstract);
    const words: string[] = [];
    for (const [word, positions] of entries) {
      for (const pos of positions as number[]) {
        words[pos] = word;
      }
    }
    return words.filter(Boolean).join(" ");
  }
  return null;
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
  const isOa = paper.is_oa ?? (paper.openAccessPdf ? true : undefined) ?? paper.open_access?.is_oa ?? false;
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
    _degradedPrecision: !!paper._degradedPrecision,
    title: rawTitle,
    authors,
    year: extractYear(paper),
    doi,
    journal,
    abstract: decodeAbstract(paper.abstract ?? paper.abstract_inverted_index),
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
        gapAnalysis: result.gapAnalysis,
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
   * Supports ?compact=true to strip abstracts for progressive loading.
   */
  app.post<{
    Body: SearchQuery;
  }>("/search/sync", async (request, reply) => {
    const query = request.body as SearchQuery;
    const compact = (request.query as any)?.compact === "true";

    if (!query?.raw_query) {
      return reply.status(400).send({ error: "raw_query is required" });
    }

    try {
      const result = await orchestrateSearch(query);

      const papers = result.deduplicated.flatMap((s) =>
        s.raw_results.map((paper) => normalizePaper(paper, s.source, result.degradedSources)),
      );

      // In compact mode, strip abstracts to reduce payload ~60%
      const compactPapers = compact
        ? papers.map(({ abstract, ...rest }) => rest)
        : papers;

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
        tierClassifications: result.tierClassifications,
        queryVersionHash: result.queryVersionHash,
        gapAnalysis: result.gapAnalysis,
        compact,
        results: compactPapers,
      });
    } catch (error) {
      return reply.status(500).send({
        error: error instanceof Error ? error.message : String(error),
      });
    }
  });

  /**
   * GET /api/paper/abstract?doi=... — Fetch abstract on demand
   * Returns both raw abstract and 3-bullet micro-summary via LLM.
   * Used for progressive abstract loading in the frontend.
   */
  app.get("/paper/abstract", async (request, reply) => {
    const { doi } = request.query as { doi?: string };
    if (!doi) {
      return reply.status(400).send({ error: "doi is required" });
    }

    try {
      // Try Crossref first for abstract
      const { CrossrefClient } = await import("@scholarsearch/mcp-sources");
      const crossref = new CrossrefClient({});
      const result = await crossref.search({ query: `doi:${doi}`, maxResults: 1 });
      const paper = result.raw_results[0];

      let abstract = paper?.abstract ?? null;

      // Fallback: try PubMed if Crossref didn't return abstract
      if (!abstract) {
        const { PubMedClient } = await import("@scholarsearch/mcp-sources");
        const pubmed = new PubMedClient({});
        const pmResult = await pubmed.search({ query: `doi:${doi}`, maxResults: 1 });
        const pmPaper = pmResult.raw_results[0];
        abstract = pmPaper?.abstract ?? null;
      }

      // Decode OpenAlex inverted index if present
      if (abstract && typeof abstract === "object" && !Array.isArray(abstract)) {
        const entries: [string, number[]][] = Object.entries(abstract);
        const words: string[] = [];
        for (const [word, positions] of entries) {
          for (const pos of positions as number[]) {
            words[pos] = word;
          }
        }
        abstract = words.filter(Boolean).join(" ");
      }

      // Generate micro-summary via LLM (Haiku/4o-mini) with verifiable anchors
      let microSummary = null;
      let microSummaryAnchors = null;
      if (abstract && typeof abstract === "string" && abstract.length > 50) {
        try {
          const { generateMicroSummary } = await import("@scholarsearch/omniroute");
          const omniRoute = new (await import("@scholarsearch/omniroute")).OmniRoute();
          const result = await generateMicroSummary(abstract, omniRoute);
          microSummary = result.summary;
          microSummaryAnchors = result.anchors;
        } catch {
          // LLM unavailable — return raw abstract only
        }
      }

      return reply.send({
        doi,
        abstract: typeof abstract === "string" ? abstract : null,
        microSummary,
        microSummaryAnchors,
      });
    } catch (error) {
      return reply.status(500).send({
        error: error instanceof Error ? error.message : String(error),
      });
    }
  });
}
