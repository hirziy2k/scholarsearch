// ============================================
// Strict Search Dispatcher
// ============================================
//
// For APIs that don't support Boolean operators, this dispatcher:
// 1. Extracts noun phrases from the AST
// 2. Fires parallel queries (one per noun phrase)
// 3. Returns the union of results
// 4. Provides NOT exclusions for local filtering
//
// This replaces the lazy AND→OR conversion for boolean-unsupported APIs,
// preserving full recall through intelligent parallel dispatch.

import type { ASTNode } from "@scholarsearch/shared";
import {
  compileStrict,
  extractNounPhrases,
  extractExclusions,
  type ParallelQuery,
} from "./strict-translation.js";

export interface StrictDispatchResult {
  source: string;
  queries: ParallelQuery[];
  nounPhraseCount: number;
  exclusions: string[];
}

/**
 * Prepare a strict dispatch for a boolean-unsupported API.
 * Returns the parallel queries and local exclusions.
 */
export function prepareStrictDispatch(
  ast: ASTNode,
  source: string,
): StrictDispatchResult {
  const queries = compileStrict(ast, source);
  const exclusions = extractExclusions(ast);

  return {
    source,
    queries,
    nounPhraseCount: queries.length,
    exclusions,
  };
}

/**
 * Check if a paper title should be excluded based on NOT operands.
 * Used for local filtering after parallel dispatch.
 */
export function shouldExclude(
  title: string,
  exclusions: string[],
): boolean {
  if (exclusions.length === 0) return false;
  const lower = title.toLowerCase();
  return exclusions.some((excl) => lower.includes(excl));
}
