import type { RankingWeights, SearchMode } from "../schemas/search.js";
import { getPredatoryMultiplier } from "./predatory-quarantine.js";

// ============================================
// Openness-First Ranking Weights
// ============================================
// Alternative ranking mode that heavily weights OA availability,
// code availability, dataset availability, and open licenses.
// Flips the bias away from closed-access legacy journals.

export const OPENNESS_WEIGHTS: RankingWeights = {
  relevance: 0.15,
  semantic_similarity: 0.10,
  keyword_match: 0.10,
  peer_review: 0.05,
  study_design: 0.05,
  citation_impact: 0.05,
  journal_quality: 0.05,
  recency: 0.10,
  oa_availability: 0.35,  // Heavy weight on openness
};

// ============================================
// Dry Eye / Ophthalmology Domain Weights
// ============================================
// Optimized for clinical ophthalmology research.
// Heavily weights journal quality (top DED journals) and study design
// (RCTs, prospective cohort studies preferred).

export const DRY_EYE_WEIGHTS: RankingWeights = {
  relevance: 0.20,
  semantic_similarity: 0.15,
  keyword_match: 0.15,
  peer_review: 0.10,
  study_design: 0.15,     // Elevated: RCT/cohort preferred in clinical DED research
  citation_impact: 0.10,
  journal_quality: 0.10,  // Elevated: top ophthalmology journals prioritized
  recency: 0.05,
  oa_availability: 0.00,
};

// ============================================
// High-Impact Ophthalmology / Dry Eye Journals
// ============================================
// Journals with highest impact in DED research, ranked by relevance.

export const OPHTHALMOLOGY_JOURNALS: Record<string, number> = {
  // Tier 1: DED-focused / highest impact
  "ocular surface": 1.0,
  "investigative ophthalmology & visual science": 0.95,
  "iovs": 0.95,
  "american journal of ophthalmology": 0.95,
  "ophthalmology": 0.95,
  "jAMA ophthalmology": 0.9,
  "british journal of ophthalmology": 0.9,
  "cornea": 0.9,
  "eye": 0.85,
  "survey of ophthalmology": 0.85,
  "progress in retinal and eye research": 0.85,
  // Tier 2: General ophthalmology
  "clinical & experimental ophthalmology": 0.8,
  "canadian journal of ophthalmology": 0.75,
  "journal of cataract and refractive surgery": 0.75,
  "journal of refractive surgery": 0.7,
  "optometry and vision science": 0.7,
  "vision research": 0.7,
  "current eye research": 0.7,
  // Tier 3: Related specialty
  "lancet": 0.6,  // High-impact general but publishes DED
  "new england journal of medicine": 0.6,
  "bmj": 0.5,
  "plos one": 0.5,
  "scientific reports": 0.45,
};

/**
 * Get journal quality score for a paper based on journal name.
 * Returns 0 if journal not in the high-impact list.
 */
export function getJournalQualityScore(journal: string): number {
  if (!journal) return 0;
  const normalized = journal.toLowerCase().trim();
  for (const [name, score] of Object.entries(OPHTHALMOLOGY_JOURNALS)) {
    if (normalized.includes(name.toLowerCase()) || name.toLowerCase().includes(normalized)) {
      return score;
    }
  }
  return 0;
}

// ============================================
// Default Ranking Weights by Mode
// ============================================

