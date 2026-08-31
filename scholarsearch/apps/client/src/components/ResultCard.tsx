"use client";

import { useState, useCallback, useRef, useEffect } from "react";

// Singleton Web Worker — shared across all ResultCard instances
let workerInstance: Worker | null = null;
function getWorker(): Worker {
  if (!workerInstance) {
    // Create worker from inline blob to avoid import.meta.url CommonJS issues
    const workerCode = `
      ${getWorkerInlineCode()}
    `;
    const blob = new Blob([workerCode], { type: "application/javascript" });
    workerInstance = new Worker(URL.createObjectURL(blob));
  }
  return workerInstance;
}

// Inline worker code as a string (avoids module resolution issues)
function getWorkerInlineCode(): string {
  return `
    function levenshtein(a, b) {
      if (a.length === 0) return b.length;
      if (b.length === 0) return a.length;
      const matrix = [];
      for (let i = 0; i <= b.length; i++) matrix[i] = [i];
      for (let j = 0; j <= a.length; j++) matrix[0][j] = j;
      for (let i = 1; i <= b.length; i++) {
        for (let j = 1; j <= a.length; j++) {
          const cost = b.charAt(i - 1) === a.charAt(j - 1) ? 0 : 1;
          matrix[i][j] = Math.min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + cost);
        }
      }
      return matrix[b.length][a.length];
    }
    function levenshteinSimilarity(a, b) {
      const maxLen = Math.max(a.length, b.length);
      if (maxLen === 0) return 1;
      return 1 - levenshtein(a, b) / maxLen;
    }
    function findFuzzyAnchor(abstract, claim, threshold) {
      if (!abstract || !claim) return null;
      const claimLen = claim.length;
      const abstractLower = abstract.toLowerCase();
      const claimLower = claim.toLowerCase();
      const exactIndex = abstractLower.indexOf(claimLower);
      if (exactIndex !== -1) return { start: exactIndex, end: exactIndex + claimLen, similarity: 1 };
      const windowStep = Math.max(1, Math.floor(claimLen / 4));
      let bestMatch = null;
      for (let i = 0; i <= abstract.length - claimLen; i += windowStep) {
        const window = abstractLower.substring(i, i + claimLen);
        const similarity = levenshteinSimilarity(claimLower, window);
        if (similarity >= (threshold || 0.7)) {
          const expandRange = Math.floor(claimLen * 0.2);
          const start = Math.max(0, i - expandRange);
          const end = Math.min(abstract.length, i + claimLen + expandRange);
          for (let j = start; j <= i; j++) {
            for (let k = i + claimLen; k <= end; k++) {
              const candidate = abstractLower.substring(j, k);
              const sim = levenshteinSimilarity(claimLower, candidate);
              if (sim > (bestMatch ? bestMatch.similarity : 0)) {
                bestMatch = { start: j, end: k, similarity: sim };
              }
            }
          }
          if (!bestMatch) bestMatch = { start: i, end: i + claimLen, similarity };
        }
      }
      return bestMatch;
    }
    const cancelled = new Set();
    self.onmessage = function(e) {
      const { type, paperId, abstract, claims } = e.data;
      if (type === "cancel") { cancelled.add(paperId); return; }
      if (type === "resolve") {
        if (cancelled.has(paperId)) { cancelled.delete(paperId); return; }
        const anchors = [];
        for (const claim of claims) {
          if (cancelled.has(paperId)) { cancelled.delete(paperId); return; }
          const match = findFuzzyAnchor(abstract, claim, 0.7);
          anchors.push(match ? { claim, start: match.start, end: match.end } : { claim, start: -1, end: -1 });
        }
        self.postMessage({ type: "resolved", paperId, anchors });
      }
    };
  `;
}

// Global map to track pending resolve callbacks per paperId
const pendingResolves = new Map<string, Array<{ claim: string; start: number; end: number }>>();

