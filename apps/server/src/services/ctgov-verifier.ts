// ============================================
// CT.gov Cross-Reference Verifier
// ============================================
// Verifies extracted NCT IDs against the ClinicalTrials.gov API.
// Fast-fail strategy: 5s timeout, circuit breaker (3 failures → open for 120s).
// When unavailable: paper tagged `ctgov_unavailable`, continues with reduced trust.
// NEVER blocks results — soft gate only.

import type { ExtractedTrialId } from "./metadata-verification.js";

// ============================================
// Circuit Breaker (CT.gov-specific)
// ============================================

interface CTGovCircuitState {
  failures: number;
  openUntil: number | null;
  lastSuccess: number | null;
}

const CTGOV_FAILURE_THRESHOLD = 3;
const CTGOV_OPEN_DURATION_MS = 120_000; // 2 minutes
const CTGOV_TIMEOUT_MS = 5_000;

let circuitState: CTGovCircuitState = {
  failures: 0,
  openUntil: null,
  lastSuccess: null,
};

function isCircuitOpen(): boolean {
  if (circuitState.openUntil === null) return false;
  if (Date.now() >= circuitState.openUntil) {
    // Half-open: allow one probe
    circuitState.openUntil = null;
    return false;
  }
  return true;
}

function recordCircuitSuccess(): void {
  circuitState.failures = 0;
  circuitState.openUntil = null;
  circuitState.lastSuccess = Date.now();
}

function recordCircuitFailure(): void {
  circuitState.failures++;
  circuitState.lastSuccess = null;
  if (circuitState.failures >= CTGOV_FAILURE_THRESHOLD) {
    circuitState.openUntil = Date.now() + CTGOV_OPEN_DURATION_MS;
    console.warn(
      `[ctgov-circuit] OPEN — ${circuitState.failures} consecutive failures. ` +
      `Re-probing in ${CTGOV_OPEN_DURATION_MS / 1000}s.`
    );
  }
}

// ============================================
// CT.gov API Response Types
// ============================================

interface CTGovStudy {
  NCTId: string[];
  BriefTitle?: string[];
  OfficialTitle?: string[];
  OverallStatus?: string[];
  CompletionDate?: Array<{ $: string }>;
  StartDate?: Array<{ $: string }>;
  Phase?: string[];
  StudyType?: string[];
  Condition?: string[];
  InterventionName?: string[];
  LeadSponsorName?: string[];
}

interface CTGovResponse {
  FullStudiesResponse?: {
    FullStudies?: Array<{ Study: CTGovStudy }>;
    NStudiesFound?: number;
  };
}

export interface CTGovVerificationResult {
  nctId: string;
  found: boolean;
  titleMatch: boolean;
  status: string | null;
  completionDate: string | null;
  phase: string | null;
  studyType: string | null;
  conditions: string[];
  interventions: string[];
  sponsor: string | null;
  verificationStatus: "verified" | "mismatch" | "not_found" | "ctgov_unavailable";
  confidence: number;
}

// ============================================
// Fetch with Timeout
// ============================================

async function fetchWithTimeout(
  url: string,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "Accept": "application/json",
      },
    });
    return response;
  } finally {
    clearTimeout(timer);
  }
}

// ============================================
// Title Similarity (Jaro-Winkler lite)
// ============================================

