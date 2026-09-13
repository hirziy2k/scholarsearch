// ============================================
// Geopolitical Equity Override
// ============================================
// When evidence from ASEAN/East Asian registries is unverified (no CT.gov
// cross-reference available), this module inverts the regional weight bias
// to artificially boost locally-relevant but internationally-unverified trials.
//
// Rationale: ASEAN clinical trials often use local registries (ChiCTR, IRCT,
// CTRI, etc.) that lack CT.gov indexing. Without override, these papers get
// deprioritized by citation-count and journal-impact scoring, creating a
// systematic visibility gap for regional evidence.

export interface EquityOverrideInput {
  /** Paper's country/region of origin */
  country?: string;
  /** Paper's publisher or journal country */
  publisherCountry?: string;
  /** Whether the paper has verified trial registration */
  trialVerified: boolean;
  /** Whether the paper is from a recognized ASEAN/East Asian registry */
  fromRegionalRegistry: boolean;
  /** Current ranking scores before override */
  currentScores: Record<string, number>;
  /** User's region context */
  userRegion?: string;
}

export interface EquityOverrideResult {
  /** Adjusted scores after equity override */
  adjustedScores: Record<string, number>;
  /** Whether override was applied */
  overrideApplied: boolean;
  /** Reason for override */
  reason: string;
  /** Regions that triggered the override */
  triggeredRegions: string[];
}

// Regions eligible for equity override
const EQUITY_REGIONS = new Set([
  // ASEAN
  "MY", "SG", "ID", "TH", "PH", "VN", "MM", "KH", "LA", "BN",
  // East Asia
  "CN", "TW", "HK",
  // South Asia
  "IN", "PK", "BD", "LK", "NP",
  // Other underserved
  "EG", "NG", "KE", "ZA", "BR", "MX", "CO", "AR",
]);

// Regional registries that typically lack CT.gov indexing
const REGIONAL_REGISTRIES = new Set([
  "ChiCTR",   // China
  "IRCT",     // Iran
  "CTRI",     // India
  "JPRN",     // Japan
  "ReBEC",    // Brazil
  "ACTRN",    // Australia/NZ (sometimes indexed, sometimes not)
  "CTR",      // Chinese Taiwan
]);

// Weight factors to invert when override applies
const INVERT_FACTORS = [
  "citation_impact",
  "journal_quality",
];

// Boost factors for unverified regional evidence
const REGIONAL_BOOST = {
  citation_impact: 0.3,    // Reduce citation weight (regional papers have fewer citations)
  journal_quality: 0.2,    // Reduce journal impact weight (local journals may not be indexed)
  keyword_match: 1.3,      // Boost keyword relevance (local terminology)
  recency: 1.2,            // Boost recency (regional research may be more current)
  open_access: 1.1,        // Slight OA boost (regional often OA)
} as const;

/**
 * Apply geopolitical equity override to ranking scores.
 *
 * When a paper is from an underserved region AND has unverified trial
 * registration (i.e., not cross-referenced with CT.gov), the scoring
 * weights are adjusted to prevent systematic deprioritization.
 */
export function applyEquityOverride(input: EquityOverrideInput): EquityOverrideResult {
  const {
    country,
    publisherCountry,
    trialVerified,
    fromRegionalRegistry,
    currentScores,
    userRegion,
  } = input;

  const triggeredRegions: string[] = [];
  let shouldOverride = false;

  // Check if paper is from an equity-eligible region
  const paperRegion = country ?? publisherCountry;
  if (paperRegion && EQUITY_REGIONS.has(paperRegion)) {
    triggeredRegions.push(paperRegion);
    shouldOverride = true;
  }

  // Check if user is in same region (stronger override)
  if (userRegion && paperRegion && userRegion === paperRegion) {
    triggeredRegions.push(`same-region:${userRegion}`);
    shouldOverride = true;
  }

  // Only override for unverified regional evidence
  if (trialVerified) {
    // Verified trials don't need equity override
    shouldOverride = false;
  }

  if (!shouldOverride || triggeredRegions.length === 0) {
    return {
      adjustedScores: { ...currentScores },
      overrideApplied: false,
      reason: "No override needed",
      triggeredRegions: [],
    };
  }

  // Apply weight inversion
  const adjustedScores = { ...currentScores };

  for (const factor of INVERT_FACTORS) {
    if (adjustedScores[factor] !== undefined) {
      // Invert: multiply by the inverse of the boost factor
      const boost = REGIONAL_BOOST[factor as keyof typeof REGIONAL_BOOST] ?? 1.0;
      adjustedScores[factor] *= (1 / boost);
    }
  }

  // Apply regional boosts for non-inverted factors
  for (const [factor, boost] of Object.entries(REGIONAL_BOOST)) {
    if (factor in adjustedScores && !INVERT_FACTORS.includes(factor)) {
      adjustedScores[factor] *= boost;
    }
  }

  // Normalize scores to prevent total > 1.0
  const total = Object.values(adjustedScores).reduce((s, v) => s + v, 0);
  if (total > 0) {
    for (const key of Object.keys(adjustedScores)) {
      adjustedScores[key] /= total;
    }
  }

  const reason = shouldOverride && fromRegionalRegistry
    ? `Equity override: ${triggeredRegions.join(", ")} — unverified regional trial with local registry`
    : `Equity override: ${triggeredRegions.join(", ")} — region-matched evidence boost`;

  return {
    adjustedScores,
    overrideApplied: true,
    reason,
    triggeredRegions,
  };
}

/**
 * Check if a paper's trial registration is from a regional registry
 * (as opposed to a globally-indexed one like CT.gov or ISRCTN).
 */
export function isRegionalRegistry(registry: string): boolean {
  return REGIONAL_REGISTRIES.has(registry);
}

/**
 * Get all equity-eligible regions.
 */
export function getEquityRegions(): string[] {
  return Array.from(EQUITY_REGIONS);
}
