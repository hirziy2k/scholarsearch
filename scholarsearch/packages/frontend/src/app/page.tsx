"use client";

import { useState } from "react";
import { SearchBar } from "../components/SearchBar";
import { ResultList } from "../components/ResultList";
import { RankingPanel } from "../components/RankingPanel";
import { ModeSelector } from "../components/ModeSelector";
import { useSSESearch } from "../hooks/useSSESearch";
import type { SearchMode, RankingWeights } from "@scholarsearch/shared";

const DEFAULT_WEIGHTS: RankingWeights = {
  relevance: 0.25,
  semantic_similarity: 0.20,
  keyword_match: 0.15,
  peer_review: 0.10,
  study_design: 0.10,
  citation_impact: 0.10,
  journal_quality: 0.10,
  recency: 0.10,
  oa_availability: 0.05,
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("discovery");
  const [weights, setWeights] = useState<RankingWeights>(DEFAULT_WEIGHTS);
  const [showRankingPanel, setShowRankingPanel] = useState(false);

  const {
    results,
    isSearching,
    progress,
    error,
    search,
  } = useSSESearch();

  const handleSearch = () => {
    if (!query.trim()) return;
    search({
      raw_query: query,
      mode,
      weights,
      max_results: 100,
    });
  };

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 sm:text-4xl">
          ScholarSearch
        </h1>
        <p className="mt-2 text-lg text-gray-600">
          Transparent academic search with regional clinical elevation
        </p>
      </div>

      {/* Search Interface */}
      <div className="space-y-4">
        <SearchBar
          value={query}
          onChange={setQuery}
          onSearch={handleSearch}
          isSearching={isSearching}
        />

        <div className="flex items-center justify-between">
          <ModeSelector value={mode} onChange={setMode} />

          <button
            onClick={() => setShowRankingPanel(!showRankingPanel)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showRankingPanel ? "Hide Ranking Settings" : "Show Ranking Settings"}
          </button>
        </div>

        {/* Ranking Panel */}
        {showRankingPanel && (
          <RankingPanel weights={weights} onChange={setWeights} />
        )}

        {/* Clinical Context Badge (shown in clinical mode) */}
        {mode === "clinical" && (
          <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2">
            <span className="text-sm text-blue-700">
              📍 Context: Malaysia (Urban/General Adult)
            </span>
            <button className="text-xs text-blue-600 underline hover:text-blue-800">
              Change Region
            </button>
          </div>
        )}

        {/* Progress */}
        {progress.length > 0 && (
          <div className="space-y-2">
            {progress.map((p) => (
              <div
                key={p.source}
                className="flex items-center gap-3 text-sm text-gray-600"
              >
                <span
                  className={`inline-block h-2 w-2 rounded-full ${
                    p.status === "completed"
                      ? "bg-green-500"
                      : p.status === "error"
                        ? "bg-red-500"
                        : "bg-yellow-500 animate-pulse"
                  }`}
                />
                <span className="font-medium">{p.source}</span>
                <span>
                  {p.status === "completed"
                    ? `${p.count ?? 0} results`
                    : p.status === "error"
                      ? "Error"
                      : "Searching..."}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      <ResultList results={results} query={query} />
    </div>
  );
}