export const DEFAULT_WEIGHTS: Record<SearchMode, RankingWeights> = {
  discovery: {
    relevance: 0.25,
    semantic_similarity: 0.20,
    keyword_match: 0.15,
    peer_review: 0.05,
    study_design: 0.05,
    citation_impact: 0.10,
    journal_quality: 0.10,
    recency: 0.10,
    oa_availability: 0.00,
  },
  evidence: {
    relevance: 0.20,
    semantic_similarity: 0.15,
    keyword_match: 0.10,
    peer_review: 0.15,
    study_design: 0.15,
    citation_impact: 0.10,
    journal_quality: 0.10,
    recency: 0.05,
    oa_availability: 0.00,
  },
  clinical: {
    relevance: 0.00,
    semantic_similarity: 0.00,
    keyword_match: 0.00,
    peer_review: 0.00,
    study_design: 0.00,
    citation_impact: 0.00,
    journal_quality: 0.00,
    recency: 0.00,
    oa_availability: 0.00,
  },
  systematic_review: {
    relevance: 0.15,
    semantic_similarity: 0.10,
    keyword_match: 0.15,
    peer_review: 0.15,
    study_design: 0.15,
    citation_impact: 0.10,
    journal_quality: 0.10,
    recency: 0.10,
    oa_availability: 0.00,
  },
  thesis: {
    relevance: 0.25,
    semantic_similarity: 0.20,
    keyword_match: 0.15,
    peer_review: 0.10,
    study_design: 0.05,
    citation_impact: 0.10,
    journal_quality: 0.10,
    recency: 0.05,
    oa_availability: 0.00,
  },
  manuscript: {
    relevance: 0.30,
    semantic_similarity: 0.25,
    keyword_match: 0.15,
    peer_review: 0.05,
    study_design: 0.05,
    citation_impact: 0.10,
    journal_quality: 0.05,
    recency: 0.05,
    oa_availability: 0.00,
  },
  citation_verification: {
    relevance: 0.00,
    semantic_similarity: 0.00,
    keyword_match: 0.00,
    peer_review: 0.00,
    study_design: 0.00,
    citation_impact: 0.00,
    journal_quality: 0.00,
    recency: 0.00,
    oa_availability: 0.00,
  },
  adversarial: {
    relevance: 0.20,
    semantic_similarity: 0.15,
    keyword_match: 0.15,
    peer_review: 0.15,
    study_design: 0.15,
    citation_impact: 0.10,
    journal_quality: 0.05,
    recency: 0.05,
    oa_availability: 0.00,
  },
  bibliometric: {
    relevance: 0.15,
    semantic_similarity: 0.10,
    keyword_match: 0.10,
    peer_review: 0.05,
    study_design: 0.05,
    citation_impact: 0.20,
    journal_quality: 0.20,
    recency: 0.15,
    oa_availability: 0.00,
  },
  openness: OPENNESS_WEIGHTS,
};

// ============================================
// Openness Score Calculator
// ============================================

export interface OpennessSignals {
  isOa?: boolean;
  hasCode?: boolean;
  hasDataset?: boolean;
  hasOpenLicense?: boolean;
  hasFullText?: boolean;
}

/**
 * Calculate an openness score (0-1) for a paper.
 * Higher scores = more open and accessible.
 * Returns NEGATIVE scores for predatory sources (quarantined).
 */
export function calculateOpennessScore(signals: OpennessSignals, paper?: any): number {
  let score = 0;
  if (signals.isOa) score += 0.35;
  if (signals.hasCode) score += 0.25;
  if (signals.hasDataset) score += 0.20;
  if (signals.hasOpenLicense) score += 0.10;
  if (signals.hasFullText) score += 0.10;

  // Predatory OA Quarantine: flip score to negative if source is flagged
  if (paper) {
    const multiplier = getPredatoryMultiplier(paper);
    if (multiplier < 0) {
      // Predatory source: invert and amplify the penalty
      return Math.max(-2.0, score * multiplier);
    }
  }

  return Math.min(1, score);
}

/**
 * Detect openness signals from a paper record.
 */
export function detectOpennessSignals(paper: any): OpennessSignals {
  const isOa = paper.isOa ?? paper.is_oa ?? false;
  const hasFullText = !!paper.fullTextUrl || !!paper.openAccessPdf;

  // Check for code availability (common indicators)
  const hasCode = !!(
    paper.codeUrl ||
    paper.code_repository ||
    paper.github_url ||
    (paper.title && /code\s+(available|at|on|in)/i.test(paper.title)) ||
    (paper.abstract && /code\s+(available|at|on|in)\s+(github|gitlab|bitbucket)/i.test(paper.abstract))
  );

  // Check for dataset availability
  const hasDataset = !!(
    paper.datasetUrl ||
    paper.data_repository ||
    paper.figshare_url ||
    paper.dryad_url ||
    (paper.title && /data\s+(available|at|on|in|set)/i.test(paper.title)) ||
    (paper.abstract && /data\s+(available|at|on|in)\s+(figshare|dryad|zenodo)/i.test(paper.abstract))
  );

  // Check for open license
  const hasOpenLicense = !!(
    paper.license &&
    /cc[-\s]?(by|by-sa|by-nc|by-nd|zero|0|pddl)/i.test(paper.license)
  );

  return { isOa, hasCode, hasDataset, hasOpenLicense, hasFullText };
}

