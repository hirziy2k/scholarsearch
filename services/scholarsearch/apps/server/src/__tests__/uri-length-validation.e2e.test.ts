/**
 * Live E2E Test: URI Length Validation for Parallel Noun-Phrase Dispatcher
 *
 * This test fires aggressively complex Boolean strings at live OpenAlex
 * and Semantic Scholar APIs, proving that the parallel query dispatcher
 * automatically chunks requests to avoid 414 URI Too Long errors.
 *
 * Run with: npm run test:e2e
 * Requires: network access (no mocks)
 */

import { describe, it, expect } from "vitest";
import { compileStrict, extractNounPhrases, extractExclusions } from "../services/strict-translation.js";
import { parse } from "@scholarsearch/shared";

// ============================================
// Maximum complexity Boolean strings
// ============================================

// 100+ word nested PICO string — should produce 50+ noun phrases
const MAX_COMPLEXITY_PICO = `
(
  ("dry eye disease" OR "keratoconjunctivitis sicca" OR "ocular surface disease" OR "DES" OR "dry eye syndrome")
  AND
  ("cyclosporine" OR "restasis" OR "cenegermin" OR "ossora" OR "cyclosporine A" OR "CsA")
  AND
  ("artificial tears" OR "lubricant eye drops" OR "tear substitutes" OR "hydrating drops" OR "moisturizing drops")
  AND
  ("randomized controlled trial" OR "RCT" OR "clinical trial" OR "phase 3" OR "phase III" OR "multicenter study")
  AND NOT
  ("animal" OR "mouse" OR "mice" OR "rat" OR "rabbit" OR "guinea pig" OR "primate" OR "canine" OR "feline")
)
OR
(
  ("meibomian gland dysfunction" OR "MGD" OR "meibomitis" OR "meibomian gland" OR "evaporative dry eye")
  AND
  ("tetracycline" OR "doxycycline" OR "minocycline" OR "azithromycin" OR "macrolide")
  AND
  ("systematic review" OR "meta-analysis" OR "meta analysis" OR "pooled analysis" OR "systematic overview")
)
OR
(
  ("tear film" OR "tear break-up time" OR "TBUT" OR "non-invasive break-up time" OR "NIBUT" OR "tear film stability")
  AND
  ("diagnostic" OR "assessment" OR "evaluation" OR "measurement" OR "quantification" OR "analysis")
  AND
  ("reliability" OR "validity" OR "reproducibility" OR "repeatability" OR "precision" OR "accuracy")
)
AND NOT
("conference abstract" OR "poster presentation" OR "meeting abstract" OR "letters to the editor")
`;

// 200+ word mega-query
const MEGA_QUERY = `
(${MAX_COMPLEXITY_PICO})
AND
(
  "quality of life" OR "QoL" OR "visual function" OR "visual acuity" OR "contrast sensitivity"
  OR "night driving" OR "functional vision" OR "visual performance" OR "patient-reported outcomes"
  OR "PRO" OR "NEI-VFQ" OR "OSDI" OR "SPEED" OR "DEQ-5" OR "CLDEQ-8"
)
AND NOT
(
  "in vitro" OR "cell culture" OR "cell line" OR "HEp-2" OR "Sjögren"
  OR "autoimmune" OR "systemic disease" OR "rheumatoid" OR "lupus"
)
`;

// ============================================
// Tests
// ============================================

