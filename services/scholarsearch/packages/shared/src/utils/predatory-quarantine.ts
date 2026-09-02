// ============================================
// Predatory OA Quarantine
// ============================================
//
// Cross-references DOIs, ISSNs, and publisher domains against a static
// bloom filter of known predatory journals. When a paper is flagged,
// the Openness-First ranking weight flips to a negative multiplier,
// burying it instantly.
//
// This is DETERMINISTIC — no LLM involvement. The quarantine is a
// static registry with configurable confidence thresholds.

import {
  PREDATORY_DOMAINS,
  PREDATORY_PUBLISHERS,
  PREDATORY_ISSNS,
  PREDATORY_NEGATIVE_MULTIPLIER,
  PREDATORY_CONFIDENCE_THRESHOLD,
  type PredatoryEntry,
} from "../data/predatory-publishers.js";

export interface QuarantineResult {
  /** Whether the paper is flagged as predatory */
  isPredatory: boolean;
  /** Confidence score (0-1) */
  confidence: number;
  /** Matched entry details */
  matchedEntry: PredatoryEntry | null;
  /** Which field triggered the match */
  matchedField: "domain" | "publisher" | "issn" | null;
  /** The negative multiplier to apply to oa_availability */
  negativeMultiplier: number;
}

/**
 * Check if a paper is from a predatory source.
 *
 * @param paper - The paper record to check
 * @returns QuarantineResult with confidence and match details
 */
export function checkPredatory(paper: any): QuarantineResult {
  const defaultResult: QuarantineResult = {
    isPredatory: false,
    confidence: 0,
    matchedEntry: null,
    matchedField: null,
    negativeMultiplier: 0,
  };

  // Extract paper metadata
  const doi = (paper.DOI ?? paper.doi ?? "").toLowerCase();
  const issn = (paper.ISSN ?? paper.issn ?? "").replace(/-/g, "").toLowerCase();
  const publisher = (paper.publisher ?? paper.publisherName ?? "").toLowerCase();
  const journal = (paper.containerTitle ?? paper.journal ?? paper.source ?? "").toLowerCase();
  const domain = extractDomain(doi);

  // Check domain against predatory domains
  if (domain) {
    for (const entry of PREDATORY_DOMAINS) {
      if (entry.domain && matchDomain(domain, entry.domain)) {
        if (entry.confidence >= PREDATORY_CONFIDENCE_THRESHOLD) {
          return {
            isPredatory: true,
            confidence: entry.confidence,
            matchedEntry: entry,
            matchedField: "domain",
            negativeMultiplier: PREDATORY_NEGATIVE_MULTIPLIER,
          };
        }
      }
    }
  }

  // Check publisher against predatory publishers
  if (publisher) {
    for (const entry of PREDATORY_PUBLISHERS) {
      if (entry.publisher && publisher.includes(entry.publisher)) {
        if (entry.confidence >= PREDATORY_CONFIDENCE_THRESHOLD) {
          return {
            isPredatory: true,
            confidence: entry.confidence,
            matchedEntry: entry,
            matchedField: "publisher",
            negativeMultiplier: PREDATORY_NEGATIVE_MULTIPLIER,
          };
        }
      }
    }
  }

  // Check ISSN against predatory ISSNs
  if (issn) {
    for (const entry of PREDATORY_ISSNS) {
      if (entry.issn && issn === entry.issn.replace(/-/g, "")) {
        if (entry.confidence >= PREDATORY_CONFIDENCE_THRESHOLD) {
          return {
            isPredatory: true,
            confidence: entry.confidence,
            matchedEntry: entry,
            matchedField: "issn",
            negativeMultiplier: PREDATORY_NEGATIVE_MULTIPLIER,
          };
        }
      }
    }
  }

  return defaultResult;
}

/**
 * Extract domain from a DOI or URL.
 */
function extractDomain(doi: string): string | null {
  if (!doi) return null;

  // Handle DOI URLs
  if (doi.startsWith("http")) {
    try {
      const url = new URL(doi);
      return url.hostname.toLowerCase();
    } catch {
      return null;
    }
  }

  // Handle raw DOIs (e.g., "10.1234/journal.2024.001")
  // Extract the publisher domain from the DOI prefix
  const parts = doi.split("/");
  if (parts.length >= 2) {
    // Common patterns: "10.1234/journal" → "10.1234"
    // We check the prefix against known predatory DOI prefixes
    return parts[0] ?? null;
  }

  return null;
}

/**
 * Match a domain against a pattern.
 * Supports exact match and wildcard patterns (e.g., "journal-of-*").
 */
function matchDomain(domain: string, pattern: string): boolean {
  if (pattern.includes("*")) {
    const regex = new RegExp("^" + pattern.replace(/\*/g, ".*") + "$", "i");
    return regex.test(domain);
  }
  return domain === pattern;
}

/**
 * Get the negative multiplier for a paper if it's predatory.
 * Returns 0 if the paper is clean.
 *
 * @param paper - The paper record to check
 * @returns The multiplier to apply to oa_availability (0 or PREDATORY_NEGATIVE_MULTIPLIER)
 */
export function getPredatoryMultiplier(paper: any): number {
  const result = checkPredatory(paper);
  return result.isPredatory ? result.negativeMultiplier : 0;
}
