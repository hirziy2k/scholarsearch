// ============================================
// Document Tier Classification
// ============================================
//
// Classifies documents into peer-review and grey literature tiers.
// Uses a PRIORITY HIERARCHY, not naive DOI regex:
//   1. Crossref `type` field + publisher member ID
//   2. PubMed `PublicationType` array
//   3. Structural title/abstract triggers + institutional publisher names
//
// This ensures clinical guidelines published in commercial journals
// are NOT algorithmically buried beneath less relevant RCTs.

// ============================================
// Helpers
// ============================================

function safeLower(val: unknown): string {
  if (val == null) return "";
  if (typeof val === "string") return val.toLowerCase();
  if (Array.isArray(val)) return val.map(safeLower).join(" ");
  return String(val).toLowerCase();
}

// ============================================
// Peer-Review Tiers (L1-L6)
// ============================================

export enum PeerReviewTier {
  /** Systematic reviews, Cochrane reviews */
  L1_SYSTEMATIC_REVIEW = 1,
  /** Meta-analyses */
  L2_META_ANALYSIS = 2,
  /** Randomized controlled trials */
  L3_RANDOMIZED_CONTROLLED = 3,
  /** Controlled observational studies (cohort, case-control) */
  L4_CONTROLLED_OBSERVATIONAL = 4,
  /** Case series, case reports, narrative reviews */
  L5_CASE_SERIES = 5,
  /** Unclassified or non-peer-reviewed */
  L6_UNCLASSIFIED = 6,
}

// ============================================
// Grey Literature Tiers (GL1-GL6)
// ============================================

export enum GreyLiteratureTier {
  /** Clinical practice guidelines (NICE, AAO, RANZCO, MOH) */
  GL1_CLINICAL_GUIDELINE = 1,
  /** Technical standards (ISO, BSI, JTC, ANSI) */
  GL2_TECHNICAL_STANDARD = 2,
  /** Government policy documents, ministry circulars */
  GL3_GOVERNMENT_POLICY = 3,
  /** Institutional protocols, hospital SOPs, training modules */
  GL4_INSTITUTIONAL_PROTOCOL = 4,
  /** Verified theses and dissertations */
  GL5_THESIS = 5,
  /** Conference abstracts, preprints, white papers, other grey */
  GL6_OTHER_GREY = 6,
}

export interface TierClassification {
  peerReviewTier: PeerReviewTier;
  greyLiteratureTier: GreyLiteratureTier | null;
  documentType: string;
  tierSource: "crossref_type" | "pubmed_type" | "structural_regex" | "inferred";
  confidence: number; // 0-1
}

// ============================================
// Crossref Type → Peer Review Tier Mapping
// ============================================
//
// Crossref uses `type` field from the article metadata.
// This is the MOST RELIABLE signal — it's set by the publisher.

const CROSSREF_TYPE_MAP: Record<string, PeerReviewTier> = {
  "journal-article": PeerReviewTier.L5_CASE_SERIES, // Default for articles
  "review-article": PeerReviewTier.L5_CASE_SERIES,
  "meta-analysis": PeerReviewTier.L2_META_ANALYSIS,
  "systematic-review": PeerReviewTier.L1_SYSTEMATIC_REVIEW,
  "research-article": PeerReviewTier.L5_CASE_SERIES,
  "randomized-controlled-trial": PeerReviewTier.L3_RANDOMIZED_CONTROLLED,
  "clinical-trial": PeerReviewTier.L3_RANDOMIZED_CONTROLLED,
  "controlled-clinical-trial": PeerReviewTier.L3_RANDOMIZED_CONTROLLED,
  "cohort-study": PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL,
  "observational-study": PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL,
  "case-control-study": PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL,
  "case-series": PeerReviewTier.L5_CASE_SERIES,
  "case-report": PeerReviewTier.L5_CASE_SERIES,
  "report": PeerReviewTier.L6_UNCLASSIFIED,
  "standard": PeerReviewTier.L6_UNCLASSIFIED, // Standards are GL2, not peer-review
  "guideline": PeerReviewTier.L6_UNCLASSIFIED, // Guidelines are GL1, not peer-review
  "dataset": PeerReviewTier.L6_UNCLASSIFIED,
  "proceedings-article": PeerReviewTier.L6_UNCLASSIFIED,
  "posted-content": PeerReviewTier.L6_UNCLASSIFIED,
};

