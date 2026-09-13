import { createHash } from "crypto";

// ============================================
// Text Normalization
// ============================================

/**
 * Normalize a title for deduplication purposes.
 * Lowercase, remove punctuation, collapse whitespace, normalize Unicode.
 */
export function normalizeTitle(title: string): string {
  // Handle non-string inputs (arrays, null, undefined)
  if (!title) return "";
  let str: string;
  if (Array.isArray(title)) {
    str = title[0] ?? "";
  } else if (typeof title === "string") {
    str = title;
  } else {
    str = String(title);
  }
  
  return str
    .toLowerCase()
    .normalize("NFKD")                    // Decompose Unicode characters
    .replace(/[\u0300-\u036f]/g, "")      // Remove combining diacritical marks
    .replace(/[^\w\s]/g, " ")             // Replace non-word chars with space
    .replace(/\s+/g, " ")                 // Collapse whitespace
    .trim();
}

/**
 * Normalize an author name for deduplication.
 * Handle common variations: "J. Smith" vs "Smith, J.A." vs "John Smith"
 */
export function normalizeAuthorName(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u306f]/g, "")
    .replace(/[.,;:]/g, " ")              // Remove punctuation
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Extract the surname from an author name string.
 * Handles formats: "Last, First", "First Last", "Last, F.M."
 */
export function extractSurname(name: string): string {
  // If comma-separated, assume "Last, First" format
  if (name.includes(",")) {
    return normalizeAuthorName(name.split(",")[0]!);
  }

  // Otherwise assume "First Last" — take last word
  const parts = normalizeAuthorName(name).split(" ");
  return parts[parts.length - 1] || "";
}

// ============================================
// Entity-Aware Blocking
// ============================================
//
// In clinical literature, entirely distinct RCTs often share nearly
// identical titles differing only by geography or methodology.
// "Efficacy of Treatment X in a Malaysian Cohort" vs "Singaporean Cohort"
// must NOT be auto-merged even if Jaro-Winkler > 0.92.

// Geographic entities: countries, regions, demographic modifiers
const GEO_ENTITIES = new Set([
  // Countries
  "malaysia", "singapore", "indonesia", "thailand", "philippines", "vietnam",
  "china", "japan", "korea", "india", "pakistan", "bangladesh", "sri lanka",
  "usa", "united states", "us", "uk", "united kingdom", "canada", "australia",
  "germany", "france", "italy", "spain", "netherlands", "sweden", "norway",
  "brazil", "mexico", "argentina", "colombia", "chile", "peru",
  "egypt", "south africa", "nigeria", "kenya", "ethiopia", "ghana",
  "saudi arabia", "uae", "qatar", "kuwait", "oman", "bahrain",
  "turkey", "iran", "iraq", "israel", "jordan", "lebanon",
  "russia", "ukraine", "poland", "czech", "hungary", "romania",
  "taiwan", "hong kong", "macau",
  // Regional modifiers
  "urban", "rural", "suburban", "metropolitan",
  "asian", "african", "european", "american", "middle eastern",
  "tropical", "temperate",
]);

// Methodological entities: study design, phase, trial type
const METHOD_ENTITIES = new Set([
  // Study phases
  "phase i", "phase 1", "phase ii", "phase 2", "phase iii", "phase 3",
  "phase iv", "phase 4", "pilot", "feasibility",
  // Study designs
  "rct", "randomized controlled trial", "randomised controlled trial",
  "cohort", "prospective", "retrospective", "cross-sectional",
  "case-control", "case control", "longitudinal",
  "meta-analysis", "meta analysis", "systematic review",
  "network meta-analysis", "umbrella review",
  "case series", "case report", "case study",
  "open-label", "open label", "double-blind", "double blind",
  "single-blind", "single blind", "sham-controlled", "sham controlled",
  // Intervention types
  "phase ii", "phase iii", "treatment", "intervention", "therapy",
  "placebo", "vehicle", "active comparator",
]);

// ============================================
// Diagnostic / Anatomical Lexicon
// ============================================
//
// In clinical literature, identical titles often differ only by
// the anatomical target or specific condition. These MUST block auto-merge.

