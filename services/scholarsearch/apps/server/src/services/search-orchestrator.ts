import { v4 as uuidv4 } from "uuid";
import { 
  OpenAlexClient, 
  PubMedClient, 
  SemanticScholarClient, 
  CrossrefClient,
  CoreClient,
  EricClient,
  DoajClient,
  ScopusClient,
} from "@scholarsearch/mcp-sources";
import type { SearchContext, SearchResult } from "@scholarsearch/mcp-sources";
import {
  computeDeduplicationHash,
  areTitlesDuplicate,
  checkShadowMerge,
  CircuitBreakerManager,
  compileForLocalIntersection,
  evaluateAST,
  checkCardinality,
  DEFAULT_CARDINALITY_THRESHOLD,
  getERICCrosswalk,
  getDOAJCrosswalk,
  getMalayClinicalCrosswalk,
  getDryEyeCrosswalk,
  isDryEyeQuery,
  classifyDocument,
  generateQueryVersionHash,
  DEFAULT_WEIGHTS,
  analyzeResearchGaps,
  type QueryVersionHash,
  type DegradedModeAlert,
  type ShadowMergeFlag,
  type CardinalityCheckResult,
  type TierClassification,
  type GapAnalysisResult,
} from "@scholarsearch/shared";
import type { SearchQuery, SearchFilters, RankingWeights } from "@scholarsearch/shared";

// ============================================
// Source Clients
// ============================================

const openalex = new OpenAlexClient({ email: process.env.OPENALEX_EMAIL });
const pubmed = new PubMedClient({ apiKey: process.env.NCBI_API_KEY });
const semanticScholar = new SemanticScholarClient({ apiKey: process.env.SEMANTIC_SCHOLAR_API_KEY });
const crossref = new CrossrefClient({ email: process.env.UNPAYWALL_EMAIL });
const core = new CoreClient({ apiKey: process.env.CORE_API_KEY });
const eric = new EricClient();
const doaj = new DoajClient();
const scopus = new ScopusClient({ apiKey: process.env.SCOPUS_API_KEY });

// ============================================
// Source Selection by Mode
// ============================================

const SOURCE_ROUTING: Record<string, string[]> = {
  discovery: ["openalex", "semantic_scholar", "crossref", "core", "eric", "doaj", "scopus"],
  evidence: ["pubmed", "openalex", "semantic_scholar", "crossref", "core", "eric", "doaj", "scopus"],
  clinical: ["pubmed", "openalex", "semantic_scholar", "crossref", "core", "eric", "doaj", "scopus"],
  systematic_review: ["pubmed", "openalex", "semantic_scholar", "crossref", "core", "eric", "doaj", "scopus"],
  thesis: ["openalex", "semantic_scholar", "crossref", "core", "eric", "doaj", "scopus"],
  manuscript: ["openalex", "semantic_scholar", "crossref", "core", "eric", "doaj", "scopus"],
  adversarial: ["openalex", "semantic_scholar", "crossref", "core", "eric", "doaj", "scopus"],
  bibliometric: ["openalex", "crossref", "semantic_scholar", "core", "eric", "doaj"],
  citation_verification: ["crossref", "openalex", "semantic_scholar", "core"],
};

function selectSources(mode: string, customSources?: string[]): string[] {
  if (customSources && customSources.length > 0) return customSources;
  return SOURCE_ROUTING[mode] ?? SOURCE_ROUTING["discovery"]!;
}

// ============================================
// Source-Specific Filter Building
// ============================================

