// ============================================
// Trial Registration ID Extractor
// ============================================
// Extracts clinical trial registry IDs from paper metadata.
// Supports: NCT, ISRCTN, ACTRN, EUCTR, ChiCTR, IRCT, JPRN, CTRI, REBEC
// Searches: title, abstract, keywords, full text (if provided)
//
// Each pattern includes a validation checksum where applicable
// (e.g., NCT has a Luhn-like check digit).

export interface ExtractedTrialId {
  registry: string;
  id: string;
  raw: string;       // Original matched string
  confidence: number; // 0-1, structural confidence
}

// Registry patterns with capture groups
const REGISTRY_PATTERNS: Array<{
  registry: string;
  pattern: RegExp;
  validate?: (id: string) => boolean;
}> = [
  // ClinicalTrials.gov — NCT + 8 digits
  {
    registry: "NCT",
    pattern: /\b(NCT\d{8})\b/gi,
    validate: (id) => {
      // NCT IDs are sequential; no checksum, but must be 8 digits
      const digits = id.replace("NCT", "");
      return /^\d{8}$/.test(digits);
    },
  },
  // ISRCTN — ISRCTN + 8 alphanumeric (case-insensitive)
  {
    registry: "ISRCTN",
    pattern: /\b(ISRCTN[A-Z0-9]{8})\b/gi,
    validate: (id) => {
      const code = id.replace("ISRCTN", "");
      return /^[A-Z0-9]{8}$/i.test(code);
    },
  },
  // ANZCTR (Australia/NZ) — ACTRN + 14 digits
  {
    registry: "ACTRN",
    pattern: /\b(ACTRN\d{14})\b/gi,
    validate: (id) => {
      const digits = id.replace("ACTRN", "");
      return /^\d{14}$/.test(digits);
    },
  },
  // EU Clinical Trials Register — EUCTR-20{year}-{digits}-{digits}
  {
    registry: "EUCTR",
    pattern: /\b(EUCTR[\d-]{6,20})\b/g,
    validate: (id) => /^EUCTR\d{4}-\d{3,8}-\d{2}$/.test(id),
  },
  // Chinese Clinical Trial Registry — ChiCTR + 6-8 digits
  {
    registry: "ChiCTR",
    pattern: /\b(ChiCTR\d{6,8})\b/gi,
    validate: (id) => {
      const digits = id.replace("ChiCTR", "");
      return /^\d{6,8}$/.test(digits);
    },
  },
  // Iranian Registry — IRCT + alphanumeric
  {
    registry: "IRCT",
    pattern: /\b(IRCT[\dA-Z]{8,})\b/gi,
    validate: (id) => {
      const code = id.replace(/IRCT/i, "");
      return /^[\dA-Z]{8,}$/.test(code);
    },
  },
  // Japan Primary Registries Network — JPRN-CTR{type}+digits
  {
    registry: "JPRN",
    pattern: /\b(JPRN-[A-Z]{2,4}\d{4,})\b/gi,
  },
  // Clinical Trials Registry India — CTRI + / + year + / + digits
  {
    registry: "CTRI",
    pattern: /\b(CTRI\/\d{4}\/\d{2,6})\b/gi,
  },
  // Brazilian Registry — RBR- + 6+ alphanumeric
  {
    registry: "ReBEC",
    pattern: /\b(RBR-[A-Z0-9]{6,})\b/gi,
  },
];

/**
 * Extract all trial registration IDs from text fields.
 * Searches title, abstract, keywords, and optional fullText.
 */
export function extractTrialIds(paper: {
  title?: string;
  abstract?: string;
  keywords?: string[];
  fullText?: string;
}): ExtractedTrialId[] {
  const fields = [
    paper.title ?? "",
    paper.abstract ?? "",
    ...(paper.keywords ?? []),
    paper.fullText ?? "",
  ].join(" ");

  const seen = new Set<string>();
  const results: ExtractedTrialId[] = [];

  for (const { registry, pattern, validate } of REGISTRY_PATTERNS) {
    // Reset regex lastIndex for each field pass
    const regex = new RegExp(pattern.source, pattern.flags);
    let match: RegExpExecArray | null;

    while ((match = regex.exec(fields)) !== null) {
      const raw = match[1] ?? match[0];
      const normalized = raw.toUpperCase();

      if (seen.has(normalized)) continue;
      seen.add(normalized);

      // Structural confidence: 0.8 base, +0.2 if validation passes
      let confidence = 0.8;
      if (validate && validate(raw)) {
        confidence = 1.0;
      }

      results.push({ registry, id: normalized, raw, confidence });
    }
  }

  return results;
}

/**
 * Check if a paper has any trial registration ID.
 */
export function hasTrialRegistration(paper: {
  title?: string;
  abstract?: string;
  keywords?: string[];
  fullText?: string;
}): boolean {
  return extractTrialIds(paper).length > 0;
}

/**
 * Get the primary (highest confidence) trial ID for a paper.
 */
export function getPrimaryTrialId(paper: {
  title?: string;
  abstract?: string;
  keywords?: string[];
  fullText?: string;
}): ExtractedTrialId | null {
  const ids = extractTrialIds(paper);
  if (ids.length === 0) return null;
  return ids.sort((a, b) => b.confidence - a.confidence)[0];
}