const DIAGNOSTIC_ENTITIES = new Set([
  // Ophthalmology
  "glaucoma", "cataract", "cataracts", "macular degeneration", "amd",
  "diabetic retinopathy", "retinal detachment", "retinal vein occlusion",
  "keratoconus", "dry eye", "dry eye disease", "blepharitis",
  "conjunctivitis", "uveitis", "iritis", "episcleritis", "scleritis",
  "strabismus", "amblyopia", "ptosis", "chalazion", "hordeolum",
  "corneal ulcer", "corneal erosion", "fuchs dystrophy",
  "keratitis", "endophthalmitis", "vitrectomy", "retinopathy",
  "presbyopia", "myopia", "hyperopia", "astigmatism",
  "optic neuritis", "optic neuropathy", "papilledema",
  "nystagmus", "color vision deficiency", "visual field defect",
  // General clinical
  "diabetes", "diabetes mellitus", "type 1 diabetes", "type 2 diabetes",
  "hypertension", "hypotension", "obesity", "bmi",
  "alzheimer", "alzheimer disease", "parkinson", "parkinson disease",
  "stroke", "myocardial infarction", "heart failure",
  "asthma", "copd", "pneumonia", "bronchitis",
  "arthritis", "rheumatoid arthritis", "osteoarthritis",
  "depression", "anxiety", "bipolar", "schizophrenia",
  "epilepsy", "seizure", "migraine", "headache",
  "chronic pain", "fibromyalgia", "neuropathy",
  "anemia", "leukemia", "lymphoma", "melanoma",
  "pregnancy", "gestational", "prenatal", "postpartum",
  "pediatric", "neonatal", "geriatric", "elderly",
  // Treatment modalities
  "laser", "photocoagulation", "cryotherapy", "cryopexy",
  "intravitreal", "subconjunctival", "topical", "systemic",
  "surgical", "phacoemulsification", "vitrectomy", "trabeculectomy",
  "implant", "injection", "drops", "ointment",
  "photodynamic therapy", "radiation therapy", "chemotherapy",
]);

export interface ExtractedEntities {
  geo: Set<string>;
  method: Set<string>;
  diagnostic: Set<string>;
}

/**
 * Extract geographic, methodological, and diagnostic entities from a title string.
 */
export function extractEntities(title: string): ExtractedEntities {
  const lower = normalizeTitle(title);
  const words = lower.split(/\s+/);

  const geo = new Set<string>();
  const method = new Set<string>();
  const diagnostic = new Set<string>();

  // Check multi-word geographic entities first
  for (const entity of GEO_ENTITIES) {
    if (entity.includes(" ") && lower.includes(entity)) {
      geo.add(entity);
    }
  }

  // Check multi-word methodological entities
  for (const entity of METHOD_ENTITIES) {
    if (entity.includes(" ") && lower.includes(entity)) {
      method.add(entity);
    }
  }

  // Check multi-word diagnostic entities
  for (const entity of DIAGNOSTIC_ENTITIES) {
    if (entity.includes(" ") && lower.includes(entity)) {
      diagnostic.add(entity);
    }
  }

  // Check single-word entities
  for (const word of words) {
    if (GEO_ENTITIES.has(word)) geo.add(word);
    if (METHOD_ENTITIES.has(word)) method.add(word);
    if (DIAGNOSTIC_ENTITIES.has(word)) diagnostic.add(word);
  }

  // Also check for numeric patterns: "phase ii", "phase 2", etc.
  const phaseMatch = lower.match(/phase\s*(i{1,4}v?|1|2|3|4)/);
  if (phaseMatch) method.add(phaseMatch[0]);

  return { geo, method, diagnostic };
}

/**
 * Check if two titles have conflicting entities.
 * Returns true if entities differ, meaning auto-merge should be blocked.
 */
export function hasConflictingEntities(title1: string, title2: string): boolean {
  const e1 = extractEntities(title1);
  const e2 = extractEntities(title2);

  // If neither has any entities, don't block
  const anyEntities =
    e1.geo.size > 0 || e2.geo.size > 0 ||
    e1.method.size > 0 || e2.method.size > 0 ||
    e1.diagnostic.size > 0 || e2.diagnostic.size > 0;
  if (!anyEntities) return false;

  // Check geographic conflict
  if (e1.geo.size > 0 && e2.geo.size > 0) {
    const geoOverlap = [...e1.geo].some(g => e2.geo.has(g));
    if (!geoOverlap) return true;
  }

  // Check methodological conflict
  if (e1.method.size > 0 && e2.method.size > 0) {
    const methodOverlap = [...e1.method].some(m => e2.method.has(m));
    if (!methodOverlap) return true;
  }

  // Check diagnostic/clinical conflict
  if (e1.diagnostic.size > 0 && e2.diagnostic.size > 0) {
    const diagOverlap = [...e1.diagnostic].some(d => e2.diagnostic.has(d));
    if (!diagOverlap) return true;
  }

  return false;
}

// ============================================
// Deterministic Hashing
// ============================================

/**
 * Generate a deterministic deduplication hash from normalized title + year + first author surname.
 * Uses SHA-256 for collision resistance.
 */
export function computeDeduplicationHash(
  title: string,
  year: number,
  firstAuthorName: string,
): string {
  const normalizedTitle = normalizeTitle(title);
  const normalizedAuthor = extractSurname(firstAuthorName);

  const input = `${normalizedTitle}|${year}|${normalizedAuthor}`;

  return createHash("sha256").update(input).digest("hex");
}

/**
 * Compute a DOI-based hash (lowercased, stripped of prefix).
 */