function buildSourceContext(
  source: string,
  compiledQuery: string,
  maxResults: number,
  filters?: SearchFilters,
): SearchContext {
  switch (source) {
    case "pubmed":
      return {
        query: compiledQuery,
        maxResults,
        filters: {
          ...(filters?.date_from ? { from_publication_date: `${filters.date_from}/01/01` } : {}),
          ...(filters?.date_to ? { to_publication_date: `${filters.date_to}/12/31` } : {}),
        },
      };
    case "openalex":
      return {
        query: compiledQuery,
        maxResults,
        filters: {
          ...(filters?.date_from ? { from_publication_date: `${filters.date_from}-01-01` } : {}),
          ...(filters?.date_to ? { to_publication_date: `${filters.date_to}-12-31` } : {}),
          ...(filters?.open_access_only ? { is_oa: "true" } : {}),
        },
      };
    default:
      return { query: compiledQuery, maxResults };
  }
}

// ============================================
// Deduplication with Shadow Merge + Entity-Aware Blocking
// ============================================

interface DedupEntry {
  hash: string;
  doi?: string;
  title: string;
  year: number;
  firstAuthor: string;
}

interface DedupResult {
  unique: SearchResult[];
  duplicatesRemoved: number;
  shadowMergeFlags: ShadowMergeFlag[];
  entityBlockedCount: number;
  totalBefore: number;
  totalAfter: number;
}

