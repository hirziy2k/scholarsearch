// ============================================
// Database-Native Syntax Resolver / Validator / Renderer
// ============================================
//
// Implementation layer over data/native-syntax-registry.ts.
// Governing rule: an adapter must only emit functionality verified
// in the registry for the target database + interface.
//
// - Canonical AST (from query-parser.ts) carries CONCEPTUAL logic.
// - This module resolves the target profile, gates capabilities by
//   evidence tier, validates the request, renders NATIVE strings,
//   and pairs every output with a provenance manifest.
// - Unsupported features are NEVER silently substituted.
//   Modes: fail | warn_and_omit | warn_and_downgrade (default OFF for
//   systematic/scoping searches) | form_only.
//
// Pure module: no network, no fs, no credentials.

import {
  getProfile,
  getCapability,
  REGISTRY_VERSION,
  type CapabilityRecord,
  type EvidenceTier,
} from "../data/native-syntax-registry.js";
import type { ASTNode } from "./query-parser.js";

// ============================================
// Translation policy
// ============================================

export type UnsupportedMode = "fail" | "warn_and_omit" | "warn_and_downgrade" | "form_only";

export interface TranslationPolicy {
  require_tier: EvidenceTier; // minimum tier that passes without warning
  allow_secondary_with_warning: boolean;
  allow_unverified: boolean;
  unsupported_feature_mode: UnsupportedMode;
}

/** Strict default for systematic/scoping review work. */
export const DEFAULT_STRICT_POLICY: TranslationPolicy = {
  require_tier: "VERIFIED OFFICIAL",
  allow_secondary_with_warning: true,
  allow_unverified: false,
  unsupported_feature_mode: "warn_and_omit",
};

// ============================================
// Capability resolution + evidence gate
// ============================================

export type CapabilityVerdict =
  | { allowed: true; record: CapabilityRecord; warning: null }
  | { allowed: true; record: CapabilityRecord; warning: string }
  | { allowed: false; record: CapabilityRecord | null; reason: string };

export function requireCapability(
  platform_id: string,
  capability: string,
  policy: TranslationPolicy = DEFAULT_STRICT_POLICY,
): CapabilityVerdict {
  const profile = getProfile(platform_id);
  if (!profile) {
    return { allowed: false, record: null, reason: `Unknown target profile: ${platform_id}` };
  }
  const record = getCapability(platform_id, capability);
  if (!record) {
    return { allowed: false, record: null, reason: `Capability '${capability}' not in registry for ${platform_id}` };
  }
  if (record.impl_status === "NOT_APPLICABLE") {
    return { allowed: false, record, reason: `Capability '${capability}' is NOT_APPLICABLE on ${platform_id}: ${record.restriction}` };
  }
  if (record.impl_status === "UNVERIFIED") {
    if (policy.allow_unverified) {
      return { allowed: true, record, warning: `UNVERIFIED capability '${capability}' on ${platform_id} emitted with warning` };
    }
    return { allowed: false, record, reason: `UNVERIFIED capability '${capability}' on ${platform_id} blocked by policy` };
  }
  if (record.impl_status === "DEPRECATED") {
    return { allowed: false, record, reason: `DEPRECATED capability '${capability}' on ${platform_id}` };
  }
  if (record.evidence_tier === "VERIFIED OFFICIAL") {
    return { allowed: true, record, warning: null };
  }
  if (record.evidence_tier === "SUPPORTED — SECONDARY EVIDENCE") {
    if (policy.allow_secondary_with_warning) {
      return { allowed: true, record, warning: `Secondary-evidence capability '${capability}' on ${platform_id}: ${record.restriction}` };
    }
    return { allowed: false, record, reason: `Secondary-evidence capability '${capability}' on ${platform_id} blocked by policy` };
  }
  return { allowed: false, record, reason: `Capability '${capability}' on ${platform_id} fails evidence gate` };
}

// ============================================
// Feature detection on raw query text
// ============================================

