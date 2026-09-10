// ============================================
// Regional Triage Card Component
// ============================================
//
// Austere clinical interface for paper verification.
// Visual schema: white/off-white bg, charcoal typography,
// soft amber border for unverified papers.
//
// Joint Technical Committee compliance: focus, not fireworks.

import React, { useState, useCallback } from "react";

// ============================================
// Design Tokens
// ============================================

const TOKENS = {
  bg: "#FAFAFA",
  bgCard: "#FFFFFF",
  text: "#2D2D2D",
  textSecondary: "#6B6B6B",
  textMuted: "#999999",
  border: "#E5E5E5",
  borderTriage: "#E8A317", // Soft amber for unverified
  borderVerified: "#4A8C5C", // Muted green for verified
  borderExcluded: "#C44D4D", // Muted red for excluded
  font: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  fontSize: "14px",
  lineHeight: "1.5",
} as const;

// ============================================
// Types
// ============================================

export type TriageStatus = "pending" | "confirmed" | "excluded" | "flagged";

export interface TriagePaper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  journal: string;
  doi: string | null;
  source: string;
  country: string | null;
  trialIds: Array<{ registry: string; id: string }>;
  verificationStatus: "verified" | "unverified" | "regional" | "ctgov_unavailable";
  rankingScores: Record<string, number>;
}

export interface TriageCardProps {
  paper: TriagePaper;
  onAdjudicate: (paperId: string, action: "confirm" | "exclude" | "flag_for_review", reason?: string) => void;
}

// ============================================
// Triage Card Component
// ============================================

export function TriageCard({ paper, onAdjudicate }: TriageCardProps) {
  const [status, setStatus] = useState<TriageStatus>("pending");
  const [reason, setReason] = useState("");
  const [showReason, setShowReason] = useState(false);

  const handleAdjudicate = useCallback((action: "confirm" | "exclude" | "flag_for_review") => {
    if (action === "exclude" && !reason) {
      setShowReason(true);
      return;
    }
    setStatus(action === "confirm" ? "confirmed" : action === "exclude" ? "excluded" : "flagged");
    onAdjudicate(paper.id, action, reason || undefined);
  }, [paper.id, reason, onAdjudicate]);

  const borderColor = status === "confirmed" ? TOKENS.borderVerified
    : status === "excluded" ? TOKENS.borderExcluded
    : paper.verificationStatus === "regional" || paper.verificationStatus === "ctgov_unavailable"
    ? TOKENS.borderTriage
    : TOKENS.border;

  return (
    <div
      style={{
        background: TOKENS.bgCard,
        border: `1px solid ${borderColor}`,
        borderRadius: "4px",
        padding: "16px",
        marginBottom: "12px",
        fontFamily: TOKENS.font,
        fontSize: TOKENS.fontSize,
        lineHeight: TOKENS.lineHeight,
        color: TOKENS.text,
      }}
    >
      {/* Title */}
      <div style={{ fontWeight: 600, marginBottom: "4px" }}>
        {paper.title}
      </div>

      {/* Authors + Year */}
      <div style={{ color: TOKENS.textSecondary, marginBottom: "4px" }}>
        {paper.authors.slice(0, 3).join(", ")}
        {paper.authors.length > 3 ? ` et al.` : ""}
        {" "}({paper.year})
      </div>

      {/* Journal + Source */}
      <div style={{ color: TOKENS.textSecondary, fontSize: "13px", marginBottom: "8px" }}>
        {paper.journal} | {paper.source}
      </div>

      {/* Trial Registration IDs */}
      {paper.trialIds.length > 0 && (
        <div style={{ fontSize: "12px", color: TOKENS.textMuted, marginBottom: "8px" }}>
          {paper.trialIds.map((t) => (
            <span key={t.id} style={{ marginRight: "8px" }}>
              {t.registry}: {t.id}
            </span>
          ))}
        </div>
      )}

      {/* Verification Status Badge */}
      <div style={{ marginBottom: "12px" }}>
        <span
          style={{
            display: "inline-block",
            padding: "2px 8px",
            borderRadius: "2px",
            fontSize: "12px",
            fontWeight: 500,
            background: paper.verificationStatus === "verified" ? "#E8F5E9"
              : paper.verificationStatus === "regional" ? "#FFF8E1"
              : paper.verificationStatus === "ctgov_unavailable" ? "#FFF3E0"
              : "#F5F5F5",
            color: paper.verificationStatus === "verified" ? "#2E7D32"
              : paper.verificationStatus === "regional" ? "#F57F17"
              : paper.verificationStatus === "ctgov_unavailable" ? "#E65100"
              : "#757575",
          }}
        >
          {paper.verificationStatus === "verified" ? "Verified"
            : paper.verificationStatus === "regional" ? "Regional — Unverified"
            : paper.verificationStatus === "ctgov_unavailable" ? "CT.gov Unavailable"
            : "Unverified"}
        </span>
      </div>

      {/* Adjudication Buttons — only shown when pending */}
      {status === "pending" && (
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={() => handleAdjudicate("confirm")}
            style={{
              padding: "6px 12px",
              border: `1px solid ${TOKENS.borderVerified}`,
              borderRadius: "2px",
              background: "transparent",
              color: TOKENS.borderVerified,
              cursor: "pointer",
              fontSize: "13px",
              fontFamily: TOKENS.font,
            }}
          >
            Confirm
          </button>
          <button
            onClick={() => handleAdjudicate("exclude")}
            style={{
              padding: "6px 12px",
              border: `1px solid ${TOKENS.borderExcluded}`,
              borderRadius: "2px",
              background: "transparent",
              color: TOKENS.borderExcluded,
              cursor: "pointer",
              fontSize: "13px",
              fontFamily: TOKENS.font,
            }}
          >
            Exclude
          </button>
          <button
            onClick={() => handleAdjudicate("flag_for_review")}
            style={{
              padding: "6px 12px",
              border: `1px solid ${TOKENS.borderTriage}`,
              borderRadius: "2px",
              background: "transparent",
              color: TOKENS.borderTriage,
              cursor: "pointer",
              fontSize: "13px",
              fontFamily: TOKENS.font,
            }}
          >
            Flag for Review
          </button>
        </div>
      )}

      {/* Reason input for exclusion */}
      {showReason && status === "pending" && (
        <div style={{ marginTop: "8px" }}>
          <input
            type="text"
            placeholder="Reason for exclusion (required)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 8px",
              border: `1px solid ${TOKENS.border}`,
              borderRadius: "2px",
              fontSize: "13px",
              fontFamily: TOKENS.font,
              color: TOKENS.text,
              boxSizing: "border-box",
            }}
          />
          <button
            onClick={() => handleAdjudicate("exclude")}
            disabled={!reason}
            style={{
              marginTop: "4px",
              padding: "6px 12px",
              border: `1px solid ${TOKENS.borderExcluded}`,
              borderRadius: "2px",
              background: reason ? TOKENS.borderExcluded : "transparent",
              color: reason ? "#FFFFFF" : TOKENS.borderExcluded,
              cursor: reason ? "pointer" : "not-allowed",
              fontSize: "13px",
              fontFamily: TOKENS.font,
            }}
          >
            Confirm Exclusion
          </button>
        </div>
      )}

      {/* Status confirmation */}
      {status !== "pending" && (
        <div style={{ fontSize: "12px", color: TOKENS.textMuted, marginTop: "4px" }}>
          {status === "confirmed" ? "Confirmed" : status === "excluded" ? "Excluded" : "Flagged for review"}
        </div>
      )}
    </div>
  );
}