export function normalizeDoi(doi: string): string {
  return doi
    .toLowerCase()
    .replace(/^https?:\/\/doi\.org\//, "")
    .replace(/^doi:/, "")
    .trim();
}

export function computeDoiHash(doi: string): string {
  const normalized = normalizeDoi(doi);
  return createHash("sha256").update(normalized).digest("hex");
}

// ============================================
// String Similarity
// ============================================

/**
 * Jaro-Winkler similarity between two strings.
 * Returns a value between 0 (no similarity) and 1 (identical).
 */
export function jaroWinklerSimilarity(s1: string, s2: string): number {
  if (s1 === s2) return 1;
  if (s1.length === 0 || s2.length === 0) return 0;

  const matchWindow = Math.floor(Math.max(s1.length, s2.length) / 2) - 1;
  if (matchWindow < 0) return 0;

  const s1Matches = new Array(s1.length).fill(false);
  const s2Matches = new Array(s2.length).fill(false);

  let matches = 0;
  let transpositions = 0;

  // Count matches
  for (let i = 0; i < s1.length; i++) {
    const start = Math.max(0, i - matchWindow);
    const end = Math.min(i + matchWindow + 1, s2.length);

    for (let j = start; j < end; j++) {
      if (s2Matches[j] || s1[i] !== s2[j]) continue;
      s1Matches[i] = true;
      s2Matches[j] = true;
      matches++;
      break;
    }
  }

  if (matches === 0) return 0;

  // Count transpositions
  let k = 0;
  for (let i = 0; i < s1.length; i++) {
    if (!s1Matches[i]) continue;
    while (!s2Matches[k]) k++;
    if (s1[i] !== s2[k]) transpositions++;
    k++;
  }

  const jaro =
    (matches / s1.length +
      matches / s2.length +
      (matches - transpositions / 2) / matches) /
    3;

  // Winkler modification
  let prefix = 0;
  for (let i = 0; i < Math.min(4, s1.length, s2.length); i++) {
    if (s1[i] === s2[i]) prefix++;
    else break;
  }

  return jaro + prefix * 0.1 * (1 - jaro);
}

/**
 * Check if two titles are duplicates based on similarity threshold.
 * ENHANCED: Even if Jaro-Winkler exceeds threshold, entity-aware blocking
 * can prevent auto-merge when geographic or methodological entities differ.
 */
export function areTitlesDuplicate(
  title1: string,
  title2: string,
  threshold: number = 0.92,
): boolean {
  const norm1 = normalizeTitle(title1);
  const norm2 = normalizeTitle(title2);

  if (norm1 === norm2) return true;

  const similarity = jaroWinklerSimilarity(norm1, norm2);
  if (similarity < threshold) return false;

  // Entity-aware blocking: even with high similarity, block auto-merge
  // if titles contain conflicting geographic or methodological entities.
  if (hasConflictingEntities(title1, title2)) {
    return false;
  }

  return true;
}

// ============================================
// Shadow Merge Protocol
// ============================================
//
// Papers in the Jaro-Winkler grey zone (0.85–0.92) with matching
// years are NOT auto-merged. Instead, they are flagged as potential
// duplicates and streamed to the UI for clinician adjudication.

export const GREY_ZONE_LOWER = 0.85;
export const GREY_ZONE_UPPER = 0.92;

export interface ShadowMergeCandidate {
  /** The similarity score (0–1) */
  similarity: number;
  /** Whether the years match */
  yearMatch: boolean;
  /** Whether the first author surname matches */
  authorMatch: boolean;
}

export interface ShadowMergeFlag {
  /** Unique ID of the paper this flag is tethered to */
  pairedPaperId: string;
  /** The source of the paired paper */
  pairedSource: string;
  /** Title of the paired paper */
  pairedTitle: string;
  /** Similarity score */
  similarity: number;
  /** Reason codes for why this is a potential duplicate */
  reasons: string[];
}

/**
 * Check if two papers fall in the Shadow Merge grey zone.
 * Returns a flag if they are potential duplicates, null otherwise.
 */
export function checkShadowMerge(
  title1: string,
  title2: string,
  year1: number | undefined,
  year2: number | undefined,
  firstAuthor1: string,
  firstAuthor2: string,
  paperId: string,
  pairedSource: string,
  pairedTitle: string,
): ShadowMergeFlag | null {
  const norm1 = normalizeTitle(title1);
  const norm2 = normalizeTitle(title2);

  // Exact match → definite duplicate (handled by auto-merge)
  if (norm1 === norm2) return null;

  const similarity = jaroWinklerSimilarity(norm1, norm2);

  // Below grey zone → not a duplicate
  if (similarity < GREY_ZONE_LOWER) return null;

  // Above grey zone → definite duplicate (handled by auto-merge)
  if (similarity >= GREY_ZONE_UPPER) return null;

  // In grey zone — check secondary signals
  const yearMatch = year1 !== undefined && year2 !== undefined && year1 === year2;

  // Must have at least one corroborating signal
  const reasons: string[] = [`title_similarity_${similarity.toFixed(3)}`];
  if (yearMatch) reasons.push("year_match");

  // Check first author surname match
  const surname1 = extractSurname(firstAuthor1);
  const surname2 = extractSurname(firstAuthor2);
  const authorMatch = surname1.length > 0 && surname2.length > 0 && surname1 === surname2;
  if (authorMatch) reasons.push("author_match");

  // Need at least year OR author match to flag
  if (!yearMatch && !authorMatch) return null;

  return {
    pairedPaperId: paperId,
    pairedSource,
    pairedTitle,
    similarity,
    reasons,
  };
}
