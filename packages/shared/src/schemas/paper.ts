import { z } from "zod";

// ============================================
// Source Identifiers
// ============================================

export const SourceIdsSchema = z.object({
  openalex: z.string().optional(),
  semantic_scholar: z.string().optional(),
  pubmed: z.string().optional(),
  pmcid: z.string().optional(),
  doi: z.string().optional(),
  crossref: z.string().optional(),
  eric: z.string().optional(),
  arxiv: z.string().optional(),
  biorxiv: z.string().optional(),
  medrxiv: z.string().optional(),
  lens: z.string().optional(),
  core: z.string().optional(),
});

export type SourceIds = z.infer<typeof SourceIdsSchema>;

// ============================================
// Author
// ============================================

export const AuthorSchema = z.object({
  name: z.string(),
  orcid: z.string().optional(),
  openalex_author_id: z.string().optional(),
  affiliation: z.string().optional(),
  is_corresponding: z.boolean().optional().default(false),
});

export type Author = z.infer<typeof AuthorSchema>;

// ============================================
// Journal
// ============================================

export const JournalSchema = z.object({
  name: z.string(),
  issn: z.string().optional(),
  publisher: z.string().optional(),
  openalex_source_id: z.string().optional(),
  doaj_indexed: z.boolean().optional().default(false),
  scopus_indexed: z.boolean().optional().default(false),
  wos_indexed: z.boolean().optional().default(false),
});

export type Journal = z.infer<typeof JournalSchema>;

// ============================================
// Publication Type
// ============================================

export const PublicationTypeSchema = z.enum([
  "journal_article",
  "review",
  "systematic_review",
  "meta_analysis",
  "rct",
  "cohort",
  "case_control",
  "cross_sectional",
  "case_report",
  "conference_paper",
  "thesis",
  "book_chapter",
  "book",
  "technical_report",
  "preprint",
  "dataset",
  "editorial",
  "letter",
  "commentary",
  "protocol",
  "correction",
  "retraction",
  "expression_of_concern",
]);

export type PublicationType = z.infer<typeof PublicationTypeSchema>;

// ============================================
// Peer Review
// ============================================

export const PeerReviewLevelSchema = z.enum([
  "level_1_verified",      // DOI + Scopus/WoS + publisher confirms
  "level_2_high",          // DOI + DOAJ + Crossref
  "level_3_moderate",      // DOI + Crossref metadata
  "level_4_regional",      // DOI + Crossref, not in major indexes
  "level_5_preprint",      // Preprint server
  "level_6_unverified",    // ResearchGate/Academia only
]);

export type PeerReviewLevel = z.infer<typeof PeerReviewLevelSchema>;

export const PeerReviewStatusSchema = z.object({
  verified: z.boolean(),
  confidence: z.number().min(0).max(1),
  level: PeerReviewLevelSchema,
  method: z.string(),
  flag: z.enum([
    "peer_reviewed",
    "likely_peer_reviewed",
    "preprint",
    "unverified",
    "retracted",
    "expression_of_concern",
    "corrected",
  ]),
});

export type PeerReviewStatus = z.infer<typeof PeerReviewStatusSchema>;

// ============================================
// Open Access
// ============================================

export const OALocationSchema = z.object({
  url: z.string().url(),
  source: z.enum([
    "unpaywall",
    "core",
    "pmc",
    "arxiv",
    "biorxiv",
    "medrxiv",
    "author_site",
    "institutional_repo",
    "zenodo",
    "figshare",
    "other",
  ]),
  version: z.enum([
    "published_version",
    "accepted_version",
    "preprint",
  ]),
  license: z.string().optional(),
});

export type OALocation = z.infer<typeof OALocationSchema>;

export const OpenAccessStatusSchema = z.object({
  is_oa: z.boolean(),
  oa_status: z.enum(["gold", "green", "hybrid", "bronze", "closed"]),
  oa_locations: z.array(OALocationSchema),
  best_oa_url: z.string().url().optional(),
});

export type OpenAccessStatus = z.infer<typeof OpenAccessStatusSchema>;

// ============================================
// Citation Count
// ============================================

export const CitationCountSchema = z.object({
  total: z.number().int().min(0),
  openalex: z.number().int().min(0).optional(),
  semantic_scholar: z.number().int().min(0).optional(),
  crossref: z.number().int().min(0).optional(),
  last_updated: z.string().datetime(),
});

export type CitationCount = z.infer<typeof CitationCountSchema>;

// ============================================
// Journal Metrics
// ============================================

export const JournalMetricsSchema = z.object({
  impact_factor: z.number().nullable().optional(),
  citescore: z.number().nullable().optional(),
  sjr: z.number().nullable().optional(),
  snip: z.number().nullable().optional(),
  jci: z.number().nullable().optional(),
  h_index: z.number().nullable().optional(),
  source: z.string().optional(),
});

