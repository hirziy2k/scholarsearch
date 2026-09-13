"use client";

import { useState, useCallback } from "react";
import { SearchBar } from "../components/SearchBar";
import { ResultList } from "../components/ResultList";
import { RankingPanel } from "../components/RankingPanel";
import { ModeSelector } from "../components/ModeSelector";
import { CommandPalette } from "../components/CommandPalette";
import { useSSESearch } from "../hooks/useSSESearch";
import { useHotkeys } from "../hooks/useHotkeys";
import type { SearchMode, RankingWeights } from "@scholarsearch/shared";

const DEFAULT_WEIGHTS: RankingWeights = {
  relevance: 0.30,
  semantic_similarity: 0.20,
  keyword_match: 0.15,
  peer_review: 0.15,
  study_design: 0.10,
  citation_impact: 0.05,
  journal_quality: 0.05,
  recency: 0.05,
  oa_availability: 0.05,
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("discovery");
  const [weights, setWeights] = useState<RankingWeights>(DEFAULT_WEIGHTS);
  const [showRankingPanel, setShowRankingPanel] = useState(false);
  const [showGapAuditTrail, setShowGapAuditTrail] = useState(false);

  const {
    results,
    isSearching,
    progress,
    error,
    search,
    gapAnalysis,
    exportSession,
    addBookmark,
    isBookmarked,
    incognitoMode,
    toggleIncognito,
    clearSession,
    loaded,
    exportManifest,
    importManifest,
    discoveryFeed,
    checkDiscovery,
    mergeDiscoveryFeed,
    dismissDiscoveryFeed,
    excludePaper,
    promotePaper,
  } = useSSESearch();

  const [expandedPaperId, setExpandedPaperId] = useState<string | null>(null);

  const handleToggleExpand = useCallback((paperId: string) => {
    setExpandedPaperId((prev) => prev === paperId ? null : paperId);
  }, []);

  const { activeCardId, activeIndexRef, isPaletteOpen, setIsPaletteOpen } = useHotkeys(results, {
    onPromote: promotePaper,
    onExclude: (paper: any, reason: string) => excludePaper(paper, reason, "ta"),
    onToggleExpand: handleToggleExpand,
  });

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
        <h1 className="text-3xl font-semibold text-[#1A1A1A] tracking-tight sm:text-4xl">
          ScholarSearch
        </h1>
        <p className="mt-2 text-lg text-[#6B6B6B]">
          transparent academic search
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
            className="text-sm text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors"
          >
            {showRankingPanel ? "hide settings" : "ranking settings"}
          </button>
        </div>

        {showRankingPanel && (
          <RankingPanel weights={weights} onChange={setWeights} />
        )}

        {mode === "clinical" && (
          <div className="flex items-center gap-2 rounded-lg border border-[#E8E8E6] bg-[#FAFAF8] px-4 py-2">
            <span className="text-sm text-[#3D3D3D]">
              context: Malaysia (Urban/General Adult)
            </span>
            <button className="text-xs text-[#6B6B6B] underline hover:text-[#1A1A1A]">
              change
            </button>
          </div>
        )}

        {/* Progress */}
        {progress.length > 0 && (
          <div className="space-y-2">
            {progress.map((p) => (
              <div
                key={p.source}
                className="flex items-center gap-3 text-sm text-[#6B6B6B]"
              >
                <span
                  className={`inline-block h-2 w-2 rounded-full ${
                    p.status === "completed"
                      ? "bg-[#1A1A1A]"
                      : p.status === "error"
                        ? "bg-[#9A9A9A]"
                        : "bg-[#E8E8E6] animate-pulse"
                  }`}
                />
                <span className="font-medium text-[#1A1A1A]">{p.source}</span>
                <span>
                  {p.status === "completed"
                    ? `${p.count ?? 0}`
                    : p.status === "error"
                      ? "error"
                      : "..."}
                </span>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-[#E8E8E6] bg-[#FAFAF8] p-4 text-sm text-[#1A1A1A]">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      <ResultList
        results={results}
        query={query}
        onBookmark={addBookmark}
        isBookmarked={isBookmarked}
        activeIndexRef={activeIndexRef}
      />

      {/* Forward-Only Discovery Feed */}
      {discoveryFeed.length > 0 && (
        <div className="gap-banner rounded-lg border p-4">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-[#1A1A1A]">
                new evidence since last session
              </h3>
              <p className="mt-1 text-sm text-[#6B6B6B]">
                {discoveryFeed.length} new papers found since your last search
              </p>
              <div className="mt-2 flex gap-2">
                <button
                  onClick={mergeDiscoveryFeed}
                  className="text-xs font-mono text-[#1A1A1A] hover:underline"
                >
                  merge into results
                </button>
                <button
                  onClick={dismissDiscoveryFeed}
                  className="text-xs font-mono text-[#9A9A9A] hover:text-[#1A1A1A]"
                >
                  dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Research Gap Warning Banner */}
      {gapAnalysis?.hasGaps && gapAnalysis.gaps.length > 0 && (
        <div className={`rounded-lg border p-4 ${
          gapAnalysis.gaps.some((g: any) => g.severity === "critical")
            ? "gap-banner"
            : "border-[#E8E8E6] bg-[#FAFAF8]"
        }`}>
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <button
                onClick={() => setShowGapAuditTrail(!showGapAuditTrail)}
                className={`text-left w-full ${
                  gapAnalysis.gaps.some((g: any) => g.severity === "critical")
                    ? "text-[#1A1A1A]"
                    : "text-[#3D3D3D]"
                }`}
              >
                <h3 className="text-sm font-semibold">
                  {gapAnalysis.gaps.some((g: any) => g.severity === "critical")
                    ? "RESEARCH GAP"
                    : "evidence note"}
                  <span className="ml-2 text-[#9A9A9A] font-normal">
                    {showGapAuditTrail ? "▾" : "▸"}
                  </span>
                </h3>
              </button>
              <p className={`mt-1 text-sm ${
                gapAnalysis.gaps.some((g: any) => g.severity === "critical")
                  ? "text-[#1A1A1A]"
                  : "text-[#6B6B6B]"
              }`}>
                {gapAnalysis.bannerText}
              </p>
              <div className="mt-2 space-y-1">
                {gapAnalysis.gaps.map((gap: any, i: number) => (
                  <div key={i} className={`text-xs ${
                    gap.severity === "critical" ? "text-[#1A1A1A]" : "text-[#6B6B6B]"
                  }`}>
                    <span className="font-mono font-medium">{gap.missing}</span> — {gap.suggestion}
                  </div>
                ))}
              </div>

              {showGapAuditTrail && gapAnalysis.globalAuditTrail && (
                <div className="mt-4 rounded border border-[#E8E8E6] bg-[#FAFAF8] p-3 space-y-3">
                  <h4 className="text-xs font-semibold text-[#1A1A1A] uppercase tracking-wider">
                    audit trail
                  </h4>
                  
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-[#9A9A9A] block mb-1">query parameters</span>
                      <ul className="space-y-0.5">
                        {gapAnalysis.globalAuditTrail.queryParameters.map((qp: string, i: number) => (
                          <li key={i} className="font-mono text-[#3D3D3D]">"{qp}"</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <span className="text-[#9A9A9A] block mb-1">sources queried</span>
                      <ul className="space-y-0.5">
                        {gapAnalysis.globalAuditTrail.sourcesQueried.map((src: string, i: number) => (
                          <li key={i} className="font-mono text-[#3D3D3D]">{src}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <span className="text-[#9A9A9A] block mb-1">taxonomy nodes</span>
                      <ul className="space-y-0.5">
                        {gapAnalysis.globalAuditTrail.taxonomyNodesChecked.slice(0, 10).map((node: string, i: number) => (
                          <li key={i} className="font-mono text-[#3D3D3D]">{node}</li>
                        ))}
                        {gapAnalysis.globalAuditTrail.taxonomyNodesChecked.length > 10 && (
                          <li className="text-[#9A9A9A]">+{gapAnalysis.globalAuditTrail.taxonomyNodesChecked.length - 10} more</li>
                        )}
                      </ul>
                    </div>
                    <div>
                      <span className="text-[#9A9A9A] block mb-1">tier distribution</span>
                      <ul className="space-y-0.5">
                        {Object.entries(gapAnalysis.globalAuditTrail.tierDistribution).map(([tier, count]) => (
                          <li key={tier} className="font-mono text-[#3D3D3D]">
                            L{tier}: {String(count)} papers
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="text-xs text-[#9A9A9A] border-t border-[#E8E8E6] pt-2">
                    analyzed {gapAnalysis.globalAuditTrail.totalResultsAnalyzed} results at {gapAnalysis.globalAuditTrail.analyzedAt}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Session Controls — Export, Incognito, Clear */}
      {results.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[#E8E8E6] bg-[#FAFAF8] px-4 py-3">
          <span className="text-xs text-[#9A9A9A]">export</span>
          <button
            onClick={() => exportSession("json")}
            className="text-xs font-mono text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors"
          >
            JSON
          </button>
          <span className="text-[#E8E8E6]">·</span>
          <button
            onClick={() => exportSession("ris")}
            className="text-xs font-mono text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors"
          >
            RIS
          </button>
          <span className="text-[#E8E8E6]">·</span>
          <button
            onClick={() => exportSession("csv")}
            className="text-xs font-mono text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors"
          >
            CSV
          </button>
          <span className="text-[#E8E8E6]">·</span>
          <button
            onClick={() => exportSession("zip")}
            className="text-xs font-mono text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors"
          >
            ZIP
          </button>

          <span className="text-[#E8E8E6]">|</span>

          {/* Incognito Toggle */}
          <button
            onClick={toggleIncognito}
            className={`text-xs font-mono transition-colors ${
              incognitoMode
                ? "text-[#1A1A1A] font-medium"
                : "text-[#9A9A9A] hover:text-[#1A1A1A]"
            }`}
          >
            incognito: {incognitoMode ? "on" : "off"}
          </button>

          <span className="text-[#E8E8E6]">|</span>

          {/* Clear Session */}
          <button
            onClick={clearSession}
            className="text-xs font-mono text-[#9A9A9A] hover:text-[#1A1A1A] transition-colors"
          >
            clear session
          </button>

          <span className="text-[#E8E8E6]">|</span>

          {/* Manifest Export/Import */}
          <button
            onClick={exportManifest}
            className="text-xs font-mono text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors"
          >
            export manifest
          </button>
          <label className="text-xs font-mono text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors cursor-pointer">
            import manifest
            <input
              type="file"
              accept=".scholarsearch,.json"
              className="hidden"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (file) {
                  const result = await importManifest(file);
                  if (!result.success) {
                    console.error("Import failed:", result.error);
                  }
                }
              }}
            />
          </label>
        </div>
      )}

      {/* Command Palette — E key exclusion reasons */}
      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setIsPaletteOpen(false)}
        onSelect={(reason) => {
          const paper = results.find(
            (p) => (p.doi ?? p.id ?? `${p.title}-${p.source}`) === activeCardId,
          );
          if (paper) excludePaper(paper, reason, "ta");
          setIsPaletteOpen(false);
        }}
      />

      {/* Hotkey hint */}
      {results.length > 0 && (
        <div className="text-center text-xs text-[#9A9A9A] font-mono">
          j/k navigate · space expand · p promote · e exclude
        </div>
      )}
    </div>
  );
}
