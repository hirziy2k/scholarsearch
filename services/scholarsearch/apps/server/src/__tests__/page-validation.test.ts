import { describe, it, expect } from "vitest";
import { validatePagePayload } from "../utils/page-validation.js";

describe("Page Validation", () => {
  it("validates a normal page with results", () => {
    const results = [
      { title: "Paper 1", DOI: "10.1234/test1" },
      { title: "Paper 2", DOI: "10.1234/test2" },
    ];
    const result = validatePagePayload(results, 1, 2, 2);
    expect(result.valid).toBe(true);
  });

  it("rejects empty first page", () => {
    const result = validatePagePayload([], 1, 50, 10);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain("Empty first page");
  });

  it("allows empty non-first page (final page)", () => {
    const result = validatePagePayload([], 5, 45, 10);
    expect(result.valid).toBe(true);
  });

  it("rejects result missing both title and DOI", () => {
    const results = [
      { authors: ["Author"] }, // No title, no DOI
    ];
    const result = validatePagePayload(results, 1, 1, 1);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain("missing both title and DOI");
  });

  it("accepts result with only DOI", () => {
    const results = [
      { DOI: "10.1234/test" },
    ];
    const result = validatePagePayload(results, 1, 1, 1);
    expect(result.valid).toBe(true);
  });

  it("accepts result with Title field (capital T)", () => {
    const results = [
      { Title: "A paper" },
    ];
    const result = validatePagePayload(results, 1, 1, 1);
    expect(result.valid).toBe(true);
  });

  it("accepts result with lowercase doi", () => {
    const results = [
      { doi: "10.1234/test" },
    ];
    const result = validatePagePayload(results, 1, 1, 1);
    expect(result.valid).toBe(true);
  });

  it("accepts result with externalIds.DOI", () => {
    const results = [
      { externalIds: { DOI: "10.1234/test" } },
    ];
    const result = validatePagePayload(results, 1, 1, 1);
    expect(result.valid).toBe(true);
  });
});
