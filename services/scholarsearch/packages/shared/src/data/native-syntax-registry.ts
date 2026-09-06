// ============================================
// Canonical Database-Native Syntax Registry
// ============================================
//
// Evidence-grounded, provenance-preserving registry mapping the
// deep-search evidence package to ScholarSearch implementation.
//
// SOURCES (evidence package, 2026-09-07):
//   - native_syntax_master_matrix_extended.csv  (15 rows, UI/API mixed)
//   - controlled_vocabulary_matrix.csv          (6 rows)
//   - scholarsearch_syntax_adapter_blueprint.md (adapter contract + pseudocode)
//   - Native Search Syntax ... Initial Master Audit (Partial).md (Tier 1-5 audit)
//
// EVIDENCE HIERARCHY (never silently promote):
//   VERIFIED OFFICIAL > SUPPORTED_SECONDARY > UNVERIFIED > DEPRECATED
//
// UI vs API SEPARATION: every profile is ONE database + ONE interface.
// Never reuse a UI syntax row as an API row. API rows for ScholarSearch's
// 8 live clients are marked scholarsearch_runtime=true.
//
// This file is DATA ONLY (no network, no fs, no credentials).
// Rendering/validation lives in utils/native-syntax.ts.

// ============================================
// Types
// ============================================

export type EvidenceTier = "VERIFIED OFFICIAL" | "SUPPORTED — SECONDARY EVIDENCE" | "UNVERIFIED" | "DEPRECATED";
export type Confidence = "High" | "Medium" | "Low";
export type UiOrApi = "UI" | "API";
export type ImplStatus =
  | "SUPPORTED_IMPLEMENTABLE"   // verified + directly emittable by ScholarSearch
  | "SUPPORTED_NEEDS_ADAPTER"   // verified but needs renderer/adapter work
  | "SUPPORTED_NEEDS_VALIDATION"// evidence exists but UI/API transfer unconfirmed
  | "UNVERIFIED"
  | "DEPRECATED"
  | "NOT_APPLICABLE";           // e.g. proximity on an API with no such operator

export interface PlatformProfile {
  platform_id: string;
  database: string;
  interface: string;
  ui_or_api: UiOrApi;
  /** Currentness string straight from evidence (date or "Legacy but current") */
  currentness: string;
  date_checked: string; // ISO date this registry row was authored
  status: "CURRENT" | "NEEDS_RECHECK" | "DEPRECATED";
  evidence_tier: EvidenceTier;
  confidence: Confidence;
  source_url: string;
  scholarsearch_runtime: boolean; // true = ScholarSearch has a live API client
  notes: string;
}

export interface CapabilityRecord {
  platform_id: string;
  capability: string; // e.g. "boolean_and", "proximity_unordered", "truncation_right"
  syntax_template: string; // literal native template with {placeholders}
  restriction: string;
  verified: boolean;
  impl_status: ImplStatus;
  source_url: string;
  evidence_tier: EvidenceTier;
  confidence: Confidence;
  date_checked: string;
}

export interface FieldMapping {
  platform_id: string;
  canonical_field: string; // title | abstract | keywords | author | source | subject | doi | date | language | doctype | affiliation | fulltext | title_abstract | title_abstract_keywords
  native_field: string;
  emitter_style: "FUNCTION" | "BRACKET_TAG" | "DOT_TAG" | "PREFIX_COLON" | "PARAM" | "FORM_CONTROL" | "LUCENE_FIELD";
  restrictions: string;
  source_url: string;
  evidence_tier: EvidenceTier;
  confidence: Confidence;
}

export interface VocabularyMapping {
  platform_id: string;
  vocabulary: string; // MeSH | Emtree | CINAHL Headings | ERIC Thesaurus | APA Thesaurus | none
  canonical_action: string; // explode | no_explode | major | subheading | descriptor_search
  native_template: string;
  restriction: string;
  evidence_tier: EvidenceTier;
  confidence: Confidence;
  source_url: string;
}

export const REGISTRY_VERSION = "1.0.0";
export const REGISTRY_DATE = "2026-09-07";

// ============================================
// Platform profiles (database + interface)
// ============================================