function normalizeTitle(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function titleSimilarity(a: string, b: string): number {
  const na = normalizeTitle(a);
  const nb = normalizeTitle(b);

  if (na === nb) return 1.0;
  if (na.includes(nb) || nb.includes(na)) return 0.95;

  // Simple token overlap
  const tokensA = new Set(na.split(" "));
  const tokensB = new Set(nb.split(" "));
  let overlap = 0;
  for (const t of tokensA) {
    if (tokensB.has(t)) overlap++;
  }
  return overlap / Math.max(tokensA.size, tokensB.size);
}

// ============================================
// Single NCT Verification
// ============================================

async function verifySingleNct(
  nctId: string,
  paperTitle?: string,
): Promise<CTGovVerificationResult> {
  const empty: CTGovVerificationResult = {
    nctId,
    found: false,
    titleMatch: false,
    status: null,
    completionDate: null,
    phase: null,
    studyType: null,
    conditions: [],
    interventions: [],
    sponsor: null,
    verificationStatus: "ctgov_unavailable",
    confidence: 0,
  };

  if (isCircuitOpen()) {
    return empty;
  }

  try {
    const url = `https://clinicaltrials.gov/api/v2/studies?query.id=${nctId}&format=json&pageSize=1`;
    const response = await fetchWithTimeout(url, CTGOV_TIMEOUT_MS);

    if (!response.ok) {
      recordCircuitFailure();
      return { ...empty, verificationStatus: "ctgov_unavailable" };
    }

    const data = (await response.json()) as CTGovResponse;
    recordCircuitSuccess();

    const studies = data.FullStudiesResponse?.FullStudies;
    if (!studies || studies.length === 0) {
      return {
        ...empty,
        found: false,
        verificationStatus: "not_found",
        confidence: 0.9,
      };
    }

    const study = studies[0].Study;
    const ctgovTitle = study.BriefTitle?.[0] ?? study.OfficialTitle?.[0] ?? "";
    const paperNorm = paperTitle ? normalizeTitle(paperTitle) : "";
    const ctgovNorm = normalizeTitle(ctgovTitle);

    const titleMatch = paperNorm && ctgovNorm
      ? titleSimilarity(paperTitle!, ctgovTitle) >= 0.7
      : false;

    const status = study.OverallStatus?.[0] ?? null;
    const completionDate = study.CompletionDate?.[0]?.$ ?? null;
    const phase = study.Phase?.[0] ?? null;
    const studyType = study.StudyType?.[0] ?? null;
    const conditions = study.Condition ?? [];
    const interventions = study.InterventionName ?? [];
    const sponsor = study.LeadSponsorName?.[0] ?? null;

    let verificationStatus: CTGovVerificationResult["verificationStatus"];
    let confidence: number;

    if (titleMatch) {
      verificationStatus = "verified";
      confidence = 1.0;
    } else if (paperNorm && ctgovNorm) {
      // Title mismatch — could be the same trial with different title
      verificationStatus = "mismatch";
      confidence = 0.5;
    } else {
      // Can't compare titles (missing data), but NCT found
      verificationStatus = "verified";
      confidence = 0.8;
    }

    return {
      nctId,
      found: true,
      titleMatch,
      status,
      completionDate,
      phase,
      studyType,
      conditions,
      interventions,
      sponsor,
      verificationStatus,
      confidence,
    };
  } catch (error) {
    // Timeout, network error, parse error — all treated as unavailable
    recordCircuitFailure();
    return { ...empty, verificationStatus: "ctgov_unavailable" };
  }
}

// ============================================
// Batch Verification
// ============================================

export async function verifyTrialRegistrations(
  trialIds: ExtractedTrialId[],
  paperTitle?: string,
): Promise<CTGovVerificationResult[]> {
  // Only verify NCT IDs via CT.gov API
  const nctIds = trialIds.filter((t) => t.registry === "NCT");

  if (nctIds.length === 0) {
    return [];
  }

  // Verify sequentially to respect rate limits
  const results: CTGovVerificationResult[] = [];
  for (const trial of nctIds) {
    const result = await verifySingleNct(trial.id, paperTitle);
    results.push(result);
  }

  return results;
}

/**
 * Get circuit status for diagnostics.
 */
export function getCTGovCircuitStatus(): {
  failures: number;
  isOpen: boolean;
  openUntil: number | null;
  lastSuccess: number | null;
} {
  return {
    failures: circuitState.failures,
    isOpen: isCircuitOpen(),
    openUntil: circuitState.openUntil,
    lastSuccess: circuitState.lastSuccess,
  };
}

/**
 * Reset circuit breaker (for testing).
 */
export function resetCTGovCircuit(): void {
  circuitState = { failures: 0, openUntil: null, lastSuccess: null };
}
