// ============================================
// Automated Gap Visualization
// ============================================
//
// Analyzes tier classifications and cardinality to detect research gaps.
// When a search yields zero high-quality studies but many low-quality ones,
// it renders a "Research Gap Warning" banner — turning a poor search result
// into a direct grant proposal opportunity.

import { PeerReviewTier, type TierClassification } from "./document-tiers.js";

export interface ResearchGap {
  /** Type of gap detected */
  type: "no_rcts" | "no_systematic_reviews" | "no_meta_analyses" | "low_evidence" | "regional_gap";
  /** Severity: "warning" | "critical" */
  severity: "warning" | "critical";
  /** Human-readable message */
  message: string;
  /** What's missing */
  missing: string;
  /** What's present instead */
  present: string;
  /** Suggested action for the researcher */
  suggestion: string;
  /** Audit trail: what was checked */
  auditTrail: GapAuditTrail;
}

export interface GapAuditTrail {
  /** Query parameters used */
  queryParameters: string[];
  /** Sources queried */
  sourcesQueried: string[];
  /** Taxonomy nodes checked (MeSH, ERIC descriptors, etc.) */
  taxonomyNodesChecked: string[];
  /** Tier distribution breakdown */
  tierDistribution: Record<number, number>;
  /** Total results analyzed */
  totalResultsAnalyzed: number;
  /** Timestamp of analysis */
  analyzedAt: string;
}

export interface GapAnalysisResult {
  /** Whether any gaps were detected */
  hasGaps: boolean;
  /** List of detected gaps */
  gaps: ResearchGap[];
  /** Overall evidence quality score (0-1) */
  evidenceQuality: number;
  /** Summary banner text */
  bannerText: string;
  /** Global audit trail for the entire analysis */
  globalAuditTrail: GapAuditTrail;
}

/**
 * Analyze search results for research gaps.
 *
 * @param tierClassifications - Tier classifications from the search
 * @param totalResults - Total number of results
 * @param region - Region code for regional gap detection
 * @param queryParameters - Original query parameters for audit trail
 * @param sourcesQueried - Sources that were queried
 * @returns GapAnalysisResult with detected gaps and banner text
 */