// ============================================
// Triage Panel Component
// ============================================

export interface TriagePanelProps {
  papers: TriagePaper[];
  onAdjudicate: (paperId: string, action: "confirm" | "exclude" | "flag_for_review", reason?: string) => void;
  onBulkAdjudicate: (action: "confirm" | "exclude") => void;
}

export function TriagePanel({ papers, onAdjudicate, onBulkAdjudicate }: TriagePanelProps) {
  const pending = papers.filter((p) => !p.trialIds.length || p.verificationStatus !== "verified");
  const verified = papers.filter((p) => p.verificationStatus === "verified");

  return (
    <div
      style={{
        background: TOKENS.bg,
        padding: "24px",
        fontFamily: TOKENS.font,
        color: TOKENS.text,
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "18px", fontWeight: 600, margin: "0 0 4px 0" }}>
          Regional Triage
        </h2>
        <p style={{ fontSize: "13px", color: TOKENS.textSecondary, margin: 0 }}>
          {pending.length} papers pending verification | {verified.length} verified
        </p>
      </div>

      {/* Bulk actions */}
      {pending.length > 0 && (
        <div style={{ marginBottom: "16px", display: "flex", gap: "8px" }}>
          <button
            onClick={() => onBulkAdjudicate("confirm")}
            style={{
              padding: "6px 12px",
              border: `1px solid ${TOKENS.borderVerified}`,
              borderRadius: "2px",
              background: "transparent",
              color: TOKENS.borderVerified,
              cursor: "pointer",
              fontSize: "13px",
              fontFamily: TOKENS.font,
            }}
          >
            Confirm All Pending
          </button>
        </div>
      )}

      {/* Pending papers */}
      {pending.map((paper) => (
        <TriageCard key={paper.id} paper={paper} onAdjudicate={onAdjudicate} />
      ))}

      {/* Verified papers (collapsed) */}
      {verified.length > 0 && (
        <details style={{ marginTop: "16px" }}>
          <summary style={{ cursor: "pointer", color: TOKENS.textSecondary, fontSize: "13px" }}>
            {verified.length} verified papers (click to expand)
          </summary>
          {verified.map((paper) => (
            <TriageCard key={paper.id} paper={paper} onAdjudicate={onAdjudicate} />
          ))}
        </details>
      )}
    </div>
  );
}
