// ============================================
// Cardinality Circuit
// ============================================
//
// Prevents memory exhaustion from OR superset queries.
// Before fetching a broad OR superset, pre-flight checks the count.
// If it exceeds the threshold, pivots to sequential DOI intersection
// or alerts the user to tighten their query.

import type { ASTNode } from "./query-parser.js";

export const DEFAULT_CARDINALITY_THRESHOLD = 2000;

export interface CardinalityCheckResult {
  /** Whether the query is safe to fetch directly */
  safe: boolean;
  /** The estimated total results for the OR superset */
  estimatedCount: number;
  /** The threshold that was exceeded (if unsafe) */
  threshold: number;
  /** Strategy to use if unsafe */
  strategy: "direct" | "doi_intersection" | "user_alert";
  /** Individual terms for DOI intersection (if applicable) */
  individualTerms?: string[];
  /** Alert message if user action needed */
  alertMessage?: string;
}

/**
 * Extract leaf terms from an AST (all TERM and PHRASE nodes).
 */
export function extractLeafTerms(ast: ASTNode): string[] {
  switch (ast.type) {
    case "term":
      return [ast.value];
    case "phrase":
      return [ast.value];
    case "and":
    case "or":
      return [...extractLeafTerms(ast.left), ...extractLeafTerms(ast.right)];
    case "not":
      return extractLeafTerms(ast.operand);
    default:
      return [];
  }
}

/**
 * Check cardinality of an OR superset before fetching.
 *
 * @param orSupersetCount - The total-results count from a lightweight pre-flight
 * @param ast - The original query AST
 * @param threshold - Maximum safe result count (default 2000)
 */
export function checkCardinality(
  orSupersetCount: number,
  ast: ASTNode,
  threshold: number = DEFAULT_CARDINALITY_THRESHOLD,
): CardinalityCheckResult {
  const terms = extractLeafTerms(ast);

  if (orSupersetCount <= threshold) {
    return {
      safe: true,
      estimatedCount: orSupersetCount,
      threshold,
      strategy: "direct",
    };
  }

  // Too many results — decide between DOI intersection and user alert
  // If there are 2+ terms, DOI intersection is viable
  if (terms.length >= 2) {
    return {
      safe: false,
      estimatedCount: orSupersetCount,
      threshold,
      strategy: "doi_intersection",
      individualTerms: terms,
    };
  }

  // Single term that's too broad — user must tighten
  return {
    safe: false,
    estimatedCount: orSupersetCount,
    threshold,
    strategy: "user_alert",
    individualTerms: terms,
    alertMessage: `Query returned ${orSupersetCount.toLocaleString()} results (threshold: ${threshold.toLocaleString()}). Please add more specific terms to narrow your search.`,
  };
}

/**
 * Build individual AND queries for DOI intersection strategy.
 * For each term, create a separate query that will be run sequentially.
 * Results are intersected by DOI.
 */
export function buildIntersectionQueries(terms: string[]): string[] {
  // Each term gets its own query for individual fetching
  return terms.map(term => `"${term}"`);
}
