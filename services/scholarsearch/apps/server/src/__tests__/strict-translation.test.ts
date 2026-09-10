import { describe, it, expect } from "vitest";
import { extractNounPhrases, compileStrict, extractExclusions } from "../services/strict-translation.js";
import { parse } from "@scholarsearch/shared";

describe("Strict Translation Compiler", () => {
  describe("extractNounPhrases", () => {
    it("extracts single terms", () => {
      const ast = parse("dry eye");
      const phrases = extractNounPhrases(ast);
      expect(phrases.length).toBeGreaterThanOrEqual(1);
      expect(phrases.some((p) => p.text.toLowerCase().includes("dry"))).toBe(true);
    });

    it("extracts quoted phrases", () => {
      const ast = parse('"dry eye disease"');
      const phrases = extractNounPhrases(ast);
      expect(phrases).toHaveLength(1);
      expect(phrases[0].text).toBe("dry eye disease");
      expect(phrases[0].isPhrase).toBe(true);
    });

    it("extracts from AND expressions", () => {
      const ast = parse('"dry eye" AND cyclosporine');
      const phrases = extractNounPhrases(ast);
      expect(phrases.length).toBeGreaterThanOrEqual(2);
    });

    it("extracts from OR expressions", () => {
      const ast = parse('"dry eye" OR "keratoconjunctivitis sicca"');
      const phrases = extractNounPhrases(ast);
      expect(phrases.length).toBeGreaterThanOrEqual(2);
    });

    it("extracts from nested expressions", () => {
      const ast = parse('("dry eye" OR "DES") AND (cyclosporine OR restasis)');
      const phrases = extractNounPhrases(ast);
      expect(phrases.length).toBeGreaterThanOrEqual(4);
    });

    it("extracts NOT operand for exclusion", () => {
      const ast = parse('"dry eye" AND treatment AND NOT animals');
      const phrases = extractNounPhrases(ast);
      expect(phrases.some((p) => p.text.toLowerCase().includes("animal"))).toBe(true);
    });
  });

  describe("compileStrict", () => {
    it("produces parallel queries for Crossref", () => {
      const ast = parse('"dry eye" AND cyclosporine');
      const queries = compileStrict(ast, "crossref");
      expect(queries.length).toBeGreaterThanOrEqual(2);
      // Each query should be a simple phrase or term (no Boolean operators)
      for (const q of queries) {
        expect(q.query).not.toMatch(/\bAND\b/);
        expect(q.query).not.toMatch(/\bOR\b/);
      }
    });

    it("produces parallel queries for Semantic Scholar", () => {
      const ast = parse('"dry eye" OR "keratoconjunctivitis"');
      const queries = compileStrict(ast, "semantic_scholar");
      expect(queries.length).toBeGreaterThanOrEqual(2);
    });

    it("quotes multi-word phrases", () => {
      const ast = parse('"dry eye disease"');
      const queries = compileStrict(ast, "crossref");
      expect(queries).toHaveLength(1);
      expect(queries[0].query).toBe('"dry eye disease"');
    });

    it("deduplicates noun phrases", () => {
      const ast = parse('"dry eye" AND "dry eye"');
      const queries = compileStrict(ast, "crossref");
      // Should be deduplicated
      const uniqueQueries = new Set(queries.map((q) => q.query));
      expect(uniqueQueries.size).toBe(queries.length);
    });
  });

  describe("extractExclusions", () => {
    it("extracts NOT operands", () => {
      const ast = parse('"dry eye" AND NOT animals');
      const exclusions = extractExclusions(ast);
      expect(exclusions).toContain("animals");
    });

    it("returns empty array for no NOT", () => {
      const ast = parse('"dry eye" AND treatment');
      const exclusions = extractExclusions(ast);
      expect(exclusions).toHaveLength(0);
    });

    it("extracts nested NOT operands", () => {
      const ast = parse('("dry eye" OR "DES") AND NOT animals AND NOT mice');
      const exclusions = extractExclusions(ast);
      expect(exclusions.length).toBeGreaterThanOrEqual(2);
    });
  });
});
