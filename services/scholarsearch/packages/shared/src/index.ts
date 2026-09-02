// Schemas
export * from "./schemas/paper.js";
export * from "./schemas/search.js";

// Utils
export * from "./utils/dedup.js";
export * from "./utils/ranking.js";
export * from "./utils/circuit-breaker.js";
export * from "./utils/query-parser.js";
export * from "./utils/cardinality.js";
export * from "./utils/vocabulary-crosswalk.js";
export * from "./utils/document-tiers.js";
export * from "./utils/oa-resolver.js";
export * from "./utils/query-versioning.js";
export * from "./utils/predatory-quarantine.js";
export * from "./utils/gap-analysis.js";

// Domain Vocabulary
export { isDryEyeQuery, DRY_EYE_KEYWORDS, dryEyeVocabularyData } from "./data/dry-eye-vocabulary.js";

// Re-export specific types from dedup for convenience
export {
  extractEntities,
  hasConflictingEntities,
  type ExtractedEntities,
} from "./utils/dedup.js";
