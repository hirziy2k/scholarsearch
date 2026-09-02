// ============================================
// Controlled Vocabulary Crosswalk
// ============================================
//
// Maps free-text query terms to database-specific controlled vocabularies.
// Supports regional taxonomy overlays so localized clinical education
// descriptors don't corrupt standard thesaurus mappings.
//
// This is DETERMINISTIC — no LLM involvement. The crosswalk is a static
// registry with optional runtime overlays loaded from configuration.

// ============================================
// Core Types
// ============================================

export interface VocabularyEntry {
  /** Normalized lowercase form of the descriptor */
  term: string;
  /** Source-specific identifier (e.g., ERIC "E1101", DOAJ subject ID) */
  sourceId?: string;
  /** Exact synonyms in the controlled vocabulary */
  synonyms: string[];
  /** Broader/parent terms for hierarchy navigation */
  broaderTerms: string[];
  /** Narrower/child terms for hierarchy navigation */
  narrowerTerms: string[];
  /** Scope note from the original thesaurus */
  note?: string;
  /** Relevance weight (0-1) — higher = more exact match */
  weight: number;
}

export interface RegionalOverlay {
  /** Region code (e.g., "MY", "SG", "AU", "US-UK") */
  region: string;
  /** Human-readable name */
  name: string;
  /** Mapping: standard term → regional synonym */
  mappings: Record<string, string[]>;
  /** Regional descriptors that don't exist in the standard taxonomy */
  additions: VocabularyEntry[];
  /** Standard descriptors that are invalid/obsoleted in this region */
  exclusions: Set<string>;
}

export interface CrosswalkRegistry {
  /** Source identifier */
  source: string;
  /** All vocabulary entries indexed by normalized term */
  entries: Map<string, VocabularyEntry>;
  /** Active regional overlays */
  overlays: RegionalOverlay[];

  /** Look up a term (with optional region) */
  lookup(term: string, region?: string): VocabularyEntry | null;

  /** Expand a term to all matching controlled vocabulary synonyms */
  expand(term: string, region?: string): string[];

  /** Expand multiple terms (e.g., from an AST leaf) */
  expandAll(terms: string[], region?: string): string[];
}

// ============================================
// Registry Implementation
// ============================================

