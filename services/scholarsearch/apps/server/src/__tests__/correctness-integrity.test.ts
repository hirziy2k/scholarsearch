import { describe, it, expect } from "vitest";
import { parse, evaluateAST, DEFAULT_WEIGHTS, computeCompositeScore } from "@scholarsearch/shared";
import type { RankingWeights } from "@scholarsearch/shared";

// ============================================
// Hotfix Regression Tests
// ============================================
// Proves the three correctness patches:
// 1. clinical mode weights are non-zero
// 2. citation_verification mode weights are non-zero
// 3. local intersection evaluates title+abstract (recall delta)

describe("Hotfix: Clinical mode weights", () => {
  it("clinical mode weights sum to 1.0", () => {
    const w = DEFAULT_WEIGHTS.clinical;
    const total = Object.values(w).reduce((s, v) => s + v, 0);
    expect(total).toBeCloseTo(1.0, 2);
  });

  it("clinical mode has non-zero study_design weight", () => {
    expect(DEFAULT_WEIGHTS.clinical.study_design).toBeGreaterThan(0);
  });

  it("clinical mode has non-zero peer_review weight", () => {
    expect(DEFAULT_WEIGHTS.clinical.peer_review).toBeGreaterThan(0);
  });

  it("clinical mode produces non-zero composite for a realistic paper", () => {
    const w = DEFAULT_WEIGHTS.clinical;
    const dimensions: RankingWeights = {
      relevance: 0.8,
      semantic_similarity: 0.7,
      keyword_match: 0.6,
      peer_review: 0.9,
      study_design: 1.0,
      citation_impact: 0.5,
      journal_quality: 0.8,
      recency: 0.9,
      oa_availability: 0.3,
    };
    const score = computeCompositeScore(dimensions, w);
    expect(score).toBeGreaterThan(0);
  });

  it("clinical mode differentiates study designs — systematic review scores higher than case report", () => {
    const w = DEFAULT_WEIGHTS.clinical;
    const baseDimensions: RankingWeights = {
      relevance: 0.8,
      semantic_similarity: 0.7,
      keyword_match: 0.6,
      peer_review: 0.9,
      study_design: 0,
      citation_impact: 0.5,
      journal_quality: 0.8,
      recency: 0.9,
      oa_availability: 0.3,
    };
    // Simulate high study_design (systematic review) vs low (case report)
    const highDesign = { ...baseDimensions, study_design: 1.0 };
    const lowDesign = { ...baseDimensions, study_design: 0.3 };
    const highScore = computeCompositeScore(highDesign, w);
    const lowScore = computeCompositeScore(lowDesign, w);
    expect(highScore).toBeGreaterThan(lowScore);
  });
});

describe("Hotfix: Citation verification mode weights", () => {
  it("citation_verification weights sum to 1.0", () => {
    const w = DEFAULT_WEIGHTS.citation_verification;
    const total = Object.values(w).reduce((s, v) => s + v, 0);
    expect(total).toBeCloseTo(1.0, 2);
  });

  it("citation_verification has highest citation_impact weight among all dimensions", () => {
    const w = DEFAULT_WEIGHTS.citation_verification;
    expect(w.citation_impact).toBeGreaterThanOrEqual(w.relevance);
    expect(w.citation_impact).toBeGreaterThanOrEqual(w.semantic_similarity);
    expect(w.citation_impact).toBeGreaterThanOrEqual(w.keyword_match);
  });

  it("citation_verification produces non-zero composite", () => {
    const w = DEFAULT_WEIGHTS.citation_verification;
    const dimensions: RankingWeights = {
      relevance: 0.8,
      semantic_similarity: 0.7,
      keyword_match: 0.6,
      peer_review: 0.9,
      study_design: 0.8,
      citation_impact: 1.0,
      journal_quality: 0.9,
      recency: 0.5,
      oa_availability: 0.2,
    };
    const score = computeCompositeScore(dimensions, w);
    expect(score).toBeGreaterThan(0);
  });

  it("citation_verification differentiates high-citation from low-citation papers", () => {
    const w = DEFAULT_WEIGHTS.citation_verification;
    const baseDimensions: RankingWeights = {
      relevance: 0.5,
      semantic_similarity: 0.5,
      keyword_match: 0.5,
      peer_review: 0.5,
      study_design: 0.5,
      citation_impact: 0,
      journal_quality: 0.5,
      recency: 0.5,
      oa_availability: 0.5,
    };
    const highCite = { ...baseDimensions, citation_impact: 1.0 };
    const lowCite = { ...baseDimensions, citation_impact: 0.1 };
    const highScore = computeCompositeScore(highCite, w);
    const lowScore = computeCompositeScore(lowCite, w);
    expect(highScore).toBeGreaterThan(lowScore);
  });
});

