import { describe, it, expect } from "vitest";
import {
  extractTrialIds,
  hasTrialRegistration,
  getPrimaryTrialId,
} from "../services/metadata-verification.js";

describe("Trial Registration ID Extractor", () => {
  describe("extractTrialIds", () => {
    it("extracts NCT IDs from title", () => {
      const result = extractTrialIds({
        title: "A study of NCT01234567 for dry eye treatment",
      });
      expect(result).toHaveLength(1);
      expect(result[0].registry).toBe("NCT");
      expect(result[0].id).toBe("NCT01234567");
      expect(result[0].confidence).toBe(1.0);
    });

    it("extracts multiple NCT IDs from abstract", () => {
      const result = extractTrialIds({
        title: "Comparison trial",
        abstract: "We enrolled patients from NCT01111111 and NCT02222222",
      });
      expect(result).toHaveLength(2);
      expect(result.map((r) => r.id)).toEqual(["NCT01111111", "NCT02222222"]);
    });

    it("extracts ISRCTN IDs", () => {
      const result = extractTrialIds({
        title: "ISRCTN12345678 multi-center trial",
      });
      expect(result).toHaveLength(1);
      expect(result[0].registry).toBe("ISRCTN");
      expect(result[0].id).toBe("ISRCTN12345678");
    });

    it("extracts ACTRN IDs", () => {
      const result = extractTrialIds({
        abstract: "Registered as ACTRN12345678901234",
      });
      expect(result).toHaveLength(1);
      expect(result[0].registry).toBe("ACTRN");
    });

    it("extracts EUCTR IDs", () => {
      const result = extractTrialIds({
        title: "EUCTR2023-000123-45 trial",
      });
      expect(result).toHaveLength(1);
      expect(result[0].registry).toBe("EUCTR");
    });

    it("extracts ChiCTR IDs", () => {
      const result = extractTrialIds({
        abstract: "Registered in ChiCTR123456",
      });
      expect(result).toHaveLength(1);
      expect(result[0].registry).toBe("ChiCTR");
    });

    it("extracts IRCT IDs", () => {
      const result = extractTrialIds({
        title: "IRCT2023010112345N1 study",
      });
      expect(result).toHaveLength(1);
      expect(result[0].registry).toBe("IRCT");
    });

    it("deduplicates identical IDs", () => {
      const result = extractTrialIds({
        title: "NCT01234567 trial",
        abstract: "NCT01234567 was registered...",
      });
      expect(result).toHaveLength(1);
    });

    it("returns empty array for no trial IDs", () => {
      const result = extractTrialIds({
        title: "A general review of dry eye disease",
      });
      expect(result).toHaveLength(0);
    });

    it("handles empty input gracefully", () => {
      const result = extractTrialIds({});
      expect(result).toHaveLength(0);
    });

    it("extracts IDs from keywords", () => {
      const result = extractTrialIds({
        title: "Clinical trial",
        keywords: ["NCT09999999", "dry eye", "cyclosporine"],
      });
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe("NCT09999999");
    });
  });

  describe("hasTrialRegistration", () => {
    it("returns true when trial ID found", () => {
      expect(hasTrialRegistration({ title: "NCT01234567 study" })).toBe(true);
    });

    it("returns false when no trial ID found", () => {
      expect(hasTrialRegistration({ title: "General review" })).toBe(false);
    });
  });

  describe("getPrimaryTrialId", () => {
    it("returns highest confidence ID", () => {
      const result = getPrimaryTrialId({
        title: "NCT01234567 and ISRCTN12345678",
      });
      expect(result).not.toBeNull();
      expect(result!.confidence).toBeGreaterThanOrEqual(0.8);
    });

    it("returns null when no IDs found", () => {
      expect(getPrimaryTrialId({ title: "No trial here" })).toBeNull();
    });
  });
});
