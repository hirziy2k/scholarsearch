import { describe, it, expect } from "vitest";
import { checkExportGate } from "../services/export-gate.js";

describe("Export Gate", () => {
  const healthySources = [
    { source: "pubmed", status: "complete" as const, resultCount: 50 },
    { source: "scopus", status: "complete" as const, resultCount: 40 },
    { source: "openalex", status: "complete" as const, resultCount: 30 },
  ];

  const pubmedFailed = [
    { source: "pubmed", status: "error" as const, resultCount: 0 },
    { source: "scopus", status: "complete" as const, resultCount: 40 },
    { source: "openalex", status: "complete" as const, resultCount: 30 },
  ];

  const bothApexFailed = [
    { source: "pubmed", status: "error" as const, resultCount: 0 },
    { source: "scopus", status: "error" as const, resultCount: 0 },
    { source: "openalex", status: "complete" as const, resultCount: 30 },
  ];

  describe("systematic_review mode", () => {
    it("allows export when all sources healthy", () => {
      const result = checkExportGate("systematic_review", "ris", healthySources);
      expect(result.allowed).toBe(true);
    });

    it("blocks RIS when PubMed fails", () => {
      const result = checkExportGate("systematic_review", "ris", pubmedFailed);
      expect(result.allowed).toBe(false);
      expect(result.blockedReason).toContain("Apex source failure");
    });

    it("blocks all formats when both apex sources fail", () => {
      for (const format of ["ris", "csv", "json", "pdf"] as const) {
        const result = checkExportGate("systematic_review", format, bothApexFailed);
        expect(result.allowed).toBe(false);
      }
    });
  });

  describe("evidence mode", () => {
    it("allows export when all sources healthy", () => {
      const result = checkExportGate("evidence", "ris", healthySources);
      expect(result.allowed).toBe(true);
    });

    it("blocks RIS when PubMed fails (downgrade to PDF)", () => {
      const result = checkExportGate("evidence", "ris", pubmedFailed);
      expect(result.allowed).toBe(false);
      expect(result.downgradeTo).toBe("pdf");
      expect(result.watermark).toContain("CLINICAL BRIEF");
    });

    it("blocks CSV when PubMed fails (downgrade to PDF)", () => {
      const result = checkExportGate("evidence", "csv", pubmedFailed);
      expect(result.allowed).toBe(false);
      expect(result.downgradeTo).toBe("pdf");
    });

    it("allows PDF with watermark when PubMed fails", () => {
      const result = checkExportGate("evidence", "pdf", pubmedFailed);
      expect(result.allowed).toBe(true);
      expect(result.watermark).toContain("CLINICAL BRIEF");
    });

    it("allows JSON with watermark when PubMed fails", () => {
      const result = checkExportGate("evidence", "json", pubmedFailed);
      expect(result.allowed).toBe(true);
      expect(result.watermark).toContain("CLINICAL BRIEF");
    });
  });

  describe("other modes", () => {
    it("allows all exports in discovery mode regardless of source status", () => {
      const result = checkExportGate("discovery", "ris", pubmedFailed);
      expect(result.allowed).toBe(true);
    });

    it("allows all exports in thesis mode regardless of source status", () => {
      const result = checkExportGate("thesis", "csv", bothApexFailed);
      expect(result.allowed).toBe(true);
    });
  });
});