function normalizeTerm(term: string): string {
  return term
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

class CrosswalkRegistryImpl implements CrosswalkRegistry {
  source: string;
  entries: Map<string, VocabularyEntry>;
  overlays: RegionalOverlay[];

  constructor(source: string, entries: VocabularyEntry[], overlays: RegionalOverlay[] = []) {
    this.source = source;
    this.entries = new Map();
    this.overlays = overlays;

    for (const entry of entries) {
      const normalized = normalizeTerm(entry.term);
      this.entries.set(normalized, entry);

      // Also index by synonyms
      for (const synonym of entry.synonyms) {
        const normalizedSyn = normalizeTerm(synonym);
        if (!this.entries.has(normalizedSyn)) {
          this.entries.set(normalizedSyn, { ...entry, weight: entry.weight * 0.9 });
        }
      }
    }
  }

  lookup(term: string, region?: string): VocabularyEntry | null {
    const normalized = normalizeTerm(term);

    // Check regional overlay first
    if (region) {
      const overlay = this.overlays.find(o => o.region === region);
      if (overlay) {
        // Check if term is excluded in this region
        if (overlay.exclusions.has(normalized)) return null;

        // Check regional additions
        const addition = overlay.additions.find(
          a => normalizeTerm(a.term) === normalized
        );
        if (addition) return addition;

        // Check regional mappings (standard term → regional synonym)
        for (const [standard, regionals] of Object.entries(overlay.mappings)) {
          if (regionals.some(r => normalizeTerm(r) === normalized)) {
            return this.entries.get(standard) ?? null;
          }
        }
      }
    }

    // Fall back to standard taxonomy
    return this.entries.get(normalized) ?? null;
  }

  expand(term: string, region?: string): string[] {
    const entry = this.lookup(term, region);
    if (!entry) return [term]; // Return original if no match

    const expanded = new Set<string>([entry.term]);
    for (const syn of entry.synonyms) {
      expanded.add(syn);
    }

    // Include broader terms for better recall
    for (const broader of entry.broaderTerms) {
      expanded.add(broader);
    }

    return Array.from(expanded);
  }

  expandAll(terms: string[], region?: string): string[] {
    const expanded = new Set<string>();
    for (const term of terms) {
      for (const expandedTerm of this.expand(term, region)) {
        expanded.add(expandedTerm);
      }
    }
    return Array.from(expanded);
  }
}

// ============================================
// Factory Function
// ============================================

export function createCrosswalk(
  source: string,
  entries: VocabularyEntry[],
  overlays: RegionalOverlay[] = [],
): CrosswalkRegistry {
  return new CrosswalkRegistryImpl(source, entries, overlays);
}

// ============================================
// Regional Overlay Factory
// ============================================

export function createRegionalOverlay(
  region: string,
  name: string,
  mappings: Record<string, string[]>,
  additions: VocabularyEntry[] = [],
  exclusions: string[] = [],
): RegionalOverlay {
  return { region, name, mappings, additions, exclusions: new Set(exclusions.map(normalizeTerm)) };
}

// ============================================
// Pre-built Registries (loaded from data/)
// ============================================

// Lazy-loaded registries
let _ericRegistry: CrosswalkRegistry | null = null;
let _doajRegistry: CrosswalkRegistry | null = null;
let _malayClinicalRegistry: CrosswalkRegistry | null = null;
let _dryEyeRegistry: CrosswalkRegistry | null = null;

/**
 * Get the ERIC thesaurus crosswalk.
 * Falls back to empty registry if data not loaded.
 */
export async function getERICCrosswalk(region?: string): Promise<CrosswalkRegistry> {
  if (!_ericRegistry) {
    try {
      const { entries, overlays } = await import("../data/eric-descriptors.js");
      _ericRegistry = createCrosswalk("eric", entries ?? [], overlays ?? []);
    } catch {
      _ericRegistry = createCrosswalk("eric", []);
    }
  }
  return _ericRegistry;
}

/**
 * Get the DOAJ subject taxonomy crosswalk.
 */
export async function getDOAJCrosswalk(region?: string): Promise<CrosswalkRegistry> {
  if (!_doajRegistry) {
    try {
      const { entries, overlays } = await import("../data/doaj-subjects.js");
      _doajRegistry = createCrosswalk("doaj", entries ?? [], overlays ?? []);
    } catch {
      _doajRegistry = createCrosswalk("doaj", []);
    }
  }
  return _doajRegistry;
}

/**
 * Get the Malay Clinical Vocabulary crosswalk.
 * Intercepts Western terms and injects Malaysian clinical vernacular.
 */
export async function getMalayClinicalCrosswalk(region?: string): Promise<CrosswalkRegistry> {
  if (!_malayClinicalRegistry) {
    try {
      const mod = await import("../data/malay-clinical.js");
      const { malayClinicalData } = mod;
      _malayClinicalRegistry = createCrosswalk("malay_clinical", malayClinicalData.entries ?? [], malayClinicalData.overlays ?? []);
    } catch {
      _malayClinicalRegistry = createCrosswalk("malay_clinical", []);
    }
  }
  return _malayClinicalRegistry;
}

/**
 * Get the Dry Eye Disease domain crosswalk.
 * Expands free-text dry eye queries to controlled vocabulary including
 * symptoms, subtypes, diagnostic instruments, treatments, and psychosocial terms.
 */
export async function getDryEyeCrosswalk(region?: string): Promise<CrosswalkRegistry> {
  if (!_dryEyeRegistry) {
    try {
      const { dryEyeVocabularyData } = await import("../data/dry-eye-vocabulary.js");
      _dryEyeRegistry = createCrosswalk("dry_eye", dryEyeVocabularyData.entries ?? [], dryEyeVocabularyData.overlays ?? []);
    } catch {
      _dryEyeRegistry = createCrosswalk("dry_eye", []);
    }
  }
  return _dryEyeRegistry;
}