// ============================================
// PubMed PublicationType → Peer Review Tier Mapping
// ============================================

const PUBMED_TYPE_MAP: Record<string, PeerReviewTier> = {
  "Systematic Review": PeerReviewTier.L1_SYSTEMATIC_REVIEW,
  "Meta-Analysis": PeerReviewTier.L2_META_ANALYSIS,
  "Randomized Controlled Trial": PeerReviewTier.L3_RANDOMIZED_CONTROLLED,
  "Controlled Clinical Trial": PeerReviewTier.L3_RANDOMIZED_CONTROLLED,
  "Clinical Trial": PeerReviewTier.L3_RANDOMIZED_CONTROLLED,
  "Multicenter Study": PeerReviewTier.L3_RANDOMIZED_CONTROLLED,
  "Pragmatic Clinical Trial": PeerReviewTier.L3_RANDOMIZED_CONTROLLED,
  "Observational Study": PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL,
  "Cohort Study": PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL,
  "Case-Control Studies": PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL,
  "Cross-Sectional Studies": PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL,
  "Case Reports": PeerReviewTier.L5_CASE_SERIES,
  "Review": PeerReviewTier.L5_CASE_SERIES,
  "Journal Article": PeerReviewTier.L5_CASE_SERIES,
  "Guideline": PeerReviewTier.L6_UNCLASSIFIED, // Guidelines are GL1, not peer-review
  "Practice Guideline": PeerReviewTier.L6_UNCLASSIFIED,
  "Consensus Development Conference": PeerReviewTier.L6_UNCLASSIFIED,
};

// ============================================
// Grey Literature Classification Triggers
// ============================================

// PubMed PublicationType that indicate grey literature
const PUBMED_GREY_TYPES = new Set([
  "Guideline",
  "Practice Guideline",
  "Consensus Development Conference",
  "Technical Report",
  "Government Publication",
  "Directory",
  "Legislation",
  " laws & legislation",
]);

// Institutional publisher patterns (title contains)
const INSTITUTIONAL_PUBLISHERS = [
  "ministry of health",
  "department of health",
  "world health organization",
  "who",
  "nice",
  "national institute",
  "centers for disease control",
  "cdc",
  "food and drug administration",
  "fda",
  "american academy of ophthalmology",
  "aao",
  "royal australian",
  "ranzco",
  "college of optometrists",
  "optometric association",
  "optical council",
  "joint technical committee",
  "british standards",
  "iso",
  "ansi",
  "institution of engineers",
  "national health service",
  "nhs",
  // Ophthalmology-specific institutions
  "tear film and ocular surface society",
  "tfos",
  "international dry eye workshop",
  "dews",
  "ocular surface",
  "asia-pacific academy of ophthalmology",
  "apiaao",
  "european society of cataract and refractive surgeons",
  "escrs",
];

