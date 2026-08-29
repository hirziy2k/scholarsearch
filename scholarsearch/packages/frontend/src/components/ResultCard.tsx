"use client";

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

interface Paper {
  _source?: string;
  _watermarks?: Watermarks;
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
  };
  return badges[source] ?? source.slice(0, 2).toUpperCase();
}

function getSourceColor(source: string): string {
  const colors: Record<string, string> = {
    openalex: "bg-green-100 text-green-800",
    semantic_scholar: "bg-blue-100 text-blue-800",
    pubmed: "bg-purple-100 text-purple-800",
    crossref: "bg-orange-100 text-orange-800",
  };
  return colors[source] ?? "bg-gray-100 text-gray-800";
}

/**
 * Watermark badge: renders a dashed-border indicator when data is missing.
 */
function WatermarkBadge({ label, missing }: { label: string; missing: boolean }) {
  if (!missing) return null;
  return (
    <span className="inline-flex items-center rounded-full border border-dashed border-gray-300 bg-gray-50 px-2 py-0.5 text-xs text-gray-400">
      {label} unavailable
    </span>
  );
}

export function ResultCard({ paper, index }: ResultCardProps) {
  const title = getTitle(paper);
  const authors = getAuthors(paper);
  const year = getYear(paper);
  const source = getSource(paper);
  const citations = getCitations(paper);
  const oa = isOa(paper);
  const wm = paper._watermarks;

  const doi = paper.DOI ?? paper.doi ?? null;
  const doiUrl = doi ? `https://doi.org/${doi}` : null;

  const citationMissing = wm?.s2_citations || wm?.oa_citations;
  const abstractMissing = wm?.pm_abstract;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
      {/* Badges */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${getSourceColor(source)}`}
        >
          {getSourceBadge(source)}
        </span>

        {oa && (
          <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
            OA
          </span>
        )}

        {/* Citations — show watermark if data is missing */}
        {citationMissing ? (
          <span className="inline-flex items-center rounded-full border border-dashed border-amber-300 bg-amber-50 px-2 py-0.5 text-xs text-amber-500">
            {citations > 0 ? `${citations} cites` : "citations"} · data source degraded
          </span>
        ) : citations > 0 ? (
          <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
            {citations} citations
          </span>
        ) : null}

        {/* Watermark badges for degraded sources */}
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
        <div className="mt-1 text-xs text-gray-400">
          DOI: {doi}
        </div>
      )}

      {/* Abstract — show watermark if missing due to PubMed degradation */}
      {paper.abstract ? (
        <p className="mt-3 text-sm text-gray-600 line-clamp-3">
          {paper.abstract}
        </p>
      ) : abstractMissing ? (
        <div className="mt-3 rounded border border-dashed border-gray-200 bg-gray-50 p-3">
          <p className="text-xs text-gray-400 italic">
            Abstract unavailable — PubMed source degraded
          </p>
        </div>
      ) : null}

      {/* Actions */}
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
        {oa && paper.fullTextUrl && (
          <a
            href={paper.fullTextUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-emerald-600 hover:underline"
          >
            Full Text (PDF)
          </a>
        )}
        {doiUrl && (
          <a
            href={doiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            Publisher
          </a>
        )}
        <button className="text-gray-500 hover:text-gray-700">
          Cite
        </button>
        <button className="text-gray-500 hover:text-gray-700">
          Save
        </button>
        <button className="text-gray-500 hover:text-gray-700">
          Similar
        </button>
      </div>
    </div>
  );
}
