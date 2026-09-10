// ============================================
// Headless Bulk Export
// ============================================
//
// Autonomous pagination loop that fetches all pages from all sources,
// validates each page, and streams the compiled output directly to the
// client via HTTP chunked transfer encoding.
//
// Serverless-safe: returns 200 OK immediately, flushes bytes as pages
// arrive. No infinite execution window assumption.
//
// Rate limiting: 200ms delay between page fetches per source.

import type { FastifyReply } from "fastify";
import { Readable } from "stream";
import { getDb } from "../db.js";
import { fetchWithMutex } from "../utils/fetch-mutex.js";
import { validatePagePayload } from "../utils/page-validation.js";
import { checkExportGate } from "./export-gate.js";
import { createHash } from "crypto";

const PAGE_SIZE = 10;
const RATE_LIMIT_MS = 200;
const MAX_PAGES_PER_SOURCE = 500; // Safety cap: 500 pages * 10 = 5000 results max

type ExportFormat = "ris" | "csv" | "json";

// ============================================
// Source Client Map (lazy-loaded)
// ============================================

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

// ============================================
// RIS Formatter
// ============================================

function paperToRis(paper: any): string {
  const lines: string[] = [];

  const pubType = paper.publicationType ?? paper.type ?? "JOUR";
  const risType = pubType.toLowerCase().includes("journal") ? "JOUR"
    : pubType.toLowerCase().includes("book") ? "BOOK"
    : pubType.toLowerCase().includes("conference") ? "CONF"
    : "JOUR";

  lines.push(`TY  - ${risType}`);

  // Title
  const title = paper.title ?? paper.Title ?? "";
  if (Array.isArray(title)) {
    for (const t of title) lines.push(`TI  - ${t}`);
  } else if (title) {
    lines.push(`TI  - ${title}`);
  }

  // Authors
  const authors = paper.authors ?? paper.authorships ?? paper.author ?? [];
  for (const a of authors) {
    const name = typeof a === "string" ? a : a.name ?? a.Name ?? a.display_name ?? "";
    if (name) lines.push(`AU  - ${name}`);
  }

  // Year
  const year = paper.year ?? paper.publication_year;
  if (year) lines.push(`PY  - ${year}`);

  // Journal
  const journal = paper.journalName ?? paper.journal ?? paper.containerTitle ?? "";
  if (journal) lines.push(`JO  - ${journal}`);
  if (journal) lines.push(`T2  - ${journal}`);

  // DOI
  const doi = paper.doi ?? paper.DOI ?? paper.externalIds?.DOI;
  if (doi) lines.push(`DO  - ${doi}`);

  // Abstract
  const abstract = paper.abstract ?? "";
  if (abstract) lines.push(`AB  - ${abstract}`);

  // Keywords
  const keywords = paper.keywords ?? [];
  for (const kw of keywords) {
    lines.push(`KW  - ${kw}`);
  }

  // Publisher
  const publisher = paper.publisher ?? "";
  if (publisher) lines.push(`PB  - ${publisher}`);

  // URL
  const url = paper.fullTextUrl ?? paper.url ?? "";
  if (url) lines.push(`UR  - ${url}`);

  lines.push("ER  - ");
  return lines.join("\n");
}

// ============================================
// CSV Formatter
// ============================================

function papersToCsv(papers: any[]): string {
  if (papers.length === 0) return "";

  const headers = [
    "title", "authors", "year", "journal", "doi",
    "publicationType", "abstract", "keywords", "source",
  ];

  const escape = (val: string) => `"${val.replace(/"/g, '""')}"`;

  const rows = papers.map((p) => {
    const title = (p.title ?? "").toString().replace(/\n/g, " ");
    const authors = (p.authors ?? p.authorships ?? [])
      .map((a: any) => typeof a === "string" ? a : a.name ?? a.display_name ?? "")
      .join("; ");
    const year = p.year ?? "";
    const journal = p.journalName ?? p.journal ?? "";
    const doi = p.doi ?? p.DOI ?? "";
    const pubType = p.publicationType ?? p.type ?? "";
    const abstract = (p.abstract ?? "").replace(/\n/g, " ");
    const keywords = (p.keywords ?? []).join("; ");
    const source = p._source ?? "";

    return [
      escape(title), escape(authors), year, escape(journal),
      escape(doi), escape(pubType), escape(abstract),
      escape(keywords), escape(source),
    ].join(",");
  });

  return [headers.join(","), ...rows].join("\n");
}

// ============================================
// JSON Formatter
// ============================================

function papersToJson(papers: any[], watermark?: string): string {
  const output = {
    exportedAt: new Date().toISOString(),
    watermark: watermark ?? null,
    count: papers.length,
    papers: papers.map((p) => ({
      title: p.title ?? "",
      authors: p.authors ?? [],
      year: p.year ?? null,
      journal: p.journalName ?? p.journal ?? "",
      doi: p.doi ?? null,
      publicationType: p.publicationType ?? "",
      abstract: p.abstract ?? "",
      keywords: p.keywords ?? [],
      source: p._source ?? "",
    })),
  };
  return JSON.stringify(output, null, 2);
}

// ============================================
// Chunked Streaming Export
// ============================================

export interface BulkExportOptions {
  searchId: string;
  format: ExportFormat;
  reply: FastifyReply;
}

/**
 * Execute a headless bulk export with HTTP chunked streaming.
 *
 * Returns 200 OK immediately with Transfer-Encoding: chunked.
 * Each page of results is fetched, validated, formatted, and flushed
 * to the client as it arrives. No infinite execution window.
 */