// ============================================
// Study Design Hierarchy (Evidence Level)
// ============================================

export const STUDY_DESIGN_SCORES: Record<string, number> = {
  systematic_review: 1.0,
  meta_analysis: 1.0,
  rct: 0.9,
  cohort: 0.7,
  case_control: 0.6,
  cross_sectional: 0.5,
  case_report: 0.3,
  review: 0.4,
  editorial: 0.2,
  letter: 0.1,
  commentary: 0.2,
  preprint: 0.3,
  unknown: 0.2,
};

// ============================================
// Geographic Relevance (Clinical Mode)
// ============================================

const GEOGRAPHIC_RELEVANCE: Record<string, number> = {
  MY: 1.0, SG: 1.0, TH: 1.0, ID: 1.0, PH: 1.0,
  VN: 1.0, BN: 1.0, MM: 1.0, KH: 1.0, LA: 1.0,
  JP: 0.7, KR: 0.7, TW: 0.7, CN: 0.7, IN: 0.7,
  GB: 0.4, US: 0.4, AU: 0.4, NZ: 0.4, CA: 0.4,
};

export function getGeographicRelevance(countryCode: string | null | undefined): number {
  if (!countryCode) return 0.3;
  return GEOGRAPHIC_RELEVANCE[countryCode.toUpperCase()] ?? 0.3;
}

// ============================================
// Recency Score
// ============================================

export function computeRecencyScore(year: number, currentYear?: number): number {
  const now = currentYear ?? new Date().getFullYear();
  const age = now - year;

  if (age <= 1) return 1.0;
  if (age <= 3) return 0.8;
  if (age <= 5) return 0.6;
  if (age <= 10) return 0.4;
  return 0.2;
}

// ============================================
// Citation Impact Score (Logarithmic)
// ============================================

export function computeCitationImpactScore(
  citations: number,
  maxCitations: number,
): number {
  if (maxCitations <= 0) return 0;
  if (citations <= 0) return 0;

  return Math.min(1, Math.log(1 + citations) / Math.log(1 + maxCitations));
}

// ============================================
// Composite Score Computation
// ============================================

export interface ScoreDimensions {
  relevance: number;
  semantic_similarity: number;
  keyword_match: number;
  peer_review: number;
  study_design: number;
  citation_impact: number;
  journal_quality: number;
  recency: number;
  oa_availability: number;
}

export function computeCompositeScore(
  scores: ScoreDimensions,
  weights: RankingWeights,
): number {
  const composite =
    scores.relevance * weights.relevance +
    scores.semantic_similarity * weights.semantic_similarity +
    scores.keyword_match * weights.keyword_match +
    scores.peer_review * weights.peer_review +
    scores.study_design * weights.study_design +
    scores.citation_impact * weights.citation_impact +
    scores.journal_quality * weights.journal_quality +
    scores.recency * weights.recency +
    scores.oa_availability * weights.oa_availability;

  return Math.round(composite * 1000) / 1000; // 3 decimal places
}

/**
 * Apply retraction penalty to composite score.
 */
export function applyRetractionPenalty(
  compositeScore: number,
  retractionStatus: {
    is_retracted: boolean;
    type?: string | null;
  },
): number {
  if (retractionStatus.is_retracted && retractionStatus.type === "retraction") {
    return compositeScore * 0.01;
  }
  if (retractionStatus.is_retracted && retractionStatus.type === "expression_of_concern") {
    return compositeScore * 0.3;
  }
  if (retractionStatus.is_retracted && retractionStatus.type === "correction") {
    return compositeScore * 0.9;
  }
  return compositeScore;
}