export const PLATFORM_PROFILES: PlatformProfile[] = [
  // ---- ScholarSearch runtime APIs (8 live clients) ----
  {
    platform_id: "scopus_api", database: "Scopus", interface: "Scopus Search API (api.elsevier.com/content/search/scopus)",
    ui_or_api: "API", currentness: "2026-08-24 (UI help; API grammar mirrors advanced search)",
    date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search",
    scholarsearch_runtime: true,
    notes: "API accepts same field-code/Boolean/proximity grammar as advanced search. UI page is Tier 1; API transfer marked NEEDS_VALIDATION per-capability.",
  },
  {
    platform_id: "pubmed_api", database: "PubMed/MEDLINE", interface: "NCBI E-utilities esearch/esummary (EUTILS_BASE)",
    ui_or_api: "API", currentness: "2026-09-01 (PubMed help); proximity since 2022-11-29",
    date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://pubmed.ncbi.nlm.nih.gov/help/",
    scholarsearch_runtime: true,
    notes: "esearch `term` accepts PubMed UI field tags, MeSH tags, and [field:~N] proximity. UI/API transfer NEEDS_VALIDATION for edge cases.",
  },
  {
    platform_id: "openalex_api", database: "OpenAlex", interface: "OpenAlex REST API (/works, default.search + filter)",
    ui_or_api: "API", currentness: "2024–2025", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://developers.openalex.org/guides/filtering",
    scholarsearch_runtime: true,
    notes: "No Boolean OR/NOT in filter language; implicit AND. Client-side logic required for OR/NOT. Already handled via local-intersection compensator.",
  },
  {
    platform_id: "crossref_api", database: "Crossref", interface: "Crossref REST API (/works, query + filter)",
    ui_or_api: "API", currentness: "2020–2025", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://api.crossref.org/swagger-ui/index.html",
    scholarsearch_runtime: true,
    notes: "No Boolean operators; >=20% term-match rule; additive filters (filter=name:value). ScholarSearch must not emit AND/OR/NOT to Crossref.",
  },
  {
    platform_id: "semantic_scholar_api", database: "Semantic Scholar", interface: "S2 Graph API v1 (/paper/search, query + fields)",
    ui_or_api: "API", currentness: "FAQ current", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://www.semanticscholar.org/faq/boolean-queries",
    scholarsearch_runtime: true,
    notes: "Official FAQ: no Boolean operators or wildcards; quoted phrases only. AND-unsafe; local-intersection compensator applies.",
  },
  {
    platform_id: "eric_api", database: "ERIC", interface: "ERIC API (api.ies.ed.gov/eric, q + rows + fields)",
    ui_or_api: "API", currentness: "2024 (API); thesaurus guides 2023–2025", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://eric.ed.gov/?api",
    scholarsearch_runtime: true,
    notes: "Free-text q param verified via client use. DE=\"descriptor\" thesaurus search documented in thesaurus/LibGuides (secondary), not API docs → NEEDS_VALIDATION.",
  },
  {
    platform_id: "doaj_api", database: "DOAJ", interface: "DOAJ API v2 (/search/articles, query_string + default_operator AND)",
    ui_or_api: "API", currentness: "2024–2026", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://doaj.org/api/v2/docs",
    scholarsearch_runtime: true,
    notes: "query_string grammar (AND/OR, quotes, bibjson.* fields, ranges) per Nested Knowledge DOAJ guide (secondary) + client use. UI field:keyword transfer NEEDS_VALIDATION.",
  },
  {
    platform_id: "core_api", database: "CORE", interface: "CORE API v3 (/search/works, q + limit)",
    ui_or_api: "API", currentness: "no evidence in package", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "UNVERIFIED", confidence: "Low",
    source_url: "",
    scholarsearch_runtime: true,
    notes: "No CORE syntax row in evidence package. Generic q passthrough only; nothing native claimed. UNVERIFIED — do not document as native.",
  },
  // ---- UI translation targets (researcher copy-paste; no live client) ----
  {
    platform_id: "scopus_ui", database: "Scopus", interface: "Scopus.com advanced search",
    ui_or_api: "UI", currentness: "2026-08-24", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search",
    scholarsearch_runtime: false,
    notes: "Full grammar: OR/AND/AND NOT, W/n, PRE/n, TITLE-ABS-KEY etc. Precedence OR > W/n,PRE/n > AND > AND NOT.",
  },
  {
    platform_id: "pubmed_ui", database: "PubMed/MEDLINE", interface: "PubMed UI",
    ui_or_api: "UI", currentness: "2022-11-29 / 2026-09-01", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://pubmed.ncbi.nlm.nih.gov/help/",
    scholarsearch_runtime: false,
    notes: "Bracket tags, MeSH, [Mesh:noexp]/[majr]/[sh]/[pt]/[sb], proximity [ti|tiab|ad:~N].",
  },
  {
    platform_id: "wos_ui", database: "Web of Science Core Collection", interface: "Advanced search",
    ui_or_api: "UI", currentness: "2023-08-23", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://webofscience.zendesk.com/hc/en-us/articles/20016122409105-Search-Operators",
    scholarsearch_runtime: false,
    notes: "NEAR/x, SAME; wildcards *,?,\$; left truncation in Topic/Title/Identifying Codes only. Precedence NEAR/x > SAME > NOT > AND > OR.",
  },
  {
    platform_id: "ovid_medline_ui", database: "MEDLINE via Ovid", interface: "Ovid command line (UI)",
    ui_or_api: "UI", currentness: "Legacy but current", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm",
    scholarsearch_runtime: false,
    notes: "ADJn adjacency; truncation root*/root\$, wildcards # and ?; fields .ti/.ab/.kf/.mp; MeSH exp term/, *term/, term/sh, fs.",
  },
  {
    platform_id: "embase_com_ui", database: "Embase", interface: "Embase.com",
    ui_or_api: "UI", currentness: "2026-03-06", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "Medium",
    source_url: "https://www.elsevier.support/embase/answer/can-i-use-boolean-operators-wildcards-and-proximity-operators-in-embase",
    scholarsearch_runtime: false,
    notes: "NEAR/n (unordered), NEXT/n (ordered); wildcards *,?, \$; no leading wildcards. Emtree via Query Builder (explode / major-focus checkboxes).",
  },
  {
    platform_id: "sciencedirect_ui", database: "ScienceDirect", interface: "ScienceDirect advanced search (UI)",
    ui_or_api: "UI", currentness: "2026-03-01", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://www.elsevier.support/sciencedirect/answer/how-do-i-use-the-advanced-search",
    scholarsearch_runtime: false,
    notes: "AND/OR/NOT + hyphen-minus NOT; precedence NOT > AND > OR; implicit AND; NO truncation in UI.",
  },
  {
    platform_id: "base_ui", database: "BASE", interface: "BASE basic/advanced search (UI)",
    ui_or_api: "UI", currentness: "help page current", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://www.base-search.net/about/en/help.php",
    scholarsearch_runtime: false,
    notes: "Implicit AND; * multi-char wildcard (not leading, not in phrases); verbatim mode; field restrictions via advanced form.",
  },
  {
    platform_id: "springer_ui", database: "SpringerLink / Springer Nature", interface: "Springer Nature Link advanced search (UI)",
    ui_or_api: "UI", currentness: "2025-02-25", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "Medium",
    source_url: "https://support.springernature.com/en/support/solutions/articles/6000080445-springer-nature-link-advanced-search-option",
    scholarsearch_runtime: false,
    notes: "Form-based: Keywords/Title/Author(s)/Editor(s)/In Journal(s)/Date Published. Boolean + quotes; NO verified proximity/truncation → form_only adapter.",
  },
  {
    platform_id: "dimensions_dsl", database: "Dimensions", interface: "Dimensions DSL API",
    ui_or_api: "API", currentness: "DSL 2.15 (current)", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://docs.dimensions.ai/dsl/language.html",
    scholarsearch_runtime: false,
    notes: "search <source> ... for \"...\" where ... return ...; Boolean in for-strings; suffix wildcards ?/*; proximity \"phrase\"~N (Lucene slop).",
  },
  {
    platform_id: "lens_ui", database: "Lens", interface: "Lens scholarly/patent search (Query Text Editor + structured)",
    ui_or_api: "UI", currentness: "2026-03-17", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://support.lens.org/",
    scholarsearch_runtime: false,
    notes: "Proximity \"phrase\"~N; wildcards ?/* single-term only, not leading, ignored in phrases, not stemmed.",
  },
  // ---- Secondary-evidence UI targets (emit only with warning) ----
  {
    platform_id: "ebscohost_ui", database: "EBSCOhost (CINAHL/PsycINFO/ERIC)", interface: "EBSCOhost Advanced search",
    ui_or_api: "UI", currentness: "undated handout; guides 2020–2024", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://connect.ebsco.com/s/article/EBSCOhost-Searching-Tips?language=en_US",
    scholarsearch_runtime: false,
    notes: "Nn (near, any order), Wn (within, ordered); truncation *; wildcards ?/#. Precedence not formally specified — always parenthesize.",
  },
  {
    platform_id: "proquest_ui", database: "ProQuest", interface: "ProQuest Advanced/Command Line search",
    ui_or_api: "UI", currentness: "2023–2024 (LibGuides)", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://library-guides.ucl.ac.uk/proquest/command-line-search",
    scholarsearch_runtime: false,
    notes: "AND/OR/NOT, implicit AND, fields TI/AB/SU/AU/PUB; * truncation (1+ chars), ? single char internal/right; no leading truncation.",
  },
  {
    platform_id: "cochrane_ui", database: "Cochrane Library", interface: "Cochrane Advanced search + Search Manager",
    ui_or_api: "UI", currentness: "2023–2026 (LibGuides; official help not exposed)", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://zuyd.libguides.com/cochrane-library/searching",
    scholarsearch_runtime: false,
    notes: "NEAR/x (default 6 per guides — UNVERIFIED), NEXT/x; */? wildcards not inside quoted phrases. Official Search Help is a Tier 1 gap.",
  },
  {
    platform_id: "ieee_ui", database: "IEEE Xplore", interface: "IEEE basic/command search",
    ui_or_api: "UI", currentness: "2016–2024 (guides/PDFs)", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://ieeexplore.ieee.org/",
    scholarsearch_runtime: false,
    notes: "NEAR/#, ONEAR/# (uppercase); max 25 terms/clause; * wildcard in some contexts. Official engine docs inaccessible — Tier 1 gap.",
  },
  {
    platform_id: "jstor_ui", database: "JSTOR", interface: "JSTOR Advanced search (platform UI)",
    ui_or_api: "UI", currentness: "2023–2025 guides", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://support.jstor.org/",
    scholarsearch_runtime: false,
    notes: "AND/OR/NOT uppercase; NEARn (single keywords only); \"phrase\"~n; * truncation; & plural operator. Nested Boolean fragile.",
  },
  {
    platform_id: "wiley_ui", database: "Wiley Online Library", interface: "Wiley advanced search (UI)",
    ui_or_api: "UI", currentness: "2020–2023", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://onlinelibrary.wiley.com/action/showFullTable?doi=10.1002%2F9781118427287.searchguide",
    scholarsearch_runtime: false,
    notes: "AND/OR/NOT; * truncation, ? single char; wildcards not leading; precedence NOT > AND > OR (LibGuides). Form-line Boolean common.",
  },
  {
    platform_id: "tandf_ui", database: "Taylor & Francis Online", interface: "Taylor & Francis advanced search (UI)",
    ui_or_api: "UI", currentness: "2013–2024", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://www.tandfonline.com/action/authorSubmission?journalCode=&page=instructions",
    scholarsearch_runtime: false,
    notes: "Lucene-based: ?/* wildcards (not leading, not in phrases); \"phrase\"~n proximity; precedence NOT > AND > OR.",
  },
  {
    platform_id: "sage_ui", database: "SAGE Journals", interface: "SAGE Journals search (UI)",
    ui_or_api: "UI", currentness: "2012–2023", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://journals.sagepub.com/action/showFullTable?doi=10.1177%2Fsearch-tips",
    scholarsearch_runtime: false,
    notes: "Lucene extensions: term~ stemming, \"kw\"~n phrase proximity, ^ importance boost, +/-/& synonyms for AND. ~ over-broadens — warn.",
  },
  {
    platform_id: "googlescholar_ui", database: "Google Scholar", interface: "Google Scholar web UI",
    ui_or_api: "UI", currentness: "2013–2023", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://scholar.google.com/intl/en/scholar/help.html",
    scholarsearch_runtime: false,
    notes: "Implicit AND; | OR; - NOT; quotes; author:/source:/citations:/related:/site:. AROUND(n) UNVERIFIED (secondary guides only).",
  },
  {
    platform_id: "semanticscholar_ui", database: "Semantic Scholar", interface: "Semantic Scholar search (UI)",
    ui_or_api: "UI", currentness: "FAQ current", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://www.semanticscholar.org/faq/boolean-queries",
    scholarsearch_runtime: false,
    notes: "No Boolean or wildcards; quoted phrases only; filters separate. Any Boolean-looking string is NOT native.",
  },
  {
    platform_id: "doaj_ui", database: "DOAJ", interface: "DOAJ search (UI)",
    ui_or_api: "UI", currentness: "2024–2026", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium",
    source_url: "https://doaj.org/docs/search/",
    scholarsearch_runtime: false,
    notes: "AND/OR/AND NOT; quotes; field:keyword (title/abstract/publisher/bibjson.*); ranges bibjson.year:[YYYY TO YYYY]. Case-sensitive operators.",
  },
  {
    platform_id: "crossref_api_ui", database: "Crossref", interface: "Crossref REST API",
    ui_or_api: "API", currentness: "2020–2025", date_checked: "2026-09-07", status: "CURRENT",
    evidence_tier: "VERIFIED OFFICIAL", confidence: "High",
    source_url: "https://api.crossref.org/swagger-ui/index.html",
    scholarsearch_runtime: false,
    notes: "Duplicate API profile for UI/API-separation completeness (canonical: crossref_api). No Boolean; filter=name:value additive.",
  },
  {
    platform_id: "europepmc_ui", database: "Europe PMC", interface: "Europe PMC web UI",
    ui_or_api: "UI", currentness: "not in evidence package", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "UNVERIFIED", confidence: "Low",
    source_url: "",
    scholarsearch_runtime: false,
    notes: "Blueprint-only pattern (AND/OR/NOT + quotes assumed). Proximity/truncation UNVERIFIED. Do not emit without validation.",
  },
  {
    platform_id: "europepmc_api", database: "Europe PMC", interface: "Europe PMC REST API (/rest/fields + /rest/search)",
    ui_or_api: "API", currentness: "not in evidence package", date_checked: "2026-09-07", status: "NEEDS_RECHECK",
    evidence_tier: "UNVERIFIED", confidence: "Low",
    source_url: "",
    scholarsearch_runtime: false,
    notes: "API field names must come from /rest/fields registry. Kept separate from UI profile. UNVERIFIED.",
  },
];