export interface DetectedFeatures {
  has_truncation_star: boolean;
  has_wildcard_qmark: boolean;
  has_wildcard_dollar_hash: boolean;
  has_proximity_explicit: boolean; // NEAR/NEXT/W//PRE//ADJ/SAME/AROUND/~n
  has_field_syntax: boolean; // TITLE-ABS-KEY, [tag], .ti, TS=, DE=, field:
  has_mesh_syntax: boolean; // [Mesh], [majr], [sh], exp ../
  has_boolean_or: boolean;
  has_boolean_not: boolean;
  proximity_truncation_conflict: boolean; // PubMed: * inside a proximity span
}

const PROX_RE = /\b(NEAR|NEXT|ONEAR|ADJ|SAME|AROUND)\s*\/?\s*\d*|(\bW\/\d+)|(\bPRE\/\d+)|"\s*[^"]+"\s*~\s*\d+|:\s*~\s*\d+|~\d+/i;
const FIELD_RE = /(TITLE-ABS-KEY|TITLE|ABS|SUBJAREA|DOCTYPE|\[[a-z]{1,6}(:~\d+)?\]|\.(ti|ab|kf|mp)\b|\b(TS|TI|AU|SO|DO|PMID)=|DE\s*=|[a-z_.]+\s*:\s*["\w])/i;
const MESH_RE = /(\[mesh(:noexp)?\]|\[majr\]|\[sh\]|\bexp\s+\S+\/|\*\S+\/)/i;

export function detectNativeFeatures(rawQuery: string): DetectedFeatures {
  const has_star = rawQuery.includes("*");
  const has_q = rawQuery.includes("?");
  const has_dh = rawQuery.includes("$") || rawQuery.includes("#");
  const has_prox = PROX_RE.test(rawQuery);
  const has_field = FIELD_RE.test(rawQuery);
  const has_mesh = MESH_RE.test(rawQuery);
  const upper = ` ${rawQuery.toUpperCase()} `;
  const has_or = /\bOR\b/.test(upper);
  // Scopus-style AND NOT vs bare NOT; hyphen-minus NOT handled per-target
  const has_not = /\b(AND\s+NOT|NOT)\b/.test(upper) || /(^|\s)-["\w]/.test(rawQuery);
  // PubMed conflict heuristic: truncation star inside quotes that also carry :~N
  const proximity_truncation_conflict = has_star && /\[ *(ti|tiab|ad) *:~\d+ *\]/.test(rawQuery.toLowerCase());
  return {
    has_truncation_star: has_star,
    has_wildcard_qmark: has_q,
    has_wildcard_dollar_hash: has_dh,
    has_proximity_explicit: has_prox,
    has_field_syntax: has_field,
    has_mesh_syntax: has_mesh,
    has_boolean_or: has_or,
    has_boolean_not: has_not,
    proximity_truncation_conflict,
  };
}

// ============================================
// Validation
// ============================================

export interface SyntaxWarning {
  code: string;
  target: string;
  requested: string;
  action: "omitted" | "downgraded" | "flagged" | "form_only";
  reason: string;
  impact: string;
  requires_human_review: boolean;
}

export interface ValidationResult {
  ok: boolean;
  errors: string[];
  warnings: SyntaxWarning[];
}

function warn(
  code: string, target: string, requested: string, reason: string, impact: string,
  action: SyntaxWarning["action"] = "flagged",
): SyntaxWarning {
  return { code, target, requested, action, reason, impact, requires_human_review: true };
}

/**
 * Validate a conceptual request against ONE target profile.
 * Never errors on plain Boolean+phrase (portable core). Flags everything
 * natively distinct so callers cannot mistake generic output for native.
 */
export function validateForTarget(
  rawQuery: string,
  platform_id: string,
  policy: TranslationPolicy = DEFAULT_STRICT_POLICY,
): ValidationResult {
  const errors: string[] = [];
  const warnings: SyntaxWarning[] = [];
  const profile = getProfile(platform_id);
  if (!profile) {
    return { ok: false, errors: [`Unknown target profile: ${platform_id}`], warnings };
  }
  const f = detectNativeFeatures(rawQuery);

  // PubMed hard constraint: no truncation inside proximity
  if ((platform_id === "pubmed_api" || platform_id === "pubmed_ui") && f.proximity_truncation_conflict) {
    errors.push("PUBMED_PROXIMITY_TRUNCATION_CONFLICT: PubMed forbids truncation inside [ti|tiab|ad:~N] proximity expressions.");
  }

  // APIs with no Boolean must be told when the request needs Boolean
  if ((platform_id === "crossref_api" || platform_id === "crossref_api_ui") && (f.has_boolean_or || f.has_boolean_not)) {
    warnings.push(warn("UNSUPPORTED_BOOLEAN", platform_id, f.has_boolean_or ? "OR" : "NOT",
      "Crossref REST API has no Boolean operators (VERIFIED OFFICIAL); scoring + additive filters only.",
      "Boolean logic must be applied client-side; retrieved set may differ in precision.", "omitted"));
  }
  if (platform_id === "openalex_api" && (f.has_boolean_or || f.has_boolean_not)) {
    warnings.push(warn("UNSUPPORTED_BOOLEAN", platform_id, f.has_boolean_or ? "OR" : "NOT",
      "OpenAlex filter language has no OR/NOT (VERIFIED OFFICIAL); implicit AND only.",
      "Use local-intersection compensator / client-side union-exclusion.", "omitted"));
  }
  if ((platform_id === "semantic_scholar_api" || platform_id === "semanticscholar_ui") && (f.has_boolean_or || f.has_boolean_not || f.has_truncation_star || f.has_wildcard_qmark)) {
    warnings.push(warn("UNSUPPORTED_BOOLEAN_WILDCARD", platform_id, "Boolean/wildcard",
      "Semantic Scholar officially reports no Boolean or wildcard support (VERIFIED OFFICIAL); quoted phrases only.",
      "Potentially lower precision; filter client-side.", "omitted"));
  }

  // Proximity requested on a target without a verified proximity operator
  const noProxTargets = new Set(["openalex_api", "crossref_api", "crossref_api_ui", "semantic_scholar_api", "semanticscholar_ui", "core_api", "sciencedirect_ui", "springer_ui", "googlescholar_ui", "europepmc_ui", "europepmc_api"]);
  if (f.has_proximity_explicit && noProxTargets.has(platform_id)) {
    const mode = policy.unsupported_feature_mode;
    if (mode === "fail") {
      errors.push(`UNSUPPORTED_PROXIMITY: ${platform_id} has no verified proximity syntax; failing per policy.`);
    } else {
      warnings.push(warn("UNSUPPORTED_PROXIMITY", platform_id, "proximity operator",
        `${platform_id} has no verified proximity syntax in the registry.`,
        "Proximity constraint omitted; recall rises, precision falls.", mode === "form_only" ? "form_only" : "omitted"));
    }
  }

  // Unverified-feature requests never pass silently
  if (platform_id === "googlescholar_ui" && /AROUND/i.test(rawQuery)) {
    if (policy.allow_unverified) {
      warnings.push(warn("UNVERIFIED_AROUND", platform_id, "AROUND(n)", "AROUND(n) appears in secondary guides only (UNVERIFIED).", "May not execute as proximity.", "flagged"));
    } else {
      errors.push("UNVERIFIED_AROUND: AROUND(n) on Google Scholar is UNVERIFIED and blocked by policy.");
    }
  }
  if ((platform_id === "europepmc_ui" || platform_id === "europepmc_api") && (f.has_proximity_explicit || f.has_truncation_star)) {
    const msg = `Europe PMC proximity/truncation lacks verified current syntax (${platform_id}).`;
    if (policy.allow_unverified) warnings.push(warn("UNVERIFIED_EUROPEPMC", platform_id, "proximity/truncation", msg, "Validate against /rest/fields + UI before use.", "flagged"));
    else errors.push(`UNVERIFIED_EUROPEPMC: ${msg}`);
  }
  if (platform_id === "core_api" && (f.has_proximity_explicit || f.has_field_syntax)) {
    warnings.push(warn("UNVERIFIED_CORE", platform_id, "native syntax", "CORE has no syntax row in the evidence package (UNVERIFIED); q passthrough only.", "No native claim possible.", "flagged"));
  }

  // Secondary-evidence targets always carry a warning (never silent)
  const secondaryTargets = new Set(["eric_api", "doaj_api", "ebscohost_ui", "proquest_ui", "cochrane_ui", "ieee_ui", "jstor_ui", "wiley_ui", "tandf_ui", "sage_ui", "doaj_ui"]);
  if (secondaryTargets.has(platform_id)) {
    warnings.push(warn("SECONDARY_EVIDENCE", platform_id, "all features",
      `${platform_id} capability rows rest on secondary (Tier 3–5) evidence; Tier 1 recheck outstanding.`,
      "Confirm against vendor docs before protocol use.", "flagged"));
  }

  return { ok: errors.length === 0, errors, warnings };
}

// ============================================
// Native renderers (conceptual AST → native string)
// ============================================

function renderInfix(ast: ASTNode, join: (op: string, parts: string[]) => string, leaf: (v: string, phrase: boolean) => string): string {
  switch (ast.type) {
    case "term": return leaf(ast.value, false);
    case "phrase": return leaf(ast.value, true);
    case "and": return join("AND", [renderInfix(ast.left, join, leaf), renderInfix(ast.right, join, leaf)]);
    case "or": return join("OR", [renderInfix(ast.left, join, leaf), renderInfix(ast.right, join, leaf)]);
    case "not": return join("NOT", [renderInfix(ast.operand, join, leaf)]);
  }
}

const paren = (op: string, parts: string[]) =>
  op === "NOT" ? `NOT ${parts[0]}` : `(${parts.join(` ${op} `)})`;

/**
 * Scopus native Boolean core (API + UI share grammar).
 * Negation uses Scopus AND NOT form; a top-level unary NOT is emitted
 * as NOT (x) with a validation warning (Scopus expects `a AND NOT b`).
 * Proximity (W/n, PRE/n) has no AST node yet → NEEDS_ADAPTER; this
 * renderer covers the portable Boolean+phrase core only.
 */
export function renderScopusNative(ast: ASTNode): string {
  switch (ast.type) {
    case "term": return `"${ast.value}"`;
    case "phrase": return `"${ast.value}"`;
    case "and": return `(${renderScopusNative(ast.left)} AND ${renderScopusNative(ast.right)})`;
    case "or": return `(${renderScopusNative(ast.left)} OR ${renderScopusNative(ast.right)})`;
    case "not": return `NOT (${renderScopusNative(ast.operand)})`;
  }
}

/** Wrap a Scopus Boolean core in TITLE-ABS-KEY with year/doctype limits. */
export function renderScopusFielded(ast: ASTNode, opts?: { yearFrom?: number; yearTo?: number; doctype?: string }): string {
  const core = renderScopusNative(ast);
  let q = `TITLE-ABS-KEY(${core})`;
  if (opts?.yearFrom) q += ` AND PUBYEAR AFT ${opts.yearFrom - 1}`;
  if (opts?.yearTo) q += ` AND PUBYEAR BEF ${opts.yearTo + 1}`;
  if (opts?.doctype) q += ` AND DOCTYPE(${opts.doctype})`;
  return q;
}

/**
 * PubMed fielded renderer: (expr)[tiab] core + optional MeSH heading
 * lines. Truncation/proximity nodes do not exist in the AST yet, so
 * this renderer refuses to invent them — use validateForTarget first.
 */
export function renderPubMedFielded(ast: ASTNode, field: "ti" | "tiab" | "ad" | "All Fields" = "tiab"): string {
  const core = renderInfix(ast, paren, (v) => `"${v}"`);
  return `(${core})[${field}]`;
}

/** MeSH heading line renderer (explode / no-explode / major / subheading). */
export function renderMeSHHeading(
  heading: string,
  opts?: { explode?: boolean; major?: boolean; subheadings?: string[] },
): string {
  const q = (s: string) => `"${s}"`;
  if (opts?.major) return `${q(heading)}[majr]`;
  if (opts?.explode === false) return `${q(heading)}[Mesh:noexp]`;
  const base = `${q(heading)}[Mesh]`;
  if (opts?.subheadings?.length) {
    return `${base} AND (${opts.subheadings.map((s) => `${s}[sh]`).join(" OR ")})`;
  }
  return base;
}

/** ERIC descriptor line renderer (secondary evidence — validate first). */
export function renderERICDescriptor(descriptor: string): string {
  return `DE="${descriptor}"`;
}

/** DOAJ fielded fragment renderer (secondary evidence — validate first). */
export function renderDOAJFielded(field: string, keyword: string, phrase = true): string {
  return `${field}:${phrase ? `"${keyword}"` : keyword}`;
}

// ============================================
// Provenance manifest
// ============================================

export interface ProvenanceManifest {
  target: { platform_id: string; database: string; interface: string; ui_or_api: string };
  registry_version: string;
  generated_at: string;
  query: string;
  capabilities_used: Array<{ feature: string; evidence_tier: EvidenceTier; source_url: string }>;
  warnings: SyntaxWarning[];
  omitted_features: string[];
  human_review_required: boolean;
}

export function provenanceManifest(
  platform_id: string,
  query: string,
  capabilityNames: string[],
  warnings: SyntaxWarning[] = [],
  omitted: string[] = [],
): ProvenanceManifest {
  const profile = getProfile(platform_id);
  return {
    target: {
      platform_id,
      database: profile?.database ?? platform_id,
      interface: profile?.interface ?? "",
      ui_or_api: profile?.ui_or_api ?? "",
    },
    registry_version: REGISTRY_VERSION,
    generated_at: new Date().toISOString(),
    query,
    capabilities_used: capabilityNames.map((feature) => {
      const rec = getCapability(platform_id, feature);
      return {
        feature,
        evidence_tier: (rec?.evidence_tier ?? "UNVERIFIED") as EvidenceTier,
        source_url: rec?.source_url ?? profile?.source_url ?? "",
      };
    }),
    warnings,
    omitted_features: omitted,
    human_review_required: warnings.length > 0 || omitted.length > 0,
  };
}

// ============================================
// Search-term assistance classification
// ============================================
//
// Suggestions must NEVER auto-promote into the approved strategy.
// Approved protocol terminology stays byte-equivalent; everything else
// is labelled CANDIDATE / EXPERIMENTAL / REJECTED for researcher review.

export type TermStatus = "APPROVED" | "EXISTING" | "CANDIDATE" | "EXPERIMENTAL" | "REJECTED";

export function classifyTerm(
  term: string,
  approved: ReadonlySet<string> | readonly string[],
  existing: ReadonlySet<string> | readonly string[],
  rejected: ReadonlySet<string> | readonly string[] = [],
): TermStatus {
  const norm = (s: string) => s.toLowerCase().trim();
  const has = (c: ReadonlySet<string> | readonly string[], t: string) =>
    Array.isArray(c) ? c.map(norm).includes(norm(t)) : (c as Set<string>).has(t) || (c as Set<string>).has(norm(t));
  if (has(rejected, term)) return "REJECTED";
  if (has(approved, term)) return "APPROVED";
  if (has(existing, term)) return "EXISTING";
  // Heuristic: multi-word novel phrases and controlled-vocab candidates
  // default to CANDIDATE; wildcard/proximity formulations to EXPERIMENTAL.
  if (/[*?~]/.test(term) || PROX_RE.test(term)) return "EXPERIMENTAL";
  return "CANDIDATE";
}