// Set up worker message handler once
let workerHandlerAttached = false;
function attachWorkerHandler() {
  if (workerHandlerAttached) return;
  workerHandlerAttached = true;
  getWorker().onmessage = (e) => {
    if (e.data.type === "resolved") {
      const { paperId, anchors } = e.data;
      pendingResolves.delete(paperId);
      // Dispatch custom event for cards to consume
      window.dispatchEvent(
        new CustomEvent("anchor-resolved", { detail: { paperId, anchors } }),
      );
    }
  };
}

interface Watermarks {
  s2_citations?: boolean;
  s2_embeddings?: boolean;
  s2_influential?: boolean;
  oa_concepts?: boolean;
  oa_institutions?: boolean;
  oa_citations?: boolean;
  cr_references?: boolean;
  cr_license?: boolean;
  pm_mesh?: boolean;
  pm_abstract?: boolean;
}

interface TierClassification {
  peerReviewTier: number;
  greyLiteratureTier?: number | null;
  documentType?: string;
  tierSource?: string;
  confidence?: number;
}

interface VerifiableEntity {
  entity: string;
  type: "intervention" | "population" | "outcome" | "study_design" | "institution";
  confidence: number;
  sourceSentence: string;
}

interface Paper {
  _source?: string;
  _watermarks?: Watermarks;
  _tierClassification?: TierClassification;
  _degradedPrecision?: boolean;
  source?: string;
  title?: string | string[];
  Title?: string;
  DOI?: string;
  doi?: string;
  authors?: any[];
  authorships?: any[];
  author?: any[];
  year?: number;
  pubYear?: number;
  journal?: string;
  containerTitle?: string;
  container_title?: string;
  journalName?: string;
  abstract?: string;
  citations?: number;
  cited_by_count?: number;
  referenceCount?: number;
  citationCount?: number;
  isOa?: boolean;
  is_oa?: boolean;
  fullTextUrl?: string;
  openAccessPdf?: { url: string };
  type?: string;
  publicationType?: string;
}

interface ResultCardProps {
  paper: Paper;
  index: number;
  onBookmark?: (paper: Paper) => void;
  isBookmarked?: boolean;
  isVisible?: boolean;
  registerCard?: (ref: HTMLDivElement | null, paperId: string) => void;
}

function getTitle(paper: Paper): string {
  const t = paper.title;
  if (Array.isArray(t) && t.length > 0) return t[0]!;
  if (typeof t === "string") return t;
  return paper.Title ?? "Untitled";
}

function getAuthors(paper: Paper): string {
  const authors = paper.authors ?? paper.authorships ?? paper.author ?? [];
  if (!Array.isArray(authors) || authors.length === 0) return "Unknown authors";

  const names = authors.slice(0, 3).map((a: any) => {
    if (typeof a === "string") return a;
    return a.name ?? a.Name ?? a.display_name ?? `${a.given ?? ""} ${a.family ?? ""}`.trim();
  });

  const result = names.join(", ");
  return authors.length > 3 ? `${result} et al.` : result;
}

function getYear(paper: Paper): number | null {
  if (paper.year) return paper.year;
  if (paper.pubYear) return paper.pubYear;
  return null;
}

function getSource(paper: Paper): string {
  return paper._source ?? paper.source ?? "unknown";
}

function getCitations(paper: Paper): number {
  return paper.citations ?? paper.cited_by_count ?? paper.citationCount ?? 0;
}

function isOa(paper: Paper): boolean {
  if (paper.isOa !== undefined) return paper.isOa;
  if (paper.is_oa !== undefined) return paper.is_oa;
  if (paper.fullTextUrl || paper.openAccessPdf) return true;
  return false;
}

function getSourceBadge(source: string): string {
  const badges: Record<string, string> = {
    openalex: "OA",
    semantic_scholar: "S2",
    pubmed: "PM",
    crossref: "CR",
    core: "CO",
    eric: "ER",
    doaj: "DJ",
  };
  return badges[source] ?? source.slice(0, 2).toUpperCase();
}

function getSourceColor(source: string): string {
  return "bg-[#E8E8E6] text-[#1A1A1A]";
}

function WatermarkBadge({ label, missing }: { label: string; missing: boolean }) {
  if (!missing) return null;
  return (
    <span className="inline-flex items-center rounded-full border border-dashed border-gray-300 bg-gray-50 px-2 py-0.5 text-xs text-gray-400">
      {label} unavailable
    </span>
  );
}