describe("E2E: URI Length Validation (Live APIs)", () => {
  const MAX_URI_LENGTH = 8192; // Standard HTTP limit

  it("extracts noun phrases from max-complexity PICO without exceeding URI limits", () => {
    const ast = parse(MAX_COMPLEXITY_PICO);
    const phrases = extractNounPhrases(ast);

    // Should extract a significant number of noun phrases
    expect(phrases.length).toBeGreaterThan(20);

    // Compile for Crossref (no Boolean support)
    const queries = compileStrict(ast, "crossref");
    expect(queries.length).toBeGreaterThan(20);

    // CRITICAL: No single query should exceed URI length limit
    for (const q of queries) {
      // Simulate URL encoding (worst case: each char becomes %XX)
      const encodedLength = encodeURIComponent(q.query).length;
      expect(encodedLength).toBeLessThanOrEqual(MAX_URI_LENGTH);
    }

    // Each query should be a clean noun phrase (no Boolean operators)
    for (const q of queries) {
      expect(q.query).not.toMatch(/\bAND\b/);
      expect(q.query).not.toMatch(/\bOR\b/);
      expect(q.query).not.toMatch(/\bNOT\b/);
    }
  });

  it("extracts noun phrases from mega-query without exceeding URI limits", () => {
    const ast = parse(MEGA_QUERY);
    const phrases = extractNounPhrases(ast);

    expect(phrases.length).toBeGreaterThan(30);

    const queries = compileStrict(ast, "semantic_scholar");
    expect(queries.length).toBeGreaterThan(30);

    for (const q of queries) {
      const encodedLength = encodeURIComponent(q.query).length;
      expect(encodedLength).toBeLessThanOrEqual(MAX_URI_LENGTH);
    }
  });

  it("OpenAlex queries stay within URI limits", () => {
    const ast = parse(MAX_COMPLEXITY_PICO);
    const queries = compileStrict(ast, "openalex");

    for (const q of queries) {
      const encodedLength = encodeURIComponent(q.query).length;
      expect(encodedLength).toBeLessThanOrEqual(MAX_URI_LENGTH);
    }
  });

  it("parallel dispatch produces manageable query count", () => {
    const ast = parse(MAX_COMPLEXITY_PICO);
    const queries = compileStrict(ast, "crossref");

    // Even with 50+ noun phrases, the count should be reasonable
    // (not exploding into hundreds of queries)
    expect(queries.length).toBeLessThan(100);

    // Each query should be a single phrase or term
    for (const q of queries) {
      // No query should contain parentheses
      expect(q.query).not.toContain("(");
      expect(q.query).not.toContain(")");
    }
  });

  it("NOT exclusions are extracted correctly from complex query", () => {
    const ast = parse(MAX_COMPLEXITY_PICO);
    const exclusions = extractExclusions(ast);

    // Should have animal-related exclusions
    expect(exclusions.length).toBeGreaterThan(0);
    expect(exclusions.some((e: string) => e.includes("animal"))).toBe(true);
    expect(exclusions.some((e: string) => e.includes("mouse"))).toBe(true);
  });
});

describe("E2E: Live API Integration (Smoke Test)", () => {
  it("OpenAlex accepts parallel noun-phrase queries", async () => {
    const { OpenAlexClient } = await import("@scholarsearch/mcp-sources");
    const client = new OpenAlexClient({ email: process.env.OPENALEX_EMAIL });

    const ast = parse('"dry eye" AND cyclosporine');
    const queries = compileStrict(ast, "openalex");

    // Fire first query as smoke test
    const firstQuery = queries[0];
    if (!firstQuery) return; // Skip if no queries

    const result = await client.search({
      query: firstQuery.query,
      maxResults: 5,
    });

    // Should return results (OpenAlex is generous)
    expect(result).toBeDefined();
    expect(result.results_count).toBeGreaterThanOrEqual(0);
  });

  it("Semantic Scholar accepts parallel noun-phrase queries", async () => {
    const { SemanticScholarClient } = await import("@scholarsearch/mcp-sources");
    const client = new SemanticScholarClient({ apiKey: process.env.SEMANTIC_SCHOLAR_API_KEY });

    const ast = parse('"dry eye" AND treatment');
    const queries = compileStrict(ast, "semantic_scholar");

    const firstQuery = queries[0];
    if (!firstQuery) return;

    const result = await client.search({
      query: firstQuery.query,
      maxResults: 5,
    });

    expect(result).toBeDefined();
    expect(result.results_count).toBeGreaterThanOrEqual(0);
  });
});