export type JournalMetrics = z.infer<typeof JournalMetricsSchema>;

// ============================================
// Retraction Status
// ============================================

export const RetractionStatusSchema = z.object({
  is_retracted: z.boolean(),
  type: z.enum([
    "retraction",
    "expression_of_concern",
    "correction",
    "erratum",
    "withdrawal",
  ]).nullable().optional(),
  source: z.string().nullable().optional(),
  date: z.string().nullable().optional(),
  details: z.string().nullable().optional(),
});

export type RetractionStatus = z.infer<typeof RetractionStatusSchema>;

// ============================================
// Version Relationship
// ============================================

export const VersionRelationshipSchema = z.object({
  type: z.enum([
    "preprint_of",
    "published_version_of",
    "corrected_by",
    "retracted_by",
    "superseded_by",
    "related_to",
  ]),
  target_doi: z.string(),
});

export type VersionRelationship = z.infer<typeof VersionRelationshipSchema>;

// ============================================
// Confidence Score
// ============================================

export const ConfidenceScoreSchema = z.object({
  metadata_completeness: z.number().min(0).max(1),
  peer_review_verification: z.number().min(0).max(1),
  source_reliability: z.number().min(0).max(1),
  overall: z.number().min(0).max(1),
});

export type ConfidenceScore = z.infer<typeof ConfidenceScoreSchema>;

// ============================================
// Ranking Scores
// ============================================

export const RankingScoresSchema = z.object({
  relevance: z.number().min(0).max(1),
  semantic_similarity: z.number().min(0).max(1),
  keyword_match: z.number().min(0).max(1),
  peer_review: z.number().min(0).max(1),
  study_design: z.number().min(0).max(1),
  citation_impact: z.number().min(0).max(1),
  journal_quality: z.number().min(0).max(1),
  recency: z.number().min(0).max(1),
  oa_availability: z.number().min(0).max(1),
  composite: z.number().min(0).max(1),
});

export type RankingScores = z.infer<typeof RankingScoresSchema>;

// ============================================
// PICO Alignment (Clinical Mode)
// ============================================

export const PICOAlignmentSchema = z.object({
  population_age_match: z.number().min(0).max(1),
  population_demographic_match: z.number().min(0).max(1),
  clinical_setting_match: z.number().min(0).max(1),
  geographic_relevance: z.number().min(0).max(1),
  overall: z.number().min(0).max(1),
  is_heuristic: z.boolean().default(true),
  extraction_notes: z.string().optional(),
});

export type PICOAlignment = z.infer<typeof PICOAlignmentSchema>;

// ============================================
// Provenance
// ============================================

export const ProvenanceSchema = z.object({
  discovered_via: z.array(z.string()),
  ranked_by: z.string(),
  peer_review_verified_by: z.array(z.string()),
  oa_resolved_by: z.array(z.string()),
  retraction_checked_by: z.array(z.string()),
  retrieval_timestamp: z.string().datetime(),
  api_versions: z.record(z.string()),
});

export type Provenance = z.infer<typeof ProvenanceSchema>;

// ============================================
// Unified Scholarly Record (Master Schema)
// ============================================

export const ScholarlyWorkSchema = z.object({
  id: z.string().uuid(),
  source_ids: SourceIdsSchema,
  title: z.string().min(1),
  authors: z.array(AuthorSchema),
  year: z.number().int().min(1900).max(2100),
  publication_date: z.string().optional(),
  journal: JournalSchema.nullable(),
  abstract: z.string().nullable().optional(),
  keywords: z.array(z.string()),
  mesh_terms: z.array(z.string()),
  concepts: z.array(z.object({
    name: z.string(),
    score: z.number().min(0).max(1),
  })),
  publication_type: PublicationTypeSchema,
  peer_review_status: PeerReviewStatusSchema,
  study_design: z.string().nullable().optional(),
  subjects_population: z.array(z.string()),
  interventions: z.array(z.string()),
  outcomes: z.array(z.string()),
  country: z.string().nullable().optional(),
  language: z.string().nullable().optional(),
  citation_count: CitationCountSchema.nullable(),
  journal_metrics: JournalMetricsSchema.nullable(),
  open_access_status: OpenAccessStatusSchema,
  full_text_url: z.string().url().nullable().optional(),
  publisher_url: z.string().url().nullable().optional(),
  source_databases: z.array(z.string()),
  retraction_status: RetractionStatusSchema,
  version_relationships: z.array(VersionRelationshipSchema),
  references: z.array(z.string()),
  cited_by: z.array(z.string()),
  retrieval_timestamp: z.string().datetime(),
  confidence_score: ConfidenceScoreSchema,
  ranking_scores: RankingScoresSchema,
  pico_alignment: PICOAlignmentSchema.nullable().optional(),
  provenance: ProvenanceSchema,
});

export type ScholarlyWork = z.infer<typeof ScholarlyWorkSchema>;