const PEER_REVIEW_LABELS: Record<number, string> = {
  1: "Systematic Review",
  2: "Meta-Analysis",
  3: "RCT",
  4: "Observational",
  5: "Case Series",
  6: "Unclassified",
};

const PEER_REVIEW_COLORS: Record<number, string> = {
  1: "bg-[#E8E8E6] text-[#1A1A1A] font-medium",
  2: "bg-[#E8E8E6] text-[#1A1A1A] font-medium",
  3: "bg-[#E8E8E6] text-[#1A1A1A]",
  4: "bg-[#E8E8E6] text-[#3D3D3D]",
  5: "bg-[#F0F0EE] text-[#6B6B6B]",
  6: "bg-[#F5F5F3] text-[#9A9A9A]",
};

const GREY_LIT_LABELS: Record<number, string> = {
  1: "Cochrane Plain Language",
  2: "Clinical Guideline",
  3: "Govt/Policy Report",
  4: "Thesis/Dissertation",
  5: "Preprint",
  6: "Conference Paper",
  7: "Technical Report",
  8: "Patent",
  9: "Newsletter",
  10: "Blog/Commentary",
};

const GREY_LIT_COLORS: Record<number, string> = {
  1: "bg-[#E8E8E6] text-[#1A1A1A]",
  2: "bg-[#E8E8E6] text-[#1A1A1A]",
  3: "bg-[#E8E8E6] text-[#3D3D3D]",
  4: "bg-[#F0F0EE] text-[#3D3D3D]",
  5: "bg-[#F0F0EE] text-[#6B6B6B]",
  6: "bg-[#F0F0EE] text-[#6B6B6B]",
  7: "bg-[#F0F0EE] text-[#6B6B6B]",
  8: "bg-[#F5F5F3] text-[#6B6B6B]",
  9: "bg-[#F5F5F3] text-[#6B6B6B]",
  10: "bg-[#F5F5F3] text-[#9A9A9A]",
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  intervention: "intervention",
  population: "population",
  outcome: "outcome",
  study_design: "design",
  institution: "institution",
};

