// ============================================
// Cryptographic Query Versioning
// ============================================
//
// Hashes the AST, API endpoints, and timestamp to create a reproducibility
// audit trail. If an API changes its backend index, the hash breaks,
// alerting the researcher that the search is no longer reproducible.
//
// This is critical for PRISMA-compliant meta-analyses where search
// reproducibility is a requirement.

import { createHash } from "crypto";

export interface QueryVersionHash {
  /** SHA-256 hash of the query fingerprint */
  hash: string;
  /** ISO timestamp of when the hash was generated */
  timestamp: string;
  /** The AST structure that was hashed */
  astFingerprint: string;
  /** API endpoints that were queried */
  endpoints: string[];
  /** Region used for the search */
  region: string;
  /** Human-readable description of what was hashed */
  description: string;
}

/**
 * Generate a reproducibility hash for a search query.
 * Includes cardinality + top 3 DOIs to detect API state mutations.
 *
 * @param ast - The parsed AST (or raw query string as fallback)
 * @param endpoints - List of API endpoints/sources queried
 * @param region - Region code used for the search
 * @param cardinality - Total result count from the search
 * @param topDois - Top 3 DOIs from the result set (sorted)
 * @param timestamp - Optional custom timestamp (defaults to now)
 * @returns QueryVersionHash with the hash and metadata
 */
export function generateQueryVersionHash(
  ast: any,
  endpoints: string[],
  region: string,
  cardinality?: number,
  topDois?: string[],
  timestamp?: Date,
): QueryVersionHash {
  const ts = timestamp ?? new Date();

  // Create a deterministic fingerprint of the AST
  const astFingerprint = fingerprintAST(ast);

  // Sort endpoints for deterministic hashing
  const sortedEndpoints = [...endpoints].sort();

  // Sort and limit DOIs to top 3 for deterministic hashing
  const sortedDois = (topDois ?? [])
    .map(d => d.toLowerCase().replace(/^https?:\/\/doi\.org\//, ""))
    .sort()
    .slice(0, 3);

  // Build the hash input — includes cardinality + DOIs to detect API state mutations
  const hashInput = JSON.stringify({
    ast: astFingerprint,
    endpoints: sortedEndpoints,
    region: region.toUpperCase(),
    cardinality: cardinality ?? 0,
    topDois: sortedDois,
  });

  const hash = createHash("sha256").update(hashInput).digest("hex");

  return {
    hash,
    timestamp: ts.toISOString(),
    astFingerprint,
    endpoints: sortedEndpoints,
    region: region.toUpperCase(),
    description: `Query: ${sortedEndpoints.join("+")} @ ${region} | ${cardinality ?? "?"} results | AST: ${astFingerprint.slice(0, 16)}...`,
  };
}

/**
 * Create a fingerprint of an AST node.
 * Extracts structure (operators, term count) without values
 * to detect structural changes in API behavior.
 */
function fingerprintAST(node: any): string {
  if (!node) return "null";

  if (typeof node === "string") return `str:${node.length}`;
  if (typeof node === "number") return `num`;
  if (typeof node === "boolean") return `bool`;

  if (Array.isArray(node)) {
    return `arr:${node.length}:${node.map(fingerprintAST).join(",")}`;
  }

  if (typeof node === "object") {
    const keys = Object.keys(node).sort();
    const pairs = keys.map(k => `${k}:${fingerprintAST(node[k])}`);
    return `{${pairs.join(",")}}`;
  }

  return String(typeof node);
}

/**
 * Verify that a query version hash matches the current query structure.
 * Returns true if the hash is still valid (query structure unchanged).
 *
 * @param versionHash - The original QueryVersionHash
 * @param currentAst - The current AST to verify against
 * @param currentEndpoints - The current endpoints
 * @param currentRegion - The current region
 * @param currentCardinality - The current result count
 * @param currentTopDois - The current top 3 DOIs
 * @returns Whether the hash is still valid
 */
export function verifyQueryVersionHash(
  versionHash: QueryVersionHash,
  currentAst: any,
  currentEndpoints: string[],
  currentRegion: string,
  currentCardinality?: number,
  currentTopDois?: string[],
): boolean {
  const current = generateQueryVersionHash(
    currentAst,
    currentEndpoints,
    currentRegion,
    currentCardinality,
    currentTopDois,
  );
  return current.hash === versionHash.hash;
}