// Title/abstract regex triggers for grey literature
const GREY_LIT_TITLE_TRIGGERS: Array<{ regex: RegExp; tier: GreyLiteratureTier }> = [
  // Clinical guidelines
  { regex: /clinical\s+(practice\s+)?guideline/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  { regex: /preferred\s+practice\s+pattern/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  { regex: /evidence[- ]based\s+guideline/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  { regex: /management\s+of.*guideline/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  { regex: /consensus\s+(statement|guideline|recommendation)/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  { regex: /national\s+guideline/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  // Dry Eye / Ophthalmology specific guidelines
  { regex: /tfos\s+dews/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  { regex: /tear\s+film\s+and\s+ocular\s+surface\s+society/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  { regex: /dry\s+eye\s+(workshop|guideline|report|consensus)/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  { regex: /aao\s+(preferred\s+practice|guideline)/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  { regex: /international\s+dry\s+eye\s+/i, tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE },
  // Technical standards
  { regex: /technical\s+standard/i, tier: GreyLiteratureTier.GL2_TECHNICAL_STANDARD },
  { regex: /international\s+standard/i, tier: GreyLiteratureTier.GL2_TECHNICAL_STANDARD },
  { regex: /specification\s+for/i, tier: GreyLiteratureTier.GL2_TECHNICAL_STANDARD },
  { regex: /test\s+method/i, tier: GreyLiteratureTier.GL2_TECHNICAL_STANDARD },
  // Government policy
  { regex: /ministry\s+of\s+health/i, tier: GreyLiteratureTier.GL3_GOVERNMENT_POLICY },
  { regex: /government\s+(policy|circular|directive)/i, tier: GreyLiteratureTier.GL3_GOVERNMENT_POLICY },
  { regex: /national\s+(health|eye)\s+(policy|program)/i, tier: GreyLiteratureTier.GL3_GOVERNMENT_POLICY },
  // Institutional protocols
  { regex: /standard\s+operating\s+procedure/i, tier: GreyLiteratureTier.GL4_INSTITUTIONAL_PROTOCOL },
  { regex: /sop\s+for/i, tier: GreyLiteratureTier.GL4_INSTITUTIONAL_PROTOCOL },
  { regex: /protocol\s+for/i, tier: GreyLiteratureTier.GL4_INSTITUTIONAL_PROTOCOL },
  { regex: /training\s+(module|manual|handbook)/i, tier: GreyLiteratureTier.GL4_INSTITUTIONAL_PROTOCOL },
];

// ============================================
// Classification Engine
// ============================================

/**
 * Classify a paper using the PRIORITY HIERARCHY:
 *   1. Crossref type + publisher
 *   2. PubMed PublicationType
 *   3. Structural title/abstract regex + institutional publishers
 */
export function classifyDocument(
  paper: {
    // Crossref fields
    type?: string;
    publisher?: string;
    member?: string;
    // PubMed fields
    publicationTypes?: string[];
    // Common fields
    title?: string;
    abstract?: string;
    containerTitle?: string[] | string;
    source?: string;
  },
): TierClassification {
  // === Priority 1: Crossref type field ===
  if (paper.type) {
    const crossrefTier = CROSSREF_TYPE_MAP[paper.type];
    if (crossrefTier !== undefined) {
      // Check if this is actually grey literature based on publisher
      const greyTier = classifyGreyFromCrossref(paper);
      if (greyTier) {
        return {
          peerReviewTier: PeerReviewTier.L6_UNCLASSIFIED,
          greyLiteratureTier: greyTier,
          documentType: paper.type,
          tierSource: "crossref_type",
          confidence: 0.9,
        };
      }

      return {
        peerReviewTier: crossrefTier,
        greyLiteratureTier: null,
        documentType: paper.type,
        tierSource: "crossref_type",
        confidence: 0.85,
      };
    }
  }

  // === Priority 2: PubMed PublicationType ===
  if (paper.publicationTypes && paper.publicationTypes.length > 0) {
    // Check for grey literature types first
    for (const pubType of paper.publicationTypes) {
      if (PUBMED_GREY_TYPES.has(pubType)) {
        const greyTier = classifyGreyFromPubMed(pubType, paper);
        return {
          peerReviewTier: PeerReviewTier.L6_UNCLASSIFIED,
          greyLiteratureTier: greyTier.tier,
          documentType: pubType,
          tierSource: "pubmed_type",
          confidence: greyTier.confidence,
        };
      }
    }

    // Check for peer-review types (take highest tier found)
    let bestTier = PeerReviewTier.L6_UNCLASSIFIED;
    let bestType = "Journal Article";
    for (const pubType of paper.publicationTypes) {
      const tier = PUBMED_TYPE_MAP[pubType];
      if (tier !== undefined && tier < bestTier) {
        bestTier = tier;
        bestType = pubType;
      }
    }

    return {
      peerReviewTier: bestTier,
      greyLiteratureTier: null,
      documentType: bestType,
      tierSource: "pubmed_type",
      confidence: 0.8,
    };
  }

  // === Priority 3: Structural regex + institutional publishers ===
  const title = safeLower(paper.title);
  const abstract = safeLower(paper.abstract);
  const fullText = `${title} ${abstract}`;

  // Check title/abstract triggers
  for (const trigger of GREY_LIT_TITLE_TRIGGERS) {
    if (trigger.regex.test(fullText)) {
      return {
        peerReviewTier: PeerReviewTier.L6_UNCLASSIFIED,
        greyLiteratureTier: trigger.tier,
        documentType: "inferred_from_text",
        tierSource: "structural_regex",
        confidence: 0.6,
      };
    }
  }

  // Check institutional publisher
  const publisher = safeLower(paper.publisher);
  const containerTitle = safeLower(paper.containerTitle);

  for (const inst of INSTITUTIONAL_PUBLISHERS) {
    if (publisher.includes(inst) || containerTitle.includes(inst)) {
      return {
        peerReviewTier: PeerReviewTier.L6_UNCLASSIFIED,
        greyLiteratureTier: GreyLiteratureTier.GL3_GOVERNMENT_POLICY,
        documentType: "institutional_publication",
        tierSource: "structural_regex",
        confidence: 0.5,
      };
    }
  }

  // === Fallback ===
  return {
    peerReviewTier: PeerReviewTier.L6_UNCLASSIFIED,
    greyLiteratureTier: null,
    documentType: "unclassified",
    tierSource: "inferred",
    confidence: 0.3,
  };
}

// ============================================
// Helpers
// ============================================

function classifyGreyFromCrossref(paper: {
  type?: string;
  publisher?: string;
  member?: string;
}): GreyLiteratureTier | null {
  const type = paper.type ?? "";

  if (type === "guideline" || type === "standard") {
    return GreyLiteratureTier.GL1_CLINICAL_GUIDELINE;
  }
  if (type === "report") {
    return GreyLiteratureTier.GL3_GOVERNMENT_POLICY;
  }
  if (type === "standard") {
    return GreyLiteratureTier.GL2_TECHNICAL_STANDARD;
  }
  return null;
}

function classifyGreyFromPubMed(pubType: string, paper: { title?: string }): {
  tier: GreyLiteratureTier;
  confidence: number;
} {
  switch (pubType) {
    case "Guideline":
    case "Practice Guideline":
    case "Consensus Development Conference":
      return { tier: GreyLiteratureTier.GL1_CLINICAL_GUIDELINE, confidence: 0.85 };
    case "Technical Report":
      return { tier: GreyLiteratureTier.GL2_TECHNICAL_STANDARD, confidence: 0.7 };
    case "Government Publication":
      return { tier: GreyLiteratureTier.GL3_GOVERNMENT_POLICY, confidence: 0.8 };
    default:
      return { tier: GreyLiteratureTier.GL6_OTHER_GREY, confidence: 0.4 };
  }
}

/**
 * Get human-readable label for a peer review tier.
 */
export function getPeerReviewTierLabel(tier: PeerReviewTier): string {
  const labels: Record<PeerReviewTier, string> = {
    [PeerReviewTier.L1_SYSTEMATIC_REVIEW]: "Systematic Review",
    [PeerReviewTier.L2_META_ANALYSIS]: "Meta-Analysis",
    [PeerReviewTier.L3_RANDOMIZED_CONTROLLED]: "Randomized Controlled Trial",
    [PeerReviewTier.L4_CONTROLLED_OBSERVATIONAL]: "Controlled Observational",
    [PeerReviewTier.L5_CASE_SERIES]: "Case Series / Report",
    [PeerReviewTier.L6_UNCLASSIFIED]: "Unclassified",
  };
  return labels[tier];
}

/**
 * Get human-readable label for a grey literature tier.
 */
export function getGreyLiteratureTierLabel(tier: GreyLiteratureTier): string {
  const labels: Record<GreyLiteratureTier, string> = {
    [GreyLiteratureTier.GL1_CLINICAL_GUIDELINE]: "Clinical Guideline",
    [GreyLiteratureTier.GL2_TECHNICAL_STANDARD]: "Technical Standard",
    [GreyLiteratureTier.GL3_GOVERNMENT_POLICY]: "Government Policy",
    [GreyLiteratureTier.GL4_INSTITUTIONAL_PROTOCOL]: "Institutional Protocol",
    [GreyLiteratureTier.GL5_THESIS]: "Thesis / Dissertation",
    [GreyLiteratureTier.GL6_OTHER_GREY]: "Grey Literature",
  };
  return labels[tier];
}
