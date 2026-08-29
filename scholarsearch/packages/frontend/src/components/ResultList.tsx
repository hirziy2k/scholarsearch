"use client";

import { ResultCard } from "./ResultCard";

interface Paper {
  source: string;
  title?: string;
  Title?: string;
  DOI?: string;
  doi?: string;
  authors?: any[];
  authorships?: any[];
  author?: any[];
  year?: number;
  pubYear?: number;
  containerTitle?: string;
  container_title?: string;
  journalName?: string;
  abstract?: string;
  cited_by_count?: number;
  referenceCount?: number;
  citationCount?: number;
  is_oa?: boolean;
  openAccessPdf?: { url: string };
  type?: string;
  publicationType?: string;
}

interface ResultListProps {
  results: Paper[];
  query: string;
}

export function ResultList({ results, query }: ResultListProps) {
  if (results.length === 0) {
    return (
      <div className="py-12 text-center text-gray-500">
        {query
          ? "No results found. Try adjusting your query or filters."
          : "Enter a search query to find academic literature."}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Results ({results.length})
        </h2>
      </div>

      <div className="space-y-4">
        {results.map((paper, index) => (
          <ResultCard key={index} paper={paper} index={index} />
        ))}
      </div>
    </div>
  );
}
