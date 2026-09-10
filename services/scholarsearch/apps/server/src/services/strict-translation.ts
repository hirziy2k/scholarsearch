// ============================================
// Strict Translation Compiler
// ============================================
//
// For APIs that don't support Boolean operators (Crossref, Semantic Scholar),
// instead of lazily stripping operators (which collapses recall), this module:
//
// 1. Traverses the Boolean AST
// 2. Extracts all leaf nodes as individual noun phrases / unigrams
// 3. Fires parallel queries to the API — one per noun phrase
// 4. Returns the union of results
//
// The local-intersection compensator then applies the original Boolean
// logic to filter the superset, preserving full recall.
//
// This is NOT lazy stripping. It's intelligent expansion.

import type { ASTNode } from "@scholarsearch/shared";

// ============================================
// Noun Phrase Extraction
// ============================================

export interface NounPhrase {
  text: string;
  isPhrase: boolean; // true if multi-word, false if unigram
  source: string;    // Which AST node type produced this
}

/**
 * Traverse the AST and extract all leaf nodes as noun phrases.
 * AND nodes produce intersection constraints (handled locally).
 * OR nodes produce alternatives (all included).
 * NOT nodes produce exclusions (applied locally after fetch).
 */
export function extractNounPhrases(ast: ASTNode): NounPhrase[] {
  const phrases: NounPhrase[] = [];
  collectLeaves(ast, phrases);
  return phrases;
}

function collectLeaves(node: ASTNode, acc: NounPhrase[]): void {
  switch (node.type) {
    case "term":
      acc.push({
        text: node.value,
        isPhrase: node.value.split(/\s+/).length > 1,
        source: "term",
      });
      break;
    case "phrase":
      acc.push({
        text: node.value,
        isPhrase: true,
        source: "phrase",
      });
      break;
    case "and":
      // Both sides contribute noun phrases — intersection handled locally
      collectLeaves(node.left, acc);
      collectLeaves(node.right, acc);
      break;
    case "or":
      // Both sides contribute noun phrases — all included in union
      collectLeaves(node.left, acc);
      collectLeaves(node.right, acc);
      break;
    case "not":
      // NOT operand is excluded — we still fetch it for local exclusion
      collectLeaves(node.operand, acc);
      break;
  }
}

// ============================================
// Parallel Query Builder
// ============================================

export interface ParallelQuery {
  query: string;
  nounPhrase: NounPhrase;
}

/**
 * Build parallel queries from noun phrases for a specific API.
 * Each noun phrase becomes a separate query.
 * Multi-word phrases are quoted. Single terms are unquoted.
 */
export function buildParallelQueries(
  phrases: NounPhrase[],
  source: string,
): ParallelQuery[] {
  return phrases.map((phrase) => ({
    query: formatForSource(phrase.text, source),
    nounPhrase: phrase,
  }));
}

function formatForSource(text: string, source: string): string {
  const isMultiWord = text.split(/\s+/).length > 1;

  switch (source) {
    case "crossref":
      // Crossref: no Boolean; space-separated terms; >=20% must match
      // Quotes are fine for phrases
      return isMultiWord ? `"${text}"` : text;

    case "semantic_scholar":
      // S2: no Boolean; quoted phrases only native feature
      return isMultiWord ? `"${text}"` : text;

    case "openalex":
      // OpenAlex: implicit AND; free text search
      return isMultiWord ? `"${text}"` : text;

    default:
      return isMultiWord ? `"${text}"` : text;
  }
}

// ============================================
// Strict Compiler for Boolean-Unsupported APIs
// ============================================

/**
 * Compile AST for APIs that don't support Boolean operators.
 * Returns an array of parallel queries instead of a single string.
 *
 * Strategy:
 * - Extract all noun phrases from the AST
 * - Fire one query per noun phrase (parallel)
 * - Local intersection applies the original Boolean logic
 *
 * This preserves recall because:
 * - OR branches → all noun phrases included (wider net)
 * - AND branches → all noun phrases fetched, intersected locally
 * - NOT branches → noun phrase fetched, excluded locally
 */
export function compileStrict(ast: ASTNode, source: string): ParallelQuery[] {
  const phrases = extractNounPhrases(ast);

  // Deduplicate noun phrases
  const seen = new Set<string>();
  const unique: NounPhrase[] = [];
  for (const p of phrases) {
    const key = p.text.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(p);
    }
  }

  return buildParallelQueries(unique, source);
}

/**
 * Get the NOT exclusions from the AST.
 * These are applied locally after fetching the parallel queries.
 */
export function extractExclusions(ast: ASTNode): string[] {
  const exclusions: string[] = [];
  collectNotOperands(ast, exclusions);
  return exclusions;
}

function collectNotOperands(node: ASTNode, acc: string[]): void {
  switch (node.type) {
    case "not":
      // Collect all leaves under the NOT operand
      collectLeafText(node.operand, acc);
      break;
    case "and":
      collectNotOperands(node.left, acc);
      collectNotOperands(node.right, acc);
      break;
    case "or":
      collectNotOperands(node.left, acc);
      collectNotOperands(node.right, acc);
      break;
    // term/phrase: no NOT above them at this level
  }
}

function collectLeafText(node: ASTNode, acc: string[]): void {
  switch (node.type) {
    case "term":
      acc.push(node.value.toLowerCase());
      break;
    case "phrase":
      acc.push(node.value.toLowerCase());
      break;
    case "and":
      collectLeafText(node.left, acc);
      collectLeafText(node.right, acc);
      break;
    case "or":
      collectLeafText(node.left, acc);
      collectLeafText(node.right, acc);
      break;
    case "not":
      collectLeafText(node.operand, acc);
      break;
  }
}
