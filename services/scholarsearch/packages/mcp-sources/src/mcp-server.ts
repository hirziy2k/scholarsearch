#!/usr/bin/env node
/**
 * ScholarSearch MCP Sources — stdio wrapper
 *
 * Wraps existing mcp-sources clients (OpenAlex, PubMed, Semantic Scholar, Crossref,
 * CORE, ERIC, DOAJ, Scopus) via MCP stdio without rewriting core fetching.
 * Each client is exposed as a tool; orchestration (dedup, circuit-breaker) is
 * reused from @scholarsearch/shared where needed but core fetch stays in
 * per-client classes.
 *
 * Run: node dist/mcp-server.js  (or via opencode.json mcp command)
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { OpenAlexClient } from "./openalex.js";
import { PubMedClient } from "./pubmed.js";
import { SemanticScholarClient } from "./semantic-scholar.js";
import { CrossrefClient } from "./crossref.js";
import { CoreClient } from "./core.js";
import { EricClient } from "./eric.js";
import { DoajClient } from "./doaj.js";
import { ScopusClient } from "./scopus.js";
import type { SearchContext } from "./shared.js";

// Clients — reuse existing env wiring, no rewrite
const openalex = new OpenAlexClient({ email: process.env.OPENALEX_EMAIL });
const pubmed = new PubMedClient({ apiKey: process.env.NCBI_API_KEY });
const semanticScholar = new SemanticScholarClient({ apiKey: process.env.SEMANTIC_SCHOLAR_API_KEY });
const crossref = new CrossrefClient({ email: process.env.UNPAYWALL_EMAIL });
const core = new CoreClient({ apiKey: process.env.CORE_API_KEY });
const eric = new EricClient();
const doaj = new DoajClient();
const scopus = new ScopusClient({ apiKey: process.env.SCOPUS_API_KEY });

const clients: Record<string, { client: any; description: string }> = {
  openalex: { client: openalex, description: "OpenAlex — 240M works, no key" },
  pubmed: { client: pubmed, description: "PubMed — biomedical, requires NCBI_API_KEY" },
  semantic_scholar: { client: semanticScholar, description: "Semantic Scholar — SPECTER2 embeddings" },
  crossref: { client: crossref, description: "Crossref — DOI resolution, no key" },
  core: { client: core, description: "CORE — 280M OA papers" },
  eric: { client: eric, description: "ERIC — education, no key" },
  doaj: { client: doaj, description: "DOAJ — OA journals, no key" },
  scopus: { client: scopus, description: "Scopus — abstract+cit, requires SCOPUS_API_KEY" },
};

const server = new McpServer({
  name: "scholarsearch-mcp-sources",
  version: "0.1.0",
});

// Single unified search tool — delegates to existing clients, no rewrite
// Cast to any to avoid TS2589 deep instantiation with zod generics (SDK 1.10 + zod 3.23)
(server as any).tool(
  "scholarsearch_search",
  "Federated academic search across 8 sources (OpenAlex, PubMed, S2, Crossref, CORE, ERIC, DOAJ, Scopus). Uses existing mcp-sources clients; handles rate-limiting and retries internally. Returns deduplicated raw_results per source.",
  {
    query: z.string().describe("User query string (Boolean AST or natural)"),
    sources: z.array(z.string()).optional().describe("Subset of sources; default all 8 (openalex,pubmed,semantic_scholar,crossref,core,eric,doaj,scopus)"),
    maxResults: z.number().min(1).max(200).optional().describe("Max results per source"),
    timeoutMs: z.number().optional().describe("Per-source timeout ms"),
  },
  async ({ query, sources, maxResults, timeoutMs }: any) => {
    const max = maxResults ?? 10;
    const timeout = timeoutMs ?? 30000;
    const selected = sources && sources.length > 0 ? sources : Object.keys(clients);
    const results: any[] = [];
    const errors: any[] = [];

    // Parallel delegated fetch — reuses existing client.search() with SearchContext
    const promises = selected.map(async (src: any) => {
      const entry = (clients as any)[src];
      if (!entry) return;
      const ctx: SearchContext = { query, maxResults: max };
      try {
        const res = await entry.client.search(ctx);
        results.push({ source: src, query_used: (res as any).query_used ?? query, results_count: (res as any).results_count, raw_results: (res as any).raw_results.slice(0, max), duration_ms: (res as any).duration_ms });
      } catch (e: any) {
        errors.push({ source: src, error: String(e?.message ?? e) });
        results.push({ source: src, query_used: query, results_count: 0, raw_results: [], error: String(e?.message ?? e), duration_ms: 0 });
      }
    });

    // Timeout guard per batch
    await Promise.race([
      Promise.allSettled(promises),
      new Promise((_, reject) => setTimeout(() => reject(new Error(`Batch timeout ${timeout}ms`)), timeout)),
    ]).catch((e) => errors.push({ source: "batch", error: String(e) }));

    const total = results.reduce((s, r) => s + (r.results_count ?? 0), 0);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ query, sources: selected, total, results, errors }, null, 2),
        },
      ],
    };
  }
);

// Health tool — checks each client without search
(server as any).tool(
  "scholarsearch_health",
  "Check health of all 8 mcp-sources clients (no search). Returns per-source boolean.",
  {},
  async (_args: any) => {
    const health: Record<string, boolean> = {};
    for (const [name, entry] of Object.entries(clients)) {
      try {
        health[name] = await entry.client.health();
      } catch {
        health[name] = false;
      }
    }
    return { content: [{ type: "text", text: JSON.stringify(health, null, 2) }] };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Log to stderr so stdout stays pure MCP JSON-RPC
  console.error("[scholarsearch-mcp-sources] stdio ready — 8 sources wrapped, core fetch untouched");
}

main().catch((e) => {
  console.error("[scholarsearch-mcp-sources] fatal:", e);
  process.exit(1);
});