export function ResultCard({ paper, index, onBookmark, isBookmarked, isVisible = true, registerCard }: ResultCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const paperId = paper.DOI ?? paper.doi ?? `${paper.title}-${paper.source}`;

  const title = getTitle(paper);
  const authors = getAuthors(paper);
  const year = getYear(paper);
  const source = getSource(paper);
  const citations = getCitations(paper);
  const oa = isOa(paper);
  const wm = paper._watermarks;
  const tc = paper._tierClassification;

  const doi = paper.DOI ?? paper.doi ?? null;
  const doiUrl = doi ? `https://doi.org/${doi}` : null;

  const citationMissing = wm?.s2_citations || wm?.oa_citations;
  const abstractMissing = wm?.pm_abstract;

  // Progressive Abstract Loading state
  const [expanded, setExpanded] = useState(false);
  const [abstract, setAbstract] = useState(paper.abstract ?? null);
  const [microSummary, setMicroSummary] = useState<string | null>(null);
  const [microSummaryAnchors, setMicroSummaryAnchors] = useState<any>(null);
  const [loadingAbstract, setLoadingAbstract] = useState(false);
  const [hoveredClaim, setHoveredClaim] = useState<string | null>(null);

  // Web Worker resolved anchors
  const [resolvedAnchors, setResolvedAnchors] = useState<Array<{ claim: string; start: number; end: number }> | null>(null);
  const [loadingAnchors, setLoadingAnchors] = useState(false);

  // Confidence Gradient
  const precisionOpacity = paper._degradedPrecision ? "opacity-75" : "opacity-100";

  // Register with singleton observer
  const cardRefCallback = useCallback(
    (node: HTMLDivElement | null) => {
      (cardRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
      registerCard?.(node, paperId);
    },
    [registerCard, paperId],
  );

  // Attach worker handler once
  useEffect(() => {
    attachWorkerHandler();
  }, []);

  // Listen for worker-resolved anchors
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail.paperId === paperId) {
        setResolvedAnchors(detail.anchors);
        setLoadingAnchors(false);
      }
    };
    window.addEventListener("anchor-resolved", handler);
    return () => window.removeEventListener("anchor-resolved", handler);
  }, [paperId]);

  // Dispatch to worker when visible and has anchors to resolve
  useEffect(() => {
    if (isVisible && microSummaryAnchors && !resolvedAnchors && !loadingAnchors) {
      const claims = ["context", "method", "outcome"]
        .map((key) => microSummaryAnchors[key]?.claim)
        .filter(Boolean);

      if (claims.length > 0 && abstract) {
        setLoadingAnchors(true);
        getWorker().postMessage({
          type: "resolve",
          paperId,
          abstract,
          claims,
        });
      }
    }

    if (!isVisible && loadingAnchors) {
      getWorker().postMessage({ type: "cancel", paperId });
      setLoadingAnchors(false);
    }
  }, [isVisible, microSummaryAnchors, resolvedAnchors, loadingAnchors, paperId, abstract]);

  const fetchAbstract = useCallback(async () => {
    if ((abstract && microSummary) || loadingAbstract || !doi) return;
    setLoadingAbstract(true);
    try {
      const res = await fetch(`/api/paper/abstract?doi=${encodeURIComponent(doi)}`);
      const data = await res.json();
      if (data.abstract) setAbstract(data.abstract);
      if (data.microSummary) setMicroSummary(data.microSummary);
      if (data.microSummaryAnchors) setMicroSummaryAnchors(data.microSummaryAnchors);
    } catch {
      // Silently fail
    } finally {
      setLoadingAbstract(false);
    }
  }, [doi, abstract, microSummary, loadingAbstract]);

  const handleExpand = async () => {
    setExpanded(!expanded);
    if (!expanded && !abstract && doi) {
      await fetchAbstract();
    }
  };

  // Merge LLM anchors with worker-resolved anchors
  const getMergedAnchors = () => {
    if (!microSummaryAnchors) return null;
    if (!resolvedAnchors) return microSummaryAnchors;

    const merged = { ...microSummaryAnchors };
    for (const resolved of resolvedAnchors) {
      const key = ["context", "method", "outcome"].find(
        (k) => microSummaryAnchors[k]?.claim === resolved.claim,
      );
      if (key && resolved.start !== -1) {
        merged[key] = {
          ...merged[key],
          start: resolved.start,
          end: resolved.end,
          anchor: abstract?.slice(resolved.start, resolved.end) ?? merged[key].anchor,
        };
      }
    }
    return merged;
  };

  const getHighlightedAbstract = () => {
    const anchors = getMergedAnchors();
    if (!abstract || !hoveredClaim || !anchors) return null;

    const anchor = anchors[hoveredClaim];
    if (!anchor?.anchor || anchor.start === -1) return null;

    const start = anchor.start;
    const end = anchor.end;
    if (start < 0 || end > abstract.length) return null;

    return (
      <>
        {abstract.slice(0, start)}
        <span className="source-highlight active">{abstract.slice(start, end)}</span>
        {abstract.slice(end)}
      </>
    );
  };

  const mergedAnchors = getMergedAnchors();
  const verifiableEntities: VerifiableEntity[] = mergedAnchors?.verifiableEntities ?? [];

  // Entity graph layout — extract entities by type
  const interventionEntity = verifiableEntities.find((e) => e.type === "intervention");
  const outcomeEntity = verifiableEntities.find((e) => e.type === "outcome");
  const populationEntity = verifiableEntities.find((e) => e.type === "population");
  const institutionEntity = verifiableEntities.find((e) => e.type === "institution");

  return (
    <div
      ref={cardRefCallback}
      data-paper-id={paperId}
      className={`rounded-lg border border-[#E8E8E6] bg-white p-5 shadow-sm hover:shadow-md transition-shadow ${precisionOpacity}`}
    >
      {/* Badges */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${getSourceColor(source)}`}
        >
          {getSourceBadge(source)}
        </span>

        {oa && (
          <span className="inline-flex items-center rounded-full bg-[#E8E8E6] px-2 py-0.5 text-xs font-medium text-[#1A1A1A]">
            OA
          </span>
        )}

        {tc && tc.peerReviewTier && tc.peerReviewTier <= 4 && (
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${PEER_REVIEW_COLORS[tc.peerReviewTier] ?? "bg-[#F0F0EE] text-[#6B6B6B]"}`}>
            {PEER_REVIEW_LABELS[tc.peerReviewTier] ?? `PR:${tc.peerReviewTier}`}
          </span>
        )}

        {tc && tc.greyLiteratureTier && (
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${GREY_LIT_COLORS[tc.greyLiteratureTier] ?? "bg-[#F0F0EE] text-[#6B6B6B]"}`}>
            {GREY_LIT_LABELS[tc.greyLiteratureTier] ?? `GL:${tc.greyLiteratureTier}`}
          </span>
        )}

        {citationMissing ? (
          <span className="inline-flex items-center rounded-full border border-dashed border-[#9A9A9A] bg-[#F5F5F3] px-2 py-0.5 text-xs text-[#6B6B6B]">
            {citations > 0 ? `${citations} cites` : "citations"} · degraded
          </span>
        ) : citations > 0 ? (
          <span className="inline-flex items-center rounded-full bg-[#E8E8E6] px-2 py-0.5 text-xs font-medium text-[#1A1A1A]">
            {citations} cites
          </span>
        ) : null}

        <WatermarkBadge label="S2 embeddings" missing={!!wm?.s2_embeddings} />
        <WatermarkBadge label="MeSH terms" missing={!!wm?.pm_mesh} />
        <WatermarkBadge label="References" missing={!!wm?.cr_references} />
        <WatermarkBadge label="License" missing={!!wm?.cr_license} />
      </div>

      {/* Title */}
      <h3 className="text-base font-semibold text-gray-900 leading-tight">
        {doiUrl ? (
          <a
            href={doiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-blue-600 hover:underline"
          >
            {title}
          </a>
        ) : (
          title
        )}
      </h3>

      {/* Authors and Journal */}
      <div className="mt-1.5 text-sm text-gray-600">
        <span>{authors}</span>
        {year && (
          <>
            {" · "}
            <span>{year}</span>
          </>
        )}
      </div>

      {/* DOI */}
      {doi && (
        <div className="mt-1 text-xs text-[#9A9A9A] font-mono">
          {doi}
        </div>
      )}

      {/* Abstract — tick-data format micro-summary with hover-to-audit */}
      {(abstract || abstractMissing || doi) && (
        <div className="mt-3">
          {expanded && loadingAbstract ? (
            <div className="flex items-center gap-2 text-xs text-[#9A9A9A]">
              <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-[#E8E8E6] border-t-[#1A1A1A]" />
              summarizing...
            </div>
          ) : expanded && mergedAnchors && mergedAnchors.context?.claim ? (
            <div className="tick-data rounded border border-[#E8E8E6] bg-[#FAFAF8] p-3">
              <div className="space-y-1">
                {(["context", "method", "outcome"] as const).map((key) => (
                  <div
                    key={key}
                    className="cursor-default"
                    onMouseEnter={() => setHoveredClaim(key)}
                    onMouseLeave={() => setHoveredClaim(null)}
                  >
                    <span className="text-[#9A9A9A] text-xs uppercase tracking-wider">{key}</span>
                    <span className="text-[#3D3D3D] ml-2">{mergedAnchors[key]?.claim}</span>
                  </div>
                ))}
              </div>

              {/* Verifiable Entities — HTML/CSS Flex-Graph */}
              {verifiableEntities.length >= 2 && (
                <div className="mt-2 pt-2 border-t border-[#E8E8E6]" role="img" aria-label="Clinical Relationship Graph">
                  <div className="text-[#9A9A9A] text-xs uppercase tracking-wider mb-2">relationships</div>
                  <div className="entity-graph">
                    {/* Top row: Intervention → Outcome */}
                    <div className="entity-row">
                      {interventionEntity && (
                        <span className="entity-node entity-intervention" title={interventionEntity.sourceSentence}>
                          <span className="entity-type">intervention</span>
                          <span className="entity-name" title={interventionEntity.entity}>{interventionEntity.entity}</span>
                        </span>
                      )}
                      {interventionEntity && outcomeEntity && (
                        <span className="entity-arrow">→</span>
                      )}
                      {outcomeEntity && (
                        <span className="entity-node entity-outcome" title={outcomeEntity.sourceSentence}>
                          <span className="entity-type">outcome</span>
                          <span className="entity-name" title={outcomeEntity.entity}>{outcomeEntity.entity}</span>
                        </span>
                      )}
                    </div>

                    {/* Connector */}
                    {interventionEntity && populationEntity && (
                      <div className="entity-row">
                        <span className="entity-connector">│</span>
                      </div>
                    )}

                    {/* Bottom row: Population + Institution */}
                    <div className="entity-row">
                      {populationEntity && (
                        <span className="entity-node entity-population" title={populationEntity.sourceSentence}>
                          <span className="entity-type">population</span>
                          <span className="entity-name" title={populationEntity.entity}>{populationEntity.entity}</span>
                        </span>
                      )}
                      {institutionEntity && (
                        <span className="entity-node entity-institution ml-auto" title={institutionEntity.sourceSentence}>
                          <span className="entity-type">institution</span>
                          <span className="entity-name" title={institutionEntity.entity}>{institutionEntity.entity}</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Fallback: flat badge row for <2 entities */}
              {verifiableEntities.length > 0 && verifiableEntities.length < 2 && (
                <div className="mt-2 pt-2 border-t border-[#E8E8E6]">
                  <div className="text-[#9A9A9A] text-xs uppercase tracking-wider mb-1">entities</div>
                  <div className="flex flex-wrap gap-1.5">
                    {verifiableEntities.map((entity, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center rounded-full bg-[#F0F0EE] px-2 py-0.5 text-xs text-[#3D3D3D]"
                        title={entity.sourceSentence}
                      >
                        <span className="font-mono text-[#9A9A9A] mr-1">{ENTITY_TYPE_LABELS[entity.type] ?? entity.type}</span>
                        {entity.entity}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : expanded && microSummary ? (
            <div className="tick-data rounded border border-[#E8E8E6] bg-[#FAFAF8] p-3">
              <div className="whitespace-pre-line text-[#3D3D3D]">{microSummary}</div>
            </div>
          ) : expanded && abstract && getHighlightedAbstract() ? (
            <p className="text-sm text-[#3D3D3D] leading-relaxed">{getHighlightedAbstract()}</p>
          ) : expanded && abstract ? (
            <p className="text-sm text-[#3D3D3D] leading-relaxed">{abstract}</p>
          ) : expanded && abstractMissing ? (
            <div className="rounded border border-dashed border-[#E8E8E6] bg-[#FAFAF8] p-3">
              <p className="text-xs text-[#9A9A9A] italic">
                abstract unavailable — source degraded
              </p>
            </div>
          ) : null}
          <button
            onClick={handleExpand}
            className="mt-1 text-xs text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors"
          >
            {expanded ? "hide" : "summary"}
          </button>
        </div>
      )}

      {/* Actions */}
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
        {oa && paper.fullTextUrl && (
          <a
            href={paper.fullTextUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#1A1A1A] hover:underline"
          >
            PDF
          </a>
        )}
        {doiUrl && (
          <a
            href={doiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#1A1A1A] hover:underline"
          >
            publisher
          </a>
        )}
        <button className="text-[#9A9A9A] hover:text-[#1A1A1A] transition-colors">
          cite
        </button>
        <button
          onClick={() => onBookmark?.(paper)}
          className={`transition-colors ${
            isBookmarked
              ? "text-[#1A1A1A] font-medium"
              : "text-[#9A9A9A] hover:text-[#1A1A1A]"
          }`}
        >
          {isBookmarked ? "saved" : "save"}
        </button>
        <button className="text-[#9A9A9A] hover:text-[#1A1A1A] transition-colors">
          similar
        </button>
      </div>
    </div>
  );
}
