import { z } from "zod";

// ============================================
// Search Modes
// ============================================

export const SearchModeSchema = z.enum([
  "discovery",
  "evidence",
  "systematic_review",
  "thesis",
  "manuscript",
  "citation_verification",
  "adversarial",
  "bibliometric",
  "clinical",
  "openness",
]);

export type SearchMode = z.infer<typeof SearchModeSchema>;

// ============================================
// Search Filters
// ============================================

export const SearchFiltersSchema = z.object({
  date_from: z.number().int().min(1900).max(2100).optional(),
  date_to: z.number().int().min(1900).max(2100).optional(),
  publication_types: z.array(z.string()).optional(),
  peer_reviewed_only: z.boolean().optional().default(false),
  study_designs: z.array(z.string()).optional(),
  languages: z.array(z.string()).optional().default(["en"]),
  open_access_only: z.boolean().optional().default(false),
  countries: z.array(z.string()).optional(),
  disciplines: z.array(z.string()).optional(),
  authors: z.array(z.string()).optional(),
  institutions: z.array(z.string()).optional(),
  journal_issn: z.string().optional(),
  doi: z.string().optional(),
  pmid: z.string().optional(),
});

export type SearchFilters = z.infer<typeof SearchFiltersSchema>;

// ============================================
// PICO Parameters (Clinical Mode)
// ============================================

export const PICOParametersSchema = z.object({
  population: z.string().optional(),
  intervention: z.string().optional(),
  comparison: z.string().optional(),
  outcome: z.string().optional(),
  study_type: z.string().optional(),
  target_demographics: z.object({
    country: z.string().default("MY"),
    region: z.string().default("Southeast Asia"),
    age_range: z.string().optional(),
    setting: z.string().optional(),
    comorbidities: z.array(z.string()).optional(),
  }).optional(),
});

export type PICOParameters = z.infer<typeof PICOParametersSchema>;

// ============================================
// Ranking Weights
// ============================================

export const RankingWeightsSchema = z.object({
  relevance: z.number().min(0).max(1).default(0.25),
  semantic_similarity: z.number().min(0).max(1).default(0.20),
  keyword_match: z.number().min(0).max(1).default(0.15),
  peer_review: z.number().min(0).max(1).default(0.10),
  study_design: z.number().min(0).max(1).default(0.10),
  citation_impact: z.number().min(0).max(1).default(0.10),
  journal_quality: z.number().min(0).max(1).default(0.10),
  recency: z.number().min(0).max(1).default(0.10),
  oa_availability: z.number().min(0).max(1).default(0.05),
});

export type RankingWeights = z.infer<typeof RankingWeightsSchema>;

// ============================================
// Search Query
// ============================================

export const SearchQuerySchema = z.object({
  raw_query: z.string().min(1),
  mode: SearchModeSchema.default("discovery"),
  filters: SearchFiltersSchema.default({}),
  pico: PICOParametersSchema.optional(),
  weights: RankingWeightsSchema.optional(),
  max_results: z.number().int().min(1).max(500).default(100),
  sources: z.array(z.string()).optional(),
  region: z.string().optional(),
});

export type SearchQuery = z.infer<typeof SearchQuerySchema>;

// ============================================
// Expanded Query (LLM Output)
// ============================================

export const ExpandedQuerySchema = z.object({
  concepts: z.array(z.string()),
  synonyms: z.array(z.string()),
  mesh_terms: z.array(z.string()),
  boolean_variants: z.array(z.string()),
  pico: PICOParametersSchema.nullable().optional(),
  database_specific: z.record(z.string()).optional(),
});

export type ExpandedQuery = z.infer<typeof ExpandedQuerySchema>;

// ============================================
// Source Configuration
// ============================================

export const SourceConfigSchema = z.object({
  name: z.string(),
  display_name: z.string(),
  enabled: z.boolean().default(true),
  priority: z.number().int().min(1).max(10).default(5),
  rate_limit_per_second: z.number().default(5),
  requires_auth: z.boolean().default(false),
  auth_type: z.enum(["api_key", "oauth", "none"]).default("none"),
  supports_fulltext: z.boolean().default(false),
  supports_citations: z.boolean().default(true),
  supports_mesh: z.boolean().default(false),
  domain_preference: z.array(z.string()).default([]),
});

export type SourceConfig = z.infer<typeof SourceConfigSchema>;

// ============================================
// Search Result from a Single Source
// ============================================

export const SourceSearchResultSchema = z.object({
  source: z.string(),
  query_used: z.string(),
  results_count: z.number().int(),
  raw_results: z.array(z.record(z.any())),
  timestamp: z.string().datetime(),
  duration_ms: z.number().int(),
  error: z.string().nullable().optional(),
});

export type SourceSearchResult = z.infer<typeof SourceSearchResultSchema>;

// ============================================
// Search Audit Record
// ============================================

export const SearchAuditRecordSchema = z.object({
  search_id: z.string().uuid(),
  user_query: z.string(),
  expanded_query: ExpandedQuerySchema.nullable(),
  mode: SearchModeSchema,
  filters: SearchFiltersSchema,
  sources_queried: z.array(SourceSearchResultSchema),
  total_raw_results: z.number().int(),
  after_deduplication: z.number().int(),
  ranking_method: z.string(),
  ranking_weights: RankingWeightsSchema.nullable(),
  model_used: z.string().nullable(),
  model_version: z.string().nullable(),
  search_configuration: z.string(),
  retrieval_timestamp: z.object({
    start: z.string().datetime(),
    end: z.string().datetime(),
    duration_ms: z.number().int(),
  }),
});

export type SearchAuditRecord = z.infer<typeof SearchAuditRecordSchema>;