function deduplicateResults(results: SearchResult[]): DedupResult {
  const entries: DedupEntry[] = [];
  const dedupMap = new Map<string, string>();
  const uniqueResults: SearchResult[] = [];
  const shadowMergeFlags: ShadowMergeFlag[] = [];
  let entityBlockedCount = 0;

  for (const result of results) {
    const uniqueRaw: Record<string, any>[] = [];

    for (const paper of result.raw_results) {
      // --- Extract fields with full format handling ---
      const doi = paper.DOI ?? paper.doi ?? paper.externalIds?.DOI;

      let rawTitle = paper.title ?? paper.Title ?? "";
      if (Array.isArray(rawTitle)) rawTitle = rawTitle[0] ?? "";
      if (typeof rawTitle !== "string" || !rawTitle) continue;

      let year: number | undefined;
      if (typeof paper.year === "number") year = paper.year;
      else if (typeof paper.year === "string") year = parseInt(paper.year, 10);
      else if (typeof paper.publication_year === "number") year = paper.publication_year;
      else if (typeof paper.pubYear === "number") year = paper.pubYear;
      else if (paper.published?.["date-parts"]?.[0]?.[0]) year = paper.published["date-parts"][0][0];
      else if (paper.published_print?.["date-parts"]?.[0]?.[0]) year = paper.published_print["date-parts"][0][0];
      else if (paper["published-online"]?.["date-parts"]?.[0]?.[0]) year = paper["published-online"]["date-parts"][0][0];
      else if (typeof paper.sortpubdate === "string") {
        const m = paper.sortpubdate.match(/(\d{4})/);
        if (m) year = parseInt(m[1], 10);
      } else if (typeof paper.pubdate === "string") {
        const m = paper.pubdate.match(/(\d{4})/);
        if (m) year = parseInt(m[1], 10);
      }
      if (!year || isNaN(year)) continue;

      let rawAuthors = paper.authors ?? paper.authorships ?? paper.author ?? [];
      if (!Array.isArray(rawAuthors)) rawAuthors = [];
      let firstAuthor = "Unknown";
      if (rawAuthors.length > 0) {
        const a = rawAuthors[0];
        if (typeof a === "string") firstAuthor = a;
        else if (a) firstAuthor = a.name ?? a.Name ?? a.display_name ?? a.author?.name ?? "Unknown";
      }

      // --- DOI-based dedup ---
      if (doi) {
        const normalizedDoi = doi.toLowerCase().replace(/^https?:\/\/doi\.org\//, "");
        if (dedupMap.has(normalizedDoi)) {
          continue;
        }
        dedupMap.set(normalizedDoi, result.source);
      }

      // --- Hash-based dedup ---
      const hash = computeDeduplicationHash(rawTitle, year, firstAuthor);
      if (dedupMap.has(hash)) {
        continue;
      }

      // --- Title similarity check with entity-aware blocking ---
      let isDuplicate = false;
      let entityBlocked = false;
      for (const existing of entries) {
        if (Math.abs(existing.year - year) <= 1) {
          // Check for definite duplicate (above threshold)
          if (areTitlesDuplicate(existing.title, rawTitle, 0.92)) {
            isDuplicate = true;
            break;
          }

          // Check for grey-zone potential duplicate
          const flag = checkShadowMerge(
            existing.title,
            rawTitle,
            existing.year,
            year,
            existing.firstAuthor,
            firstAuthor,
            hash,
            result.source,
            rawTitle,
          );
          if (flag) {
            shadowMergeFlags.push(flag);
          }
        }
      }

      if (isDuplicate) {
        entityBlockedCount++;
        continue;
      }

      // New unique result
      dedupMap.set(hash, result.source);
      entries.push({ hash, doi, title: rawTitle, year, firstAuthor });
      uniqueRaw.push(paper);
    }

    if (uniqueRaw.length > 0) {
      uniqueResults.push({
        ...result,
        raw_results: uniqueRaw,
        results_count: uniqueRaw.length,
      });
    }
  }

  const totalBefore = results.reduce((sum, r) => sum + r.raw_results.length, 0);
  const totalAfter = uniqueResults.reduce((sum, r) => sum + r.raw_results.length, 0);

  return {
    unique: uniqueResults,
    duplicatesRemoved: totalBefore - totalAfter,
    shadowMergeFlags,
    entityBlockedCount,
    totalBefore,
    totalAfter,
  };
}

// ============================================
// Main Search Orchestrator
// ============================================

export interface SearchOrchestratorResult {
  searchId: string;
  query: string;
  compiledQueries: Map<string, string>;
  astDebug: string;
  needsLocalIntersection: boolean;
  andUnsafeSources: string[];
  cardinalityPivot: boolean;
  sources: SearchResult[];
  deduplicated: SearchResult[];
  totalRaw: number;
  totalDeduplicated: number;
  duplicatesRemoved: number;
  entityBlockedCount: number;
  shadowMergeFlags: ShadowMergeFlag[];
  degradedSources: string[];
  alerts: DegradedModeAlert[];
  frozenWeights: RankingWeights;
  weightsFrozenAt: number;
  durationMs: number;
  tierClassifications: TierClassification[];
  queryVersionHash: QueryVersionHash;
  gapAnalysis: GapAnalysisResult;
}

export type ProgressEvent =
  | { type: "source_progress"; source: string; status: "started" | "completed" | "error"; count?: number }
  | { type: "degraded"; alert: DegradedModeAlert }
  | { type: "score_frozen"; snapshot: { weights: Record<string, number>; frozenAt: number } };

export async function orchestrateSearch(
  query: SearchQuery,
  onProgress?: (event: ProgressEvent) => void,
): Promise<SearchOrchestratorResult> {
  const searchId = uuidv4();
  const startTime = Date.now();
  const alerts: DegradedModeAlert[] = [];

  // --- Step 1: Circuit breaker setup ---
  const circuitBreaker = new CircuitBreakerManager((alert) => {
    alerts.push(alert);
    onProgress?.({ type: "degraded", alert });
  });

  // --- Step 1.5: Auto-Quote Domain Phrases ---
  //
  // For domain-specific queries (e.g., dry eye), automatically detect and quote
  // multi-word phrases so the crosswalk can match them correctly.
  // This transforms "dry eye symptoms" → '"dry eye" symptoms'.
  let processedQuery = query.raw_query;
  const isDryEye = isDryEyeQuery(query.raw_query);
  console.log(`[DRY-EYE DEBUG] query="${query.raw_query}", isDryEye=${isDryEye}`);
  if (isDryEye) {
    const domainPhrases = [
      "dry eye disease", "dry eye syndrome", "dry eye",
      "tear film instability", "tear film break-up time", "tear film",
      "visual function", "functional visual acuity",
      "night driving difficulty", "night driving",
      "self-esteem", "quality of life", "vision-related quality of life",
      "osmolarity", "keratoconjunctivitis sicca",
      "meibomian gland dysfunction", "meibomian gland",
      "artificial tears", "punctal plug", "corneal staining",
      "ocular surface disease index", "dry eye questionnaire",
      "foreign body sensation", "burning sensation",
      "visual fluctuation", "glare sensitivity",
      "tear meniscus height", "non-invasive tear break-up time",
    ];

    const allPhrases = domainPhrases
      .filter((t: string) => t.includes(" "))
      .sort((a: string, b: string) => b.length - a.length);

    for (const phrase of allPhrases) {
      const lowerQuery = processedQuery.toLowerCase();
      const lowerPhrase = phrase.toLowerCase();
      const idx = lowerQuery.indexOf(lowerPhrase);
      if (idx !== -1) {
        const before = idx > 0 ? processedQuery[idx - 1] : "";
        const after = idx + phrase.length < processedQuery.length ? processedQuery[idx + phrase.length] : "";
        if (before !== '"' && after !== '"') {
          processedQuery = processedQuery.substring(0, idx) + `"${phrase}"` + processedQuery.substring(idx + phrase.length);
        }
      }
    }
  }

  // --- Step 2: AST parse + local intersection compilation ---
  const sources = selectSources(query.mode, query.sources);
  const {
    sourceQueries: compiledQueries,
    ast,
    needsLocalIntersection,
    andUnsafeSources,
  } = compileForLocalIntersection(processedQuery, sources);

  // --- Step 3: Source client map (needed by cardinality pre-flight) ---
  const clientMap: Record<string, OpenAlexClient | PubMedClient | SemanticScholarClient | CrossrefClient | CoreClient | EricClient | DoajClient> = {
    openalex,
    pubmed,
    semantic_scholar: semanticScholar,
    crossref,
    core,
    eric,
    doaj,
  };

  // --- Step 4a: Malay Clinical Vocabulary Injection ---
  //
  // Before any source-specific crosswalk, intercept Western medical terms
  // and inject locally used clinical vernacular (paracetamol, kencing manis, etc.)
  // This ensures Malaysian researchers find papers using terms they actually encounter.
  const region = query.region ?? "US"; // Default to US, can be overridden per user
  let enrichedQuery = query.raw_query;
  if (region === "MY" || region === "SG") {
    try {
      const malayCrosswalk = await getMalayClinicalCrosswalk(region);
      // Extract simple terms from the raw query for expansion
      const simpleTerms = query.raw_query
        .replace(/[()"]/g, " ")
        .split(/\s+AND\s+|\s+OR\s+|\s+NOT\s+/i)
        .map(t => t.trim())
        .filter(t => t.length > 2);

      const malayExpanded = malayCrosswalk.expandAll(simpleTerms, region);
      // Only use expansion if we found matches beyond original terms
      if (malayExpanded.length > simpleTerms.length) {
        // Build enriched query with Malay terms added as OR alternatives
        const malayTerms = malayExpanded.filter(t => !simpleTerms.includes(t));
        if (malayTerms.length > 0) {
          enrichedQuery = `${query.raw_query} OR "${malayTerms.join('" OR "')}"`;
        }
      }
    } catch {
      // Malay crosswalk unavailable — continue with original query
    }
  }

  // --- Step 4b: Crosswalk compilation for ERIC/DOAJ ---
  //
  // For ERIC and DOAJ sources, compile queries with controlled vocabulary expansion.
  // This requires the crosswalk registries to be loaded.
  const crosswalks = new Map<string, { expand(term: string, region?: string): string[] }>();
  
  if (sources.includes("eric")) {
    const ericCrosswalk = await getERICCrosswalk(region);
    crosswalks.set("eric", ericCrosswalk);
  }
  if (sources.includes("doaj")) {
    const doajCrosswalk = await getDOAJCrosswalk(region);
    crosswalks.set("doaj", doajCrosswalk);
  }

  // --- Step 4c: Domain-Specific Crosswalk (Dry Eye) ---
  //
  // Auto-detect dry eye domain queries and expand with ophthalmology vocabulary.
  // This enables precise recall for symptom subtypes, diagnostic instruments,
  // treatments, and psychosocial constructs specific to DED research.
  if (isDryEyeQuery(query.raw_query)) {
    try {
      const dryEyeCrosswalk = await getDryEyeCrosswalk(region);
      // Apply dry eye crosswalk to ALL sources for comprehensive expansion
      for (const source of sources) {
        if (!crosswalks.has(source)) {
          crosswalks.set(source, dryEyeCrosswalk);
        }
      }
    } catch {
      // Dry eye crosswalk unavailable — continue without domain expansion
    }
  }

  // Re-compile queries with crosswalk for ERIC/DOAJ/DryEye (using enriched query with Malay terms)
  if (crosswalks.size > 0) {
    const { parseAndCompileWithCrosswalk } = await import("@scholarsearch/shared");
    const crosswalkCompiled = parseAndCompileWithCrosswalk(enrichedQuery, sources, crosswalks, region);
    // Merge with existing compiled queries (ERIC/DOAJ/DryEye will be updated)
    for (const [source, compiled] of crosswalkCompiled) {
      compiledQueries.set(source, compiled);
    }
  }

  // --- Step 4: Cardinality pre-flight for AND-unsafe sources ---
  //
  // Before fetching the broad OR superset from AND-unsafe sources,
  // check if the total-results count exceeds the safe threshold.
  // If so, pivot to DOI intersection or alert the user.
  const cardinalityResults = new Map<string, CardinalityCheckResult>();

  if (needsLocalIntersection && andUnsafeSources.length > 0) {
    for (const source of andUnsafeSources) {
      const client = clientMap[source];
      if (!client || !circuitBreaker.isAvailable(source)) continue;

      const compiledQuery = compiledQueries.get(source) ?? query.raw_query;
      const context = buildSourceContext(source, compiledQuery, 1, query.filters);

      try {
        const preflight = await client.search(context);
        const count = preflight.results_count;

        const check = checkCardinality(count, ast);
        cardinalityResults.set(source, check);

        if (!check.safe) {
          if (check.strategy === "user_alert") {
            onProgress?.({ type: "degraded", alert: {
              type: "source_degraded",
              source,
              message: check.alertMessage!,
              timestamp: Date.now(),
            }});
          }
        }
      } catch {
        // If pre-flight fails, proceed normally
      }
    }
  }

  // --- Step 5: Dispatch to sources with circuit breaker ---

  const results: SearchResult[] = [];

  const promises = sources.map(async (source) => {
    if (!circuitBreaker.isAvailable(source)) {
      onProgress?.({ type: "source_progress", source, status: "error" });
      return null;
    }

    const client = clientMap[source];
    if (!client) {
      onProgress?.({ type: "source_progress", source, status: "error" });
      return null;
    }

    const compiledQuery = compiledQueries.get(source) ?? query.raw_query;
    const context = buildSourceContext(source, compiledQuery, query.max_results ?? 100, query.filters);

    onProgress?.({ type: "source_progress", source, status: "started" });

    try {
      const result = await client.search(context);
      circuitBreaker.recordSuccess(source);
      onProgress?.({ type: "source_progress", source, status: "completed", count: result.results_count });
      return result;
    } catch (error) {
      const status = (error as any)?.status ?? (error as any)?.statusCode;
      circuitBreaker.recordFailure(source, status);
      onProgress?.({ type: "source_progress", source, status: "error" });
      return {
        source,
        query_used: context.query,
        results_count: 0,
        raw_results: [],
        timestamp: new Date().toISOString(),
        duration_ms: 0,
        error: error instanceof Error ? error.message : String(error),
      } satisfies SearchResult;
    }
  });

  const settledResults = await Promise.allSettled(promises);

  for (const settled of settledResults) {
    if (settled.status === "fulfilled" && settled.value) {
      results.push(settled.value);
    }
  }

  // --- Step 5: Local intersection for AND-unsafe sources ---
  //
  // Apply exact Boolean intersection locally for sources that can't
  // faithfully handle AND operators. Also respects cardinality circuit:
  // if the OR superset was too large, results are already limited.
  let cardinalityPivot = false;
  if (needsLocalIntersection) {
    const originalAst = ast;
    for (const result of results) {
      if (andUnsafeSources.includes(result.source)) {
        const cardinalityCheck = cardinalityResults.get(result.source);

        if (cardinalityCheck && !cardinalityCheck.safe && cardinalityCheck.strategy === "doi_intersection") {
          // Cardinality pivot: fetch individual term results and intersect by DOI
          cardinalityPivot = true;
          const terms = cardinalityCheck.individualTerms ?? [];

          if (terms.length >= 2) {
            // Fetch each term separately, collect DOIs, then intersect
            const doiSets: Set<string>[] = [];

            for (const term of terms) {
              const termQuery = `"${term}"`;
              const termContext = buildSourceContext(result.source, termQuery, query.max_results ?? 100, query.filters);
              try {
                const termClient = clientMap[result.source]!;
                const termResult = await termClient.search(termContext);
                const dois = new Set<string>();
                for (const paper of termResult.raw_results) {
                  const doi = paper.DOI ?? paper.doi ?? paper.externalIds?.DOI;
                  if (doi) dois.add(doi.toLowerCase());
                }
                doiSets.push(dois);
              } catch {
                // Skip failed term queries
              }
            }

            // Intersect: keep only papers whose DOI appears in ALL term sets
            if (doiSets.length >= 2) {
              let intersection = doiSets[0]!;
              for (let i = 1; i < doiSets.length; i++) {
                intersection = new Set([...intersection].filter(d => doiSets[i]!.has(d)));
              }

              // Re-fetch the full results and filter by intersection DOIs
              const fullQuery = compiledQueries.get(result.source) ?? query.raw_query;
              const fullContext = buildSourceContext(result.source, fullQuery, query.max_results ?? 100, query.filters);
              try {
                const fullClient = clientMap[result.source]!;
                const fullResult = await fullClient.search(fullContext);
                result.raw_results = fullResult.raw_results.filter((paper: any) => {
                  const doi = paper.DOI ?? paper.doi ?? paper.externalIds?.DOI;
                  return doi && intersection.has(doi.toLowerCase());
                });
                // Tag as degraded precision — AND-unsafe source filtered locally
                for (const paper of result.raw_results) {
                  paper._degradedPrecision = true;
                }
                result.results_count = result.raw_results.length;
              } catch {
                // Fallback: apply AST intersection on whatever we have
                result.raw_results = result.raw_results.filter((paper: any) => {
                  let rawTitle = paper.title ?? paper.Title ?? "";
                  if (Array.isArray(rawTitle)) rawTitle = rawTitle[0] ?? "";
                  return evaluateAST(originalAst, rawTitle);
                });
                for (const paper of result.raw_results) {
                  paper._degradedPrecision = true;
                }
                result.results_count = result.raw_results.length;
              }
            }
          }
        } else {
          // Standard local intersection: filter by AST evaluation
          result.raw_results = result.raw_results.filter((paper: any) => {
            let rawTitle = paper.title ?? paper.Title ?? "";
            if (Array.isArray(rawTitle)) rawTitle = rawTitle[0] ?? "";
            if (typeof rawTitle !== "string") rawTitle = String(rawTitle ?? "");
            return evaluateAST(originalAst, rawTitle);
          });
          // Tag as degraded precision — AND-unsafe source filtered locally
          for (const paper of result.raw_results) {
            paper._degradedPrecision = true;
          }
          result.results_count = result.raw_results.length;
        }
      }
    }
  }

  // --- Step 5: Deduplication with Shadow Merge + Entity-Aware Blocking ---
  const { unique, duplicatesRemoved, shadowMergeFlags, entityBlockedCount } = deduplicateResults(results);

  // --- Step 5.5: Grey Literature & Peer-Review Tier Classification ---
  //
  // Classify each deduplicated paper using the priority hierarchy:
  // 1. Crossref type + publisher
  // 2. PubMed PublicationType
  // 3. Structural regex + institutional publishers
  const tierClassifications: TierClassification[] = [];
  for (const result of unique) {
    for (const paper of result.raw_results) {
      const classification = classifyDocument({
        type: paper.type,
        publisher: paper.publisher,
        member: paper.member,
        publicationTypes: paper.publicationTypes ?? (paper.pubtype ? [paper.pubtype] : undefined),
        title: paper.title,
        abstract: paper.abstract,
        containerTitle: paper.containerTitle ?? paper.journal,
        source: paper._source ?? paper.source,
      });
      tierClassifications.push(classification);
      // Attach classification to paper for downstream use
      (paper as any)._tierClassification = classification;
    }
  }

  // --- Step 6: Score Lock — freeze weights at T=0s ---
  const originalWeights: RankingWeights = query.weights ?? DEFAULT_WEIGHTS[query.mode];

  // Detect degraded sources BEFORE freezing
  const degradedSources = circuitBreaker.getDegradedSources();

  // Freeze weights — this happens exactly once per session
  const frozenSnapshot = circuitBreaker.scoreLock.freeze(
    originalWeights as Record<string, number>,
    degradedSources,
  );

  onProgress?.({
    type: "score_frozen",
    snapshot: {
      weights: frozenSnapshot.weights,
      frozenAt: frozenSnapshot.frozenAt,
    },
  });

  const totalRaw = results.reduce((sum, r) => sum + r.raw_results.length, 0);
  const totalDeduplicated = unique.reduce((sum, r) => sum + r.raw_results.length, 0);

  // --- Step 7: Cryptographic Query Versioning ---
  //
  // Hash the AST + endpoints + cardinality + top DOIs for reproducibility audit.
  // If an API changes its backend index, the hash breaks,
  // alerting the researcher that the search is no longer reproducible.
  const queriedSources = results.map(r => r.source);
  const originalAst = compileForLocalIntersection(query.raw_query, sources).ast;
  const topDois = unique
    .flatMap(r => r.raw_results)
    .map(p => p.DOI ?? p.doi ?? "")
    .filter(Boolean)
    .sort()
    .slice(0, 3);
  const queryVersionHash = generateQueryVersionHash(
    originalAst,
    queriedSources,
    region,
    totalDeduplicated,
    topDois,
  );

  // --- Step 8: Automated Gap Visualization ---
  //
  // Analyze tier classifications to detect research gaps.
  // Turn a poor search result into a grant proposal opportunity.
  const gapAnalysis = analyzeResearchGaps(
    tierClassifications,
    totalDeduplicated,
    region,
    [query.raw_query, ...Array.from(compiledQueries.values())],
    queriedSources,
  );

  return {
    searchId,
    query: query.raw_query,
    compiledQueries,
    astDebug: "", // populated by routes
    needsLocalIntersection,
    andUnsafeSources,
    cardinalityPivot,
    sources: results,
    deduplicated: unique,
    totalRaw,
    totalDeduplicated,
    duplicatesRemoved,
    entityBlockedCount,
    shadowMergeFlags,
    degradedSources,
    alerts,
    frozenWeights: frozenSnapshot.weights as RankingWeights,
    weightsFrozenAt: frozenSnapshot.frozenAt,
    durationMs: Date.now() - startTime,
    tierClassifications,
    queryVersionHash,
    gapAnalysis,
  };
}