export function analyzeResearchGaps(
  tierClassifications: TierClassification[],
  totalResults: number,
  region?: string,
  queryParameters?: string[],
  sourcesQueried?: string[],
): GapAnalysisResult {
  const gaps: ResearchGap[] = [];

  // Count papers by tier
  const tierCounts: Record<number, number> = {};
  for (const tc of tierClassifications) {
    const tier = tc.peerReviewTier;
    tierCounts[tier] = (tierCounts[tier] ?? 0) + 1;
  }

  // Build global audit trail
  const globalAuditTrail: GapAuditTrail = {
    queryParameters: queryParameters ?? [],
    sourcesQueried: sourcesQueried ?? [],
    taxonomyNodesChecked: extractTaxonomyNodes(tierClassifications),
    tierDistribution: tierCounts,
    totalResultsAnalyzed: totalResults,
    analyzedAt: new Date().toISOString(),
  };

  // Calculate evidence quality score
  const evidenceQuality = calculateEvidenceQuality(tierCounts, totalResults);

  // Check for missing RCTs
  const rctCount = tierCounts[PeerReviewTier.L3_RANDOMIZED_CONTROLLED] ?? 0;
  const observationalCount = tierCounts[PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL] ?? 0;
  const caseSeriesCount = tierCounts[PeerReviewTier.L5_CASE_SERIES] ?? 0;

  if (rctCount === 0 && (observationalCount + caseSeriesCount) > 5) {
    gaps.push({
      type: "no_rcts",
      severity: "critical",
      message: `No Randomized Controlled Trials found among ${totalResults} results`,
      missing: "RCTs",
      present: `${observationalCount} observational studies, ${caseSeriesCount} case series`,
      suggestion: "This represents a critical evidence gap. Consider a grant proposal for an RCT in this area.",
      auditTrail: globalAuditTrail,
    });
  }

  // Check for missing systematic reviews
  const srCount = tierCounts[PeerReviewTier.L1_SYSTEMATIC_REVIEW] ?? 0;
  const maCount = tierCounts[PeerReviewTier.L2_META_ANALYSIS] ?? 0;

  if (srCount === 0 && maCount === 0 && totalResults > 10) {
    gaps.push({
      type: "no_systematic_reviews",
      severity: "warning",
      message: "No systematic reviews or meta-analyses found",
      missing: "Systematic reviews / Meta-analyses",
      present: `${totalResults} individual studies`,
      suggestion: "This field may benefit from a systematic review to synthesize existing evidence.",
      auditTrail: globalAuditTrail,
    });
  }

  // Check for low evidence overall
  if (evidenceQuality < 0.3 && totalResults > 0) {
    gaps.push({
      type: "low_evidence",
      severity: "warning",
      message: `Overall evidence quality is low (${Math.round(evidenceQuality * 100)}%)`,
      missing: "High-quality study designs",
      present: `Most results are case series or unclassified (${caseSeriesCount + (tierCounts[PeerReviewTier.L6_UNCLASSIFIED] ?? 0)} papers)`,
      suggestion: "Consider broadening your search terms or exploring adjacent research areas.",
      auditTrail: globalAuditTrail,
    });
  }

  // Regional gap detection
  if (region && region !== "US" && region !== "UK") {
    const regionalPapers = tierClassifications.filter(tc =>
      tc.documentType?.includes("regional") ||
      tc.tierSource?.includes("regional")
    ).length;

    if (regionalPapers === 0 && totalResults > 5) {
      gaps.push({
        type: "regional_gap",
        severity: "warning",
        message: `No region-specific studies found for ${region}`,
        missing: `Studies from ${region}`,
        present: `${totalResults} international studies`,
        suggestion: `Consider localizing the research question for the ${region} context.`,
        auditTrail: globalAuditTrail,
      });
    }
  }

  // Generate banner text
  const bannerText = generateBannerText(gaps, evidenceQuality, totalResults);

  return {
    hasGaps: gaps.length > 0,
    gaps,
    evidenceQuality,
    bannerText,
    globalAuditTrail,
  };
}

/**
 * Extract taxonomy nodes from tier classifications.
 */
function extractTaxonomyNodes(tierClassifications: TierClassification[]): string[] {
  const nodes = new Set<string>();
  for (const tc of tierClassifications) {
    if (tc.documentType) nodes.add(tc.documentType);
    if (tc.tierSource) nodes.add(tc.tierSource);
  }
  return Array.from(nodes);
}

/**
 * Calculate evidence quality score (0-1) based on tier distribution.
 */
function calculateEvidenceQuality(
  tierCounts: Record<number, number>,
  totalResults: number,
): number {
  if (totalResults === 0) return 0;

  // Weight tiers by evidence quality
  const weights: Record<number, number> = {
    [PeerReviewTier.L1_SYSTEMATIC_REVIEW]: 1.0,
    [PeerReviewTier.L2_META_ANALYSIS]: 0.95,
    [PeerReviewTier.L3_RANDOMIZED_CONTROLLED]: 0.9,
    [PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL]: 0.6,
    [PeerReviewTier.L5_CASE_SERIES]: 0.3,
    [PeerReviewTier.L6_UNCLASSIFIED]: 0.1,
  };

  let weightedSum = 0;
  for (const [tier, count] of Object.entries(tierCounts)) {
    const weight = weights[parseInt(tier)] ?? 0.1;
    weightedSum += weight * count;
  }

  return Math.min(1, weightedSum / totalResults);
}

/**
 * Generate a human-readable banner text for the gap analysis.
 */
function generateBannerText(
  gaps: ResearchGap[],
  evidenceQuality: number,
  totalResults: number,
): string {
  if (gaps.length === 0) {
    return `Evidence quality: ${Math.round(evidenceQuality * 100)}% — ${totalResults} results analyzed.`;
  }

  const criticalGaps = gaps.filter(g => g.severity === "critical");
  if (criticalGaps.length > 0) {
    return `⚠️ Research Gap Detected: ${criticalGaps[0].message}. ${criticalGaps[0].suggestion}`;
  }

  return `📊 Evidence Gap: ${gaps[0].message}. Consider exploring adjacent research areas.`;
}