export async function executeBulkExport(options: BulkExportOptions): Promise<void> {
  const { searchId, format, reply } = options;
  const db = getDb();

  const session = await db.searchSession.findFirst({ where: { searchId } });
  if (!session) {
    reply.status(404).send({ error: "Session not found" });
    return;
  }

  // Parse source statuses
  const sourceStatuses = (JSON.parse(session.sourceStatuses) as Array<{
    source: string;
    status: string;
    resultCount: number;
    hitCount: number;
  }>).map((s) => ({
    ...s,
    status: s.status as "complete" | "error" | "pending",
  }));

  // Check export gate
  const gateResult = checkExportGate(session.mode, format, sourceStatuses);
  if (!gateResult.allowed) {
    reply.status(403).send({
      error: gateResult.blockedReason,
      downgradeTo: gateResult.downgradeTo,
    });
    return;
  }

  // Set up streaming response
  reply.raw.writeHead(200, {
    "Content-Type": format === "ris" ? "application/x-research-info-systems"
      : format === "csv" ? "text/csv"
      : "application/json",
    "Transfer-Encoding": "chunked",
    "Content-Disposition": `attachment; filename="scholarsearch-${searchId}.${format}"`,
    "X-Watermark": gateResult.watermark ?? "",
  });

  const clients = await getSourceClientMap();
  const watermark = gateResult.watermark;

  let totalFlushed = 0;
  let totalErrors = 0;

  // Stream header for CSV
  if (format === "csv") {
    const header = "title,authors,year,journal,doi,publicationType,abstract,keywords,source\n";
    reply.raw.write(header);
  }

  // Stream JSON opening
  if (format === "json") {
    reply.raw.write('{"exportedAt":"' + new Date().toISOString() + '"');
    if (watermark) reply.raw.write(`,"watermark":${JSON.stringify(watermark)}`);
    reply.raw.write(',"papers":[');
  }

  let firstPaper = true;

  // Fetch each source's pages and stream results
  for (const sourceStatus of sourceStatuses) {
    const source = sourceStatus.source;
    const hitCount = sourceStatus.hitCount ?? 0;
    const totalPages = Math.min(Math.ceil(hitCount / PAGE_SIZE), MAX_PAGES_PER_SOURCE);
    const client = clients[source];

    if (!client || sourceStatus.status === "error") continue;

    for (let page = 1; page <= totalPages; page++) {
      // Fetch via mutex
      const mutexKey = `bulk:${session.id}:${source}:${page}`;

      try {
        const fetched = await fetchWithMutex(mutexKey, async () => {
          const result = await client.search({
            query: session.rawQuery,
            maxResults: PAGE_SIZE,
          });
          return {
            results: result.raw_results ?? [],
            hitCount: result.results_count ?? hitCount,
          };
        });

        // Validate
        const validation = validatePagePayload(fetched.results, page, fetched.hitCount, PAGE_SIZE);
        if (!validation.valid) {
          totalErrors++;
          continue;
        }

        // Format and flush each paper immediately
        for (const paper of fetched.results) {
          (paper as any)._source = source;

          if (format === "ris") {
            const ris = paperToRis(paper);
            reply.raw.write(ris + "\n");
          } else if (format === "csv") {
            // CSV: accumulate papers, flush per page
            // (single paper CSV would repeat headers)
            // Instead, write each row inline
            const authors = (paper.authors ?? paper.authorships ?? [])
              .map((a: any) => typeof a === "string" ? a : a.name ?? "")
              .join("; ");
            const row = [
              `"${(paper.title ?? "").toString().replace(/"/g, '""')}"`,
              `"${authors.replace(/"/g, '""')}"`,
              paper.year ?? "",
              `"${(paper.journalName ?? paper.journal ?? "").replace(/"/g, '""')}"`,
              `"${(paper.doi ?? paper.DOI ?? "").replace(/"/g, '""')}"`,
              `"${(paper.publicationType ?? paper.type ?? "").replace(/"/g, '""')}"`,
              `"${(paper.abstract ?? "").replace(/\n/g, " ").replace(/"/g, '""')}"`,
              `"${(paper.keywords ?? []).join("; ").replace(/"/g, '""')}"`,
              `"${source}"`,
            ].join(",");
            reply.raw.write(row + "\n");
          } else if (format === "json") {
            if (!firstPaper) reply.raw.write(",");
            firstPaper = false;
            const jsonPaper = JSON.stringify({
              title: paper.title ?? "",
              authors: paper.authors ?? [],
              year: paper.year ?? null,
              journal: paper.journalName ?? paper.journal ?? "",
              doi: paper.doi ?? null,
              publicationType: paper.publicationType ?? "",
              abstract: paper.abstract ?? "",
              keywords: paper.keywords ?? [],
              source,
            });
            reply.raw.write(jsonPaper);
          }

          totalFlushed++;
        }

        // Rate limit between pages
        if (page < totalPages) {
          await new Promise((resolve) => setTimeout(resolve, RATE_LIMIT_MS));
        }
      } catch (error) {
        totalErrors++;
        console.warn(`[bulk-export] Error fetching ${source} page ${page}:`, error);
      }
    }
  }

  // Stream JSON closing
  if (format === "json") {
    reply.raw.write(`],"count":${totalFlushed},"errors":${totalErrors}}`);
  }

  // Final flush and end
  reply.raw.end();

  // Record export in database
  await db.exportRecord.create({
    data: {
      sessionId: session.id,
      format,
      status: gateResult.watermark ? "complete" : "complete",
      watermarked: !!watermark,
      watermarkText: watermark ?? null,
      resultCount: totalFlushed,
      completedAt: new Date(),
    },
  });

  console.log(
    `[bulk-export] Completed: ${searchId} format=${format} flushed=${totalFlushed} errors=${totalErrors} watermarked=${!!watermark}`
  );
}