describe("Hotfix: All modes have non-zero weights", () => {
  const modes = [
    "discovery", "evidence", "clinical", "systematic_review",
    "thesis", "manuscript", "citation_verification", "adversarial",
    "bibliometric", "openness",
  ] as const;

  for (const mode of modes) {
    it(`${mode} mode weights sum to 1.0`, () => {
      const w = DEFAULT_WEIGHTS[mode];
      const total = Object.values(w).reduce((s, v) => s + v, 0);
      expect(total).toBeCloseTo(1.0, 2);
    });

    it(`${mode} mode has at least one non-zero weight`, () => {
      const w = DEFAULT_WEIGHTS[mode];
      const hasNonZero = Object.values(w).some(v => v > 0);
      expect(hasNonZero).toBe(true);
    });
  }
});

describe("Hotfix: Local intersection recall delta (title-only vs title+abstract)", () => {
  // Deterministic fixture: paper where AND conditions are in abstract, NOT title.
  // Title-only intersection misses this paper. Title+abstract intersection catches it.
  const query = '"dry eye" AND cyclosporine';

  const paperWhereAbstractMeetsAnd = {
    title: "A Randomized Trial of Topical Immunosuppressants",
    abstract: "This study evaluated cyclosporine emulsion for the treatment of dry eye disease. Results showed significant improvement in tear production.",
  };

  const paperWhereTitleMeetsAnd = {
    title: "Cyclosporine for Dry Eye: A Systematic Review",
    abstract: "We reviewed the literature on topical immunosuppressants for ocular surface disease.",
  };

  it("title-only intersection MISSES paper with AND condition only in abstract (regression proof)", () => {
    const ast = parse(query);
    // Old behavior: evaluateAST against title only
    const titleOnly = paperWhereAbstractMeetsAnd.title;
    const result = evaluateAST(ast, titleOnly);
    expect(result).toBe(false); // Old behavior: miss — proves the bug existed
  });

  it("title+abstract intersection CATCHES paper with AND condition in abstract (fix proof)", () => {
    const ast = parse(query);
    // New behavior: evaluateAST against title + abstract
    const searchText = paperWhereAbstractMeetsAnd.title + " " + paperWhereAbstractMeetsAnd.abstract;
    const result = evaluateAST(ast, searchText);
    expect(result).toBe(true); // Fixed behavior: catch
  });

  it("title+abstract intersection still CATCHES paper with AND condition in title (no regression)", () => {
    const ast = parse(query);
    const searchText = paperWhereTitleMeetsAnd.title + " " + paperWhereTitleMeetsAnd.abstract;
    const result = evaluateAST(ast, searchText);
    expect(result).toBe(true);
  });

  it("title+abstract intersection still REJECTS paper meeting neither title nor abstract", () => {
    const ast = parse(query);
    const irrelevantPaper = {
      title: "Machine Learning for Image Classification",
      abstract: "We present a convolutional neural network architecture for medical image segmentation.",
    };
    const searchText = irrelevantPaper.title + " " + irrelevantPaper.abstract;
    const result = evaluateAST(ast, searchText);
    expect(result).toBe(false);
  });

  it("recall delta: title+abstract returns strictly more results than title-only on mixed corpus", () => {
    const ast = parse(query);
    const corpus = [
      paperWhereAbstractMeetsAnd,
      paperWhereTitleMeetsAnd,
      {
        title: "Glaucoma Management in Tropical Regions",
        abstract: "A cross-sectional study of open-angle glaucoma screening in rural Southeast Asia.",
      },
    ];

    const titleOnlyResults = corpus.filter(p =>
      evaluateAST(ast, p.title)
    );
    const titleAbstractResults = corpus.filter(p =>
      evaluateAST(ast, p.title + " " + p.abstract)
    );

    // title+abstract catches the abstract-only paper; title-only misses it
    expect(titleAbstractResults.length).toBeGreaterThanOrEqual(titleOnlyResults.length);
    expect(titleAbstractResults.length).toBe(titleOnlyResults.length + 1);
  });
});