// ============================================
// Capabilities
// ============================================

export const CAPABILITIES: CapabilityRecord[] = [
  // ---------- scopus_api (runtime) ----------
  { platform_id: "scopus_api", capability: "boolean_and", syntax_template: "{a} AND {b}", restriction: "Parenthesize non-trivial groups; no implied AND in advanced grammar", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_api", capability: "boolean_or", syntax_template: "{a} OR {b}", restriction: "OR evaluated FIRST (before W/n, PRE/n, AND, AND NOT)", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_api", capability: "boolean_not", syntax_template: "{a} AND NOT {b}", restriction: "Scopus uses AND NOT (bare NOT is not the documented form); evaluated LAST", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_api", capability: "phrase_loose", syntax_template: "\"{phrase}\"", restriction: "Loose phrase: punctuation normalized; wildcards allowed inside", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_api", capability: "phrase_exact", syntax_template: "{{{phrase}}}", restriction: "Braces preserve hyphens/punctuation; wildcards literal inside {}", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_api", capability: "proximity_unordered", syntax_template: "({left} W/{n} {right})", restriction: "Textual fields only; evaluated before AND", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_api", capability: "proximity_ordered", syntax_template: "({left} PRE/{n} {right})", restriction: "Ordered; textual fields only", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_api", capability: "field_title_abstract_keywords", syntax_template: "TITLE-ABS-KEY({expr})", restriction: "Combined-field search across title/abstract/keywords", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_api", capability: "limits_year_doctype", syntax_template: "PUBYEAR AFT {yyyy} AND PUBYEAR BEF {yyyy} AND DOCTYPE({t})", restriction: "Year/doctype vocabulary must match Scopus codelist", verified: true, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "Medium", date_checked: "2026-09-07" },
  // ---------- pubmed_api (runtime) ----------
  { platform_id: "pubmed_api", capability: "boolean_and", syntax_template: "({a} AND {b})", restriction: "Uppercase operators; left-to-right; parentheses override", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "pubmed_api", capability: "boolean_or", syntax_template: "({a} OR {b})", restriction: "Uppercase; parentheses for groups", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "pubmed_api", capability: "boolean_not", syntax_template: "({a} NOT {b})", restriction: "Uppercase NOT", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "pubmed_api", capability: "phrase", syntax_template: "\"{phrase}\"[All Fields]", restriction: "Quoted phrases bypass ATM; current compiler default. Fielded [tiab]/[ti] preferred for precision", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "pubmed_api", capability: "proximity_unordered", syntax_template: "\"{phrase}\"[{field}:~{n}]", restriction: "Fields LIMITED to ti/tiab/ad; NO truncation inside proximity; ATM not applied; order not fixed", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://www.nlm.nih.gov/pubs/techbull/nd22/nd22_pubmed_proximity_search_available.html", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "pubmed_api", capability: "truncation_right", syntax_template: "{root}*", restriction: ">=4 chars before *; turns off ATM; allowed in phrases with tags; FORBIDDEN inside proximity", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "pubmed_api", capability: "field_tags", syntax_template: "{terms}[{tag}]", restriction: "Tags: ti/tiab/mh/majr/sh/pt/dp/edat/au/ad/rn/ta/tw etc.; tags disable ATM", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "pubmed_api", capability: "vocab_mesh", syntax_template: "\"{heading}\"[Mesh]", restriction: "Default explode; see vocabulary_mappings for noexp/majr/sh", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  // ---------- openalex_api (runtime) ----------
  { platform_id: "openalex_api", capability: "boolean_and", syntax_template: "implicit AND (space-separated) + filter=…,…", restriction: "No explicit AND operator in filter language; free-text terms ANDed", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://developers.openalex.org/guides/filtering", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "openalex_api", capability: "boolean_or", syntax_template: "NOT SUPPORTED (client-side union)", restriction: "OR requires multiple queries + client-side union; local-intersection compensator handles AND side", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://developers.openalex.org/guides/filtering", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "openalex_api", capability: "boolean_not", syntax_template: "NOT SUPPORTED (client-side exclusion)", restriction: "NOT requires client-side filtering via evaluateAST", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://developers.openalex.org/guides/filtering", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "openalex_api", capability: "phrase", syntax_template: "\"{phrase}\" in default.search / title.search", restriction: "Non-exact matching inherent in .search; no proximity/wildcard operators", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://developers.openalex.org/guides/filtering", evidence_tier: "VERIFIED OFFICIAL", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "openalex_api", capability: "proximity", syntax_template: "NOT SUPPORTED", restriction: "No proximity operator; conceptual proximity must be handled outside API", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://developers.openalex.org/guides/filtering", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "openalex_api", capability: "filters", syntax_template: "filter={attr}:{value},{attr2}:{value2}", restriction: "from_publication_date/to_publication_date/is_oa/language supported by client", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://developers.openalex.org/guides/filtering", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  // ---------- crossref_api (runtime) ----------
  { platform_id: "crossref_api", capability: "boolean_and", syntax_template: "NOT SUPPORTED (space-separated terms, >=20% must match)", restriction: "AND/OR/NOT not supported; scoring + minimum-match rules apply", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://api.crossref.org/swagger-ui/index.html", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "crossref_api", capability: "boolean_or", syntax_template: "NOT SUPPORTED", restriction: "OR-like behaviour only via multiple additive filters, not Boolean", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://api.crossref.org/swagger-ui/index.html", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "crossref_api", capability: "boolean_not", syntax_template: "NOT SUPPORTED", restriction: "NOT silently dropped by current compiler is a BUG — must warn + client-side filter", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://api.crossref.org/swagger-ui/index.html", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "crossref_api", capability: "filters", syntax_template: "filter={name}:{value},{name2}:{value2} + query.{field} + select", restriction: "Filtering additive; query.affiliation etc. supported", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://api.crossref.org/swagger-ui/index.html", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  // ---------- semantic_scholar_api (runtime) ----------
  { platform_id: "semantic_scholar_api", capability: "boolean_and", syntax_template: "NOT SUPPORTED (space-separated; S2 matching)", restriction: "Official FAQ: no Boolean; complex queries joined with spaces", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://www.semanticscholar.org/faq/boolean-queries", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "semantic_scholar_api", capability: "boolean_or", syntax_template: "NOT SUPPORTED", restriction: "OR string is passed through but NOT native — warn", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://www.semanticscholar.org/faq/boolean-queries", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "semantic_scholar_api", capability: "phrase", syntax_template: "\"{phrase}\"", restriction: "Quoted phrases only native feature", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.semanticscholar.org/faq/boolean-queries", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "semantic_scholar_api", capability: "wildcard", syntax_template: "NOT SUPPORTED", restriction: "No wildcards per FAQ", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://www.semanticscholar.org/faq/boolean-queries", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  // ---------- eric_api (runtime) ----------
  { platform_id: "eric_api", capability: "boolean_and", syntax_template: "({a} AND {b}) in q", restriction: "Free-text q verified via client use; case-sensitive handling unconfirmed", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://eric.ed.gov/?api", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "eric_api", capability: "phrase", syntax_template: "\"{phrase}\" in q", restriction: "Multi-word descriptors should be quoted", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://eric.ed.gov/?api", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "eric_api", capability: "vocab_descriptor", syntax_template: "DE=\"{descriptor}\"", restriction: "Thesaurus descriptor syntax from guides, not API docs → validate before relying", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://eric.ed.gov/?thesaurus", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  // ---------- doaj_api (runtime) ----------
  { platform_id: "doaj_api", capability: "boolean_and", syntax_template: "({a} AND {b}) in query_string (default_operator AND)", restriction: "Operators case-sensitive; explicit operators recommended", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://doaj.org/api/v2/docs", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "doaj_api", capability: "phrase", syntax_template: "\"{phrase}\" in query_string", restriction: "Quotes for phrases", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://doaj.org/api/v2/docs", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "doaj_api", capability: "fielded", syntax_template: "{field}:{keyword} e.g. title:stroke; bibjson.year:[{a} TO {b}]", restriction: "Field names follow DOAJ JSON schema; some UI filters OR-linked", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://doaj.org/docs/search/", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  // ---------- core_api (runtime, unverified) ----------
  { platform_id: "core_api", capability: "free_text", syntax_template: "{q passthrough}", restriction: "No native syntax claimed; generic q only until Tier 1 docs obtained", verified: false, impl_status: "UNVERIFIED", source_url: "", evidence_tier: "UNVERIFIED", confidence: "Low", date_checked: "2026-09-07" },
  // ---------- UI exemplars (translation targets) ----------
  { platform_id: "scopus_ui", capability: "boolean_and", syntax_template: "{a} AND {b}", restriction: "Precedence: OR > W/n,PRE/n > AND > AND NOT; parenthesize", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_ui", capability: "proximity_unordered", syntax_template: "({left} W/{n} {right})", restriction: "Textual fields only", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "scopus_ui", capability: "proximity_ordered", syntax_template: "({left} PRE/{n} {right})", restriction: "Ordered", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "pubmed_ui", capability: "proximity_unordered", syntax_template: "\"{phrase}\"[{field}:~{n}]", restriction: "ti/tiab/ad only; no truncation; ATM off", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.nlm.nih.gov/pubs/techbull/nd22/nd22_pubmed_proximity_search_available.html", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "wos_ui", capability: "proximity_unordered", syntax_template: "{a} NEAR/{n} {b}", restriction: "Default NEAR = 15 words; cannot share clause with AND", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://webofscience.zendesk.com/hc/en-us/articles/20016122409105-Search-Operators", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "wos_ui", capability: "proximity_same", syntax_template: "{a} SAME {b}", restriction: "Same address/grouped field", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://webofscience.zendesk.com/hc/en-us/articles/20016122409105-Search-Operators", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "wos_ui", capability: "truncation", syntax_template: "{root}* / {a}?{b} / {a}${b}", restriction: "* multi, ? single, \$ zero/one; left truncation NOT in Author/Cited Author; min chars apply", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://webofscience.zendesk.com/hc/en-us/articles/25350084904721-Search-Rules", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "ovid_medline_ui", capability: "proximity_adjacency", syntax_template: "({left} ADJ{n} {right})", restriction: "n = 1..99; same field only; mapping must be OFF for truncation/wildcards", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "ovid_medline_ui", capability: "truncation_wildcard", syntax_template: "{root}* / {root}\$ / {root}*\$n / {a}#{b} / {a}?{b}", restriction: "# required single char; ? optional char; inside single words only", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "embase_com_ui", capability: "proximity_unordered", syntax_template: "{a} NEAR/{n} {b}", restriction: "All search options; default distance unspecified — always give /n", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://www.elsevier.support/embase/answer/can-i-use-boolean-operators-wildcards-and-proximity-operators-in-embase", evidence_tier: "VERIFIED OFFICIAL", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "embase_com_ui", capability: "proximity_ordered", syntax_template: "{a} NEXT/{n} {b}", restriction: "Ordered", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://www.elsevier.support/embase/answer/can-i-use-boolean-operators-wildcards-and-proximity-operators-in-embase", evidence_tier: "VERIFIED OFFICIAL", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "sciencedirect_ui", capability: "boolean_not_hyphen", syntax_template: "-{term} (= NOT)", restriction: "Hyphen directly before term acts as NOT; operators uppercase", verified: true, impl_status: "SUPPORTED_IMPLEMENTABLE", source_url: "https://www.elsevier.support/sciencedirect/answer/how-do-i-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "sciencedirect_ui", capability: "truncation", syntax_template: "NOT SUPPORTED", restriction: "Truncation not supported in ScienceDirect UI — must not emit *", verified: true, impl_status: "NOT_APPLICABLE", source_url: "https://www.elsevier.support/sciencedirect/answer/how-do-i-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "dimensions_dsl", capability: "proximity", syntax_template: "\"{phrase}\"~{n}", restriction: "Lucene slop in for-strings; ~0 = exact; wildcards suffix-only (?/*, no *ital)", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://docs.dimensions.ai/dsl/language.html", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "lens_ui", capability: "proximity", syntax_template: "\"{phrase}\"~{n}", restriction: "~0 exact adjacency; 2 units to swap order; more to reorder multi-word", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://support.lens.org/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "lens_ui", capability: "wildcard", syntax_template: "{a}?{b} / {root}*", restriction: "Single terms only; not first char; ignored in phrases; wildcarded terms not stemmed", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://support.lens.org/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "base_ui", capability: "wildcard", syntax_template: "{root}*", restriction: "* disables word-forms/synonyms; not in phrases", verified: true, impl_status: "SUPPORTED_NEEDS_ADAPTER", source_url: "https://www.base-search.net/about/en/help.php", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", date_checked: "2026-09-07" },
  { platform_id: "ebscohost_ui", capability: "proximity_near", syntax_template: "{a} N{n} {b}", restriction: "Near, any order (e.g. tax N5 reform); mainly full-text documented", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://connect.ebsco.com/s/article/EBSCOhost-Searching-Tips?language=en_US", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "ebscohost_ui", capability: "proximity_within", syntax_template: "{a} W{n} {b}", restriction: "Within, ORDERED (e.g. hiking W5 trails)", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://connect.ebsco.com/s/article/EBSCOhost-Searching-Tips?language=en_US", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "cochrane_ui", capability: "proximity_near", syntax_template: "{a} NEAR/{n} {b}", restriction: "Default distance 6 per LibGuides — UNVERIFIED; wildcards not inside quoted phrases", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://zuyd.libguides.com/cochrane-library/searching", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "cochrane_ui", capability: "proximity_next", syntax_template: "{a} NEXT/{n} {b}", restriction: "Ordered adjacency; official help not exposed", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://zuyd.libguides.com/cochrane-library/searching", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "ieee_ui", capability: "proximity", syntax_template: "\"{a}\" NEAR/{n} \"{b}\" / ONEAR/{n}", restriction: "UPPERCASE required; max 25 terms/clause; not in legacy advanced form", verified: false, impl_status: "SUPPORTED_NEEDS_VALIDATION", source_url: "https://ieeexplore.ieee.org/", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", date_checked: "2026-09-07" },
  { platform_id: "googlescholar_ui", capability: "proximity_around", syntax_template: "AROUND({n}) — UNVERIFIED", restriction: "No native proximity in official help; AROUND(n) secondary-only → DO NOT EMIT as native", verified: false, impl_status: "UNVERIFIED", source_url: "https://scholar.google.com/intl/en/scholar/help.html", evidence_tier: "UNVERIFIED", confidence: "Low", date_checked: "2026-09-07" },
  { platform_id: "europepmc_ui", capability: "boolean_and", syntax_template: "{a} AND {b} (assumed)", restriction: "Blueprint assumption only — UNVERIFIED", verified: false, impl_status: "UNVERIFIED", source_url: "", evidence_tier: "UNVERIFIED", confidence: "Low", date_checked: "2026-09-07" },
  { platform_id: "europepmc_api", capability: "fielded", syntax_template: "per /rest/fields registry (assumed)", restriction: "UNVERIFIED — resolve against /rest/fields before emitting", verified: false, impl_status: "UNVERIFIED", source_url: "", evidence_tier: "UNVERIFIED", confidence: "Low", date_checked: "2026-09-07" },
];

// ============================================
// Field mappings (canonical → native)
// ============================================

export const FIELD_MAPPINGS: FieldMapping[] = [
  // Scopus API (= UI grammar)
  { platform_id: "scopus_api", canonical_field: "title", native_field: "TITLE", emitter_style: "FUNCTION", restrictions: "TITLE({expr})", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "scopus_api", canonical_field: "abstract", native_field: "ABS", emitter_style: "FUNCTION", restrictions: "ABS({expr})", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "scopus_api", canonical_field: "title_abstract_keywords", native_field: "TITLE-ABS-KEY", emitter_style: "FUNCTION", restrictions: "Default combined field for concept text", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "scopus_api", canonical_field: "author", native_field: "AUTH", emitter_style: "FUNCTION", restrictions: "AUTH({name})", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "scopus_api", canonical_field: "affiliation", native_field: "AFFIL", emitter_style: "FUNCTION", restrictions: "AFFIL({expr})", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "scopus_api", canonical_field: "doi", native_field: "DOI", emitter_style: "FUNCTION", restrictions: "DOI({doi})", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "scopus_api", canonical_field: "doctype", native_field: "DOCTYPE", emitter_style: "FUNCTION", restrictions: "DOCTYPE must match codelist", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "scopus_api", canonical_field: "subject", native_field: "SUBJAREA", emitter_style: "FUNCTION", restrictions: "SUBJAREA({code})", source_url: "https://www.elsevier.support/scopus/answer/how-can-i-best-use-the-advanced-search", evidence_tier: "VERIFIED OFFICIAL", confidence: "Medium" },
  // PubMed API (= UI tags)
  { platform_id: "pubmed_api", canonical_field: "title", native_field: "ti", emitter_style: "BRACKET_TAG", restrictions: "({expr})[ti]; proximity allowed", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "pubmed_api", canonical_field: "title_abstract", native_field: "tiab", emitter_style: "BRACKET_TAG", restrictions: "({expr})[tiab]; proximity allowed", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "pubmed_api", canonical_field: "affiliation", native_field: "ad", emitter_style: "BRACKET_TAG", restrictions: "({expr})[ad]; proximity allowed, N<=1000 same block", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "pubmed_api", canonical_field: "author", native_field: "au", emitter_style: "BRACKET_TAG", restrictions: "{name}[au]", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "pubmed_api", canonical_field: "date", native_field: "dp", emitter_style: "BRACKET_TAG", restrictions: "{from}:{to}[dp]", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "pubmed_api", canonical_field: "language", native_field: "lang", emitter_style: "BRACKET_TAG", restrictions: "{lang}[lang]", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "pubmed_api", canonical_field: "doctype", native_field: "pt", emitter_style: "BRACKET_TAG", restrictions: "\"{type}\"[pt]", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  // Ovid
  { platform_id: "ovid_medline_ui", canonical_field: "title", native_field: "ti", emitter_style: "DOT_TAG", restrictions: "({expr}).ti. — mapping OFF for truncation", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "ovid_medline_ui", canonical_field: "abstract", native_field: "ab", emitter_style: "DOT_TAG", restrictions: "({expr}).ab.", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "ovid_medline_ui", canonical_field: "title_abstract", native_field: "ti,ab,kf", emitter_style: "DOT_TAG", restrictions: "({expr}).ti,ab,kf.", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "ovid_medline_ui", canonical_field: "fulltext", native_field: "mp", emitter_style: "DOT_TAG", restrictions: "Multi-purpose .mp. search", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  // WoS
  { platform_id: "wos_ui", canonical_field: "title_abstract_keywords", native_field: "TS", emitter_style: "PREFIX_COLON", restrictions: "TS=({expr}); lemmatization unless quoted/wildcard", source_url: "https://webofscience.zendesk.com/hc/en-us/articles/26916347018257-Web-of-Science-Core-Collection-Advanced-Search-Field-Tags", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "wos_ui", canonical_field: "title", native_field: "TI", emitter_style: "PREFIX_COLON", restrictions: "TI=({expr})", source_url: "https://webofscience.zendesk.com/hc/en-us/articles/26916347018257-Web-of-Science-Core-Collection-Advanced-Search-Field-Tags", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "wos_ui", canonical_field: "author", native_field: "AU", emitter_style: "PREFIX_COLON", restrictions: "No left truncation in AU", source_url: "https://webofscience.zendesk.com/hc/en-us/articles/26916347018257-Web-of-Science-Core-Collection-Advanced-Search-Field-Tags", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  // DOAJ (secondary)
  { platform_id: "doaj_api", canonical_field: "title", native_field: "title", emitter_style: "PREFIX_COLON", restrictions: "title:{kw}; JSON-schema field names", source_url: "https://doaj.org/docs/search/", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium" },
  { platform_id: "doaj_api", canonical_field: "abstract", native_field: "abstract", emitter_style: "PREFIX_COLON", restrictions: "abstract:\"{phrase}\"", source_url: "https://doaj.org/docs/search/", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium" },
  { platform_id: "doaj_api", canonical_field: "date", native_field: "bibjson.year", emitter_style: "LUCENE_FIELD", restrictions: "bibjson.year:[{a} TO {b}]", source_url: "https://doaj.org/docs/search/", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium" },
  // OpenAlex / Crossref (parametric, not field-tagged strings)
  { platform_id: "openalex_api", canonical_field: "title_abstract_keywords", native_field: "default.search", emitter_style: "PARAM", restrictions: "default.search param; use title.search for title-scoped", source_url: "https://developers.openalex.org/guides/filtering", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  { platform_id: "crossref_api", canonical_field: "title_abstract_keywords", native_field: "query", emitter_style: "PARAM", restrictions: "query param (bibliographic) or query.title/query.affiliation", source_url: "https://api.crossref.org/swagger-ui/index.html", evidence_tier: "VERIFIED OFFICIAL", confidence: "High" },
  // EBSCOhost / ProQuest / Springer (form controls where no command grammar verified)
  { platform_id: "ebscohost_ui", canonical_field: "title_abstract_keywords", native_field: "(form: TI/AB/SU select)", emitter_style: "FORM_CONTROL", restrictions: "Field dropdowns; platform tags need Tier 1 retrieval", source_url: "https://connect.ebsco.com/s/article/EBSCOhost-Searching-Tips?language=en_US", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium" },
  { platform_id: "springer_ui", canonical_field: "title", native_field: "Title (form field)", emitter_style: "FORM_CONTROL", restrictions: "Title:\"{phrase}\" pattern per support article", source_url: "https://support.springernature.com/en/support/solutions/articles/6000080445-springer-nature-link-advanced-search-option", evidence_tier: "VERIFIED OFFICIAL", confidence: "Medium" },
  { platform_id: "springer_ui", canonical_field: "title_abstract_keywords", native_field: "Keywords (form field)", emitter_style: "FORM_CONTROL", restrictions: "Keywords:({a} OR {b}) pattern", source_url: "https://support.springernature.com/en/support/solutions/articles/6000080445-springer-nature-link-advanced-search-option", evidence_tier: "VERIFIED OFFICIAL", confidence: "Medium" },
];

// ============================================
// Controlled-vocabulary mappings
// ============================================

export const VOCABULARY_MAPPINGS: VocabularyMapping[] = [
  { platform_id: "pubmed_api", vocabulary: "MeSH", canonical_action: "explode", native_template: "\"{heading}\"[Mesh]", restriction: "Default explode", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/" },
  { platform_id: "pubmed_api", vocabulary: "MeSH", canonical_action: "no_explode", native_template: "\"{heading}\"[Mesh:noexp]", restriction: "Suppress explode", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/" },
  { platform_id: "pubmed_api", vocabulary: "MeSH", canonical_action: "major", native_template: "{heading}[majr]", restriction: "Major topic", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/" },
  { platform_id: "pubmed_api", vocabulary: "MeSH", canonical_action: "subheading", native_template: "{subheading}[sh]", restriction: "Floating subheading, AND with heading", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/" },
  { platform_id: "pubmed_api", vocabulary: "MeSH", canonical_action: "publication_type", native_template: "\"{type}\"[pt]", restriction: "Systematic-review filters combine [pt]+[sb]", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://pubmed.ncbi.nlm.nih.gov/help/" },
  { platform_id: "ovid_medline_ui", vocabulary: "MeSH", canonical_action: "explode", native_template: "exp {heading}/", restriction: "Explode via exp prefix", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm" },
  { platform_id: "ovid_medline_ui", vocabulary: "MeSH", canonical_action: "no_explode", native_template: "{heading}/", restriction: "Plain heading search", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm" },
  { platform_id: "ovid_medline_ui", vocabulary: "MeSH", canonical_action: "major", native_template: "*{heading}/", restriction: "* prefix = major heading", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm" },
  { platform_id: "ovid_medline_ui", vocabulary: "MeSH", canonical_action: "subheading", native_template: "{heading}/{sh} + {sh}.fs.", restriction: "Attached (/sh) or floating (.fs.) subheadings", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://site.ovid.com/help/documentation/osp/en/Content/syntax.htm" },
  { platform_id: "embase_com_ui", vocabulary: "Emtree", canonical_action: "explode", native_template: "UI checkbox: Explode on '{term}'", restriction: "Query Builder checkbox, not inline syntax", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://www.elsevier.support/embase/answer/can-i-use-boolean-operators-wildcards-and-proximity-operators-in-embase" },
  { platform_id: "embase_com_ui", vocabulary: "Emtree", canonical_action: "major", native_template: "UI: As major focus on '{term}'", restriction: "Limits to main-topic records", evidence_tier: "VERIFIED OFFICIAL", confidence: "High", source_url: "https://www.elsevier.support/embase/answer/can-i-use-boolean-operators-wildcards-and-proximity-operators-in-embase" },
  { platform_id: "ebscohost_ui", vocabulary: "CINAHL Headings", canonical_action: "explode", native_template: "CINAHL Heading '{term}' + Explode checkbox", restriction: "Defaults often explode; Major Concept checkbox for focus", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", source_url: "https://connect.ebsco.com/s/article/EBSCOhost-Searching-Tips?language=en_US" },
  { platform_id: "eric_api", vocabulary: "ERIC Thesaurus", canonical_action: "descriptor_search", native_template: "DE=\"{descriptor}\"", restriction: "Multi-word descriptors quoted; Explode option in Thesaurus UI", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", source_url: "https://eric.ed.gov/?thesaurus" },
  { platform_id: "ebscohost_ui", vocabulary: "APA Thesaurus", canonical_action: "explode", native_template: "Thesaurus heading '{term}' (+ explode/focus via Ovid Term Finder or UI)", restriction: "Add multiple headings with Boolean; platform varies", evidence_tier: "SUPPORTED — SECONDARY EVIDENCE", confidence: "Medium", source_url: "https://psycnet.apa.org/" },
];

// ============================================
// Operator semantics (precedence preserved natively)
// ============================================

export const OPERATOR_PRECEDENCE: Record<string, string[]> = {
  // highest-first
  scopus_api: ["OR", "W/n, PRE/n", "AND", "AND NOT"],
  scopus_ui: ["OR", "W/n, PRE/n", "AND", "AND NOT"],
  wos_ui: ["NEAR/x", "SAME", "NOT", "AND", "OR"],
  sciencedirect_ui: ["NOT (-)", "AND (implicit too)", "OR"],
  pubmed_api: ["left-to-right; parentheses override; implicit AND between untagged concepts"],
  pubmed_ui: ["left-to-right; parentheses override; implicit AND between untagged concepts"],
  ovid_medline_ui: ["parentheses first, then left-to-right (no precedence between AND/OR/NOT)"],
  embase_com_ui: ["parentheses first, then left-to-right (no precedence difference)"],
  openalex_api: ["implicit AND only; no OR/NOT"],
  crossref_api: ["no Boolean; >=20% match + additive filters"],
  semantic_scholar_api: ["no Boolean; S2 matching"],
};

// ============================================
// Lookup helpers (pure)
// ============================================

export function getProfile(platform_id: string): PlatformProfile | undefined {
  return PLATFORM_PROFILES.find((p) => p.platform_id === platform_id);
}

export function getCapabilities(platform_id: string): CapabilityRecord[] {
  return CAPABILITIES.filter((c) => c.platform_id === platform_id);
}

export function getCapability(platform_id: string, capability: string): CapabilityRecord | undefined {
  return CAPABILITIES.find((c) => c.platform_id === platform_id && c.capability === capability);
}

export function getFieldMappings(platform_id: string): FieldMapping[] {
  return FIELD_MAPPINGS.filter((f) => f.platform_id === platform_id);
}

export function getVocabularyMappings(platform_id: string): VocabularyMapping[] {
  return VOCABULARY_MAPPINGS.filter((v) => v.platform_id === platform_id);
}
