// ============================================
// Predatory Publisher Quarantine
// ============================================
//
// Static bloom filter of known predatory domains, ISSNs, and publisher names.
// Used to apply a negative multiplier to Openness-First Ranking when a paper
// comes from a predatory source, preventing gaming of OA weights.
//
// Sources: Beall's List (archived), Stop Predatory Journals, Cabell's
// This is a static snapshot — periodic manual updates recommended.

export interface PredatoryEntry {
  /** Publisher or journal domain (lowercase) */
  domain?: string;
  /** ISSN (print or electronic) */
  issn?: string;
  /** Publisher name (lowercase) */
  publisher?: string;
  /** Confidence score (0-1) — higher = more likely predatory */
  confidence: number;
}

// ============================================
// Predatory Publisher Domains
// ============================================

export const PREDATORY_DOMAINS: PredatoryEntry[] = [
  // === Major Predatory Publishers ===
  { domain: "omicsonline.org", confidence: 0.95 },
  { domain: "scitechnol.com", confidence: 0.95 },
  { domain: "crimsonpublishers.com", confidence: 0.90 },
  { domain: "medcrave.com", confidence: 0.95 },
  { domain: "entirejournal.com", confidence: 0.85 },
  { domain: "researchopenworld.com", confidence: 0.90 },
  { domain: "lidsen.com", confidence: 0.85 },
  { domain: "peertechz.com", confidence: 0.90 },
  { domain: "researchrevolutions.org", confidence: 0.85 },
  { domain: "scholarsresearchlibrary.com", confidence: 0.90 },
  { domain: "innovationaljournals.com", confidence: 0.85 },
  { domain: "jscivpub.com", confidence: 0.80 },
  { domain: "journalresearch.org", confidence: 0.75 },
  { domain: "globalresearchjournals.org", confidence: 0.80 },
  { domain: "internationaljournals.net", confidence: 0.80 },
  { domain: "academicjournals.org", confidence: 0.75 },
  { domain: "sciencepubco.com", confidence: 0.90 },
  { domain: "imedpub.com", confidence: 0.90 },
  { domain: "alliedacademies.org", confidence: 0.85 },
  { domain: "clinicalbiotics.com", confidence: 0.80 },

  // === Known Predatory Journal Patterns ===
  { domain: "journal-of-*", confidence: 0.70 },
  { domain: "international-journal-of-*", confidence: 0.65 },
  { domain: "world-journal-of-*", confidence: 0.65 },
  { domain: "american-journal-of-*", confidence: 0.60 },

  // === Regional Predatory (Malaysia/SEA) ===
  { domain: "e-journal.com.my", confidence: 0.85 },
  { domain: "myjournals.org", confidence: 0.80 },
  { domain: "journalpress.net", confidence: 0.75 },
];

// ============================================
// Predatory Publisher Names
// ============================================

export const PREDATORY_PUBLISHERS: PredatoryEntry[] = [
  { publisher: "omicron science", confidence: 0.95 },
  { publisher: "scitechnol", confidence: 0.95 },
  { publisher: "crimson publishers", confidence: 0.90 },
  { publisher: "medcrave", confidence: 0.95 },
  { publisher: "research open world", confidence: 0.90 },
  { publisher: "lidsen", confidence: 0.85 },
  { publisher: "peer technology", confidence: 0.90 },
  { publisher: "scholars research library", confidence: 0.90 },
  { publisher: "science publishing co", confidence: 0.90 },
  { publisher: "imedpub", confidence: 0.90 },
  { publisher: "allied academies", confidence: 0.85 },
  { publisher: "involve publisher", confidence: 0.80 },
  { publisher: "journal press", confidence: 0.75 },
  { publisher: "global science library", confidence: 0.80 },
  { publisher: "academic journals inc", confidence: 0.75 },
  { publisher: "international research journals", confidence: 0.80 },
  { publisher: "world journal of", confidence: 0.65 },
  { publisher: "international journal of recent scientific", confidence: 0.85 },
  { publisher: "journal of emerging technologies and", confidence: 0.75 },
  { publisher: "innovative publication", confidence: 0.80 },
];

// ============================================
// Predatory ISSN List (abbreviated)
// ============================================

export const PREDATORY_ISSNS: PredatoryEntry[] = [
  // OAJ Example ISSNs
  { issn: "0974-0724", confidence: 0.90 },
  { issn: "0974-0732", confidence: 0.90 },
  { issn: "0976-5352", confidence: 0.85 },
  { issn: "2249-7838", confidence: 0.80 },
  { issn: "0974-0716", confidence: 0.85 },
];

// ============================================
// Negative Multiplier for Predatory Sources
// ============================================

/**
 * When a paper is from a predatory source, the oa_availability weight
 * flips to a negative value, burying it instantly in Openness-First mode.
 */
export const PREDATORY_NEGATIVE_MULTIPLIER = -2.0;

/**
 * Minimum confidence threshold for a source to be quarantined.
 * Prevents false positives from fuzzy domain matching.
 */
export const PREDATORY_CONFIDENCE_THRESHOLD = 0.70;
