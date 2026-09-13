// ============================================
// Export Gate with Apex Source Lock
// ============================================
//
// Enforces export restrictions based on mode and source availability:
//
// systematic_review mode:
//   - PubMed OR Scopus failure → HARD BAN on all exports
//   - Rationale: Systematic reviews require comprehensive evidence;
//     incomplete source coverage invalidates the review
//
// evidence mode (clinical):
//   - PubMed OR Scopus failure → DOWNGRADE (not ban)
//   - RIS/CSV exports BLOCKED (prevents reference manager pollution)
//   - PDF "Clinical Brief" ALLOWED (watermarked, for immediate triage)
//   - Rationale: Clinicians need immediate directional answers;
//     hard-banning would paralyze point-of-care decisions

import { getDb } from "../db.js";

export type ExportFormat = "ris" | "csv" | "json" | "pdf";

export interface ExportGateResult {
  allowed: boolean;
  format: ExportFormat;
  reason?: string;
  downgradeTo?: ExportFormat;
  watermark?: string;
  blockedReason?: string;
}

interface SourceStatus {
  source: string;
  status: "complete" | "error" | "pending";
  resultCount: number;
}

// Apex sources for the lock
const APEX_SOURCES = new Set(["pubmed", "scopus"]);

/**
 * Check if export is allowed based on mode and source availability.
 */
export function checkExportGate(
  mode: string,
  format: ExportFormat,
  sourceStatuses: SourceStatus[],
): ExportGateResult {
  const apexStatuses = sourceStatuses.filter((s) => APEX_SOURCES.has(s.source));
  const apexFailed = apexStatuses.some((s) => s.status === "error");
  const apexFailureSources = apexStatuses
    .filter((s) => s.status === "error")
    .map((s) => s.source);

  // --- systematic_review: absolute hard-ban ---
  if (mode === "systematic_review" && apexFailed) {
    return {
      allowed: false,
      format,
      blockedReason: `Export blocked: Apex source failure in systematic review mode. Failed: ${apexFailureSources.join(", ")}. Systematic reviews require comprehensive source coverage per PRISMA guidelines.`,
      reason: "Apex source lock: systematic_review mode requires all apex sources operational",
    };
  }

  // --- evidence mode: downgrade, not ban ---
  if (mode === "evidence" && apexFailed) {
    // RIS and CSV are blocked (reference manager pollution)
    if (format === "ris" || format === "csv") {
      return {
        allowed: false,
        format,
        downgradeTo: "pdf",
        blockedReason: `RIS/CSV export blocked in evidence mode with apex failure (${apexFailureSources.join(", ")}). Download a watermarked Clinical Brief PDF instead.`,
        reason: "Apex source lock: evidence mode blocks systematic reference formats during degradation",
        watermark: `CLINICAL BRIEF — Generated during partial source availability. Apex failures: ${apexFailureSources.join(", ")}. For directional guidance only — verify against full source set before clinical decisions.`,
      };
    }

    // JSON is allowed but watermarked
    if (format === "json") {
      return {
        allowed: true,
        format,
        watermark: `CLINICAL BRIEF — Partial source availability. Apex failures: ${apexFailureSources.join(", ")}`,
        reason: "JSON export allowed with clinical brief watermark",
      };
    }

    // PDF is allowed with watermark
    if (format === "pdf") {
      return {
        allowed: true,
        format,
        watermark: `CLINICAL BRIEF — Generated during partial source availability. Apex failures: ${apexFailureSources.join(", ")}. For directional guidance only — verify against full source set before clinical decisions.`,
        reason: "PDF Clinical Brief allowed during apex degradation",
      };
    }
  }

  // --- All sources healthy: full export allowed ---
  return {
    allowed: true,
    format,
    reason: "All sources operational — full export permitted",
  };
}

/**
 * Record an export attempt in the audit log.
 */
export async function recordExportAttempt(
  sessionId: string,
  format: ExportFormat,
  result: ExportGateResult,
  resultCount: number,
): Promise<void> {
  const db = getDb();

  // Find the search session by searchId
  const session = await db.searchSession.findFirst({ where: { searchId: sessionId } });
  if (!session) return;

  await db.exportRecord.create({
    data: {
      sessionId: session.id,
      format,
      status: result.allowed ? "complete" : "blocked",
      blockedReason: result.blockedReason ?? null,
      watermarked: !!result.watermark,
      watermarkText: result.watermark ?? null,
      resultCount: result.allowed ? resultCount : 0,
      completedAt: result.allowed ? new Date() : null,
    },
  });
}

/**
 * Get export history for a session.
 */
export async function getExportHistory(sessionId: string) {
  const db = getDb();
  const session = await db.searchSession.findFirst({ where: { searchId: sessionId } });
  if (!session) return [];

  return db.exportRecord.findMany({
    where: { sessionId: session.id },
    orderBy: { createdAt: "desc" },
  });
}
