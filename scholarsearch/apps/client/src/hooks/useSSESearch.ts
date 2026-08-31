"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  loadState,
  saveState,
  clearState,
  setupTabCloseListeners,
  setWipeEnabled,
} from "../lib/session-db";
import { generateRIS, downloadRIS } from "../lib/ris-export";
import { downloadArchive } from "../lib/archive-export";
import {
  generateManifest,
  exportManifest as exportManifestFile,
  parseManifest,
  reconcileManifests,
  applyReconciliation,
  type SessionManifest,
} from "../lib/session-manifest";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";

interface SourceProgress {
  source: string;
  status: "started" | "completed" | "error";
  count?: number;
}

interface Paper {
  source: string;
  [key: string]: any;
}

interface Bookmark {
  paperId: string;
  title: string;
  doi?: string;
  source: string;
  tier?: number;
  relevanceScore?: number;
  addedAt: string;
}

interface Validation {
  paperId: string;
  validatedBy: string;
  validatedAt: string;
  comment?: string;
}

interface Exclusion {
  paperId: string;
  sourceRecords: Array<{ source: string; sourceId: string }>;
  reason: string;
  timestamp: string;
  phase: "ta" | "fulltext";
}

interface PromotedPaper {
  paperId: string;
  sourceRecords: Array<{ source: string; sourceId: string }>;
  promotedFrom: "ta";
  promotedAt: string;
}

interface ShadowMergeFlag {
  pairedPaperId: string;
  pairedSource: string;
  pairedTitle: string;
  similarity: number;
  reasons: string[];
}

interface SearchState {
  results: Paper[];
  isSearching: boolean;
  progress: SourceProgress[];
  error: string | null;
  searchId: string | null;
  totalRaw: number;
  totalDeduplicated: number;
  duplicatesRemoved: number;
  durationMs: number;
  gapAnalysis: any | null;
  bookmarks: Bookmark[];
  validations: Validation[];
  exclusions: Exclusion[];
  promotedPapers: PromotedPaper[];
  shadowMergeFlags: ShadowMergeFlag[];
  lastQuery: string;
  lastMode: string;
  lastWeights: any;
  incognitoMode: boolean;
}

const DEFAULT_STATE: SearchState = {
  results: [],
  isSearching: false,
  progress: [],
  error: null,
  searchId: null,
  totalRaw: 0,
  totalDeduplicated: 0,
  duplicatesRemoved: 0,
  durationMs: 0,
  gapAnalysis: null,
  bookmarks: [],
  validations: [],
  exclusions: [],
  promotedPapers: [],
  shadowMergeFlags: [],
  lastQuery: "",
  lastMode: "discovery",
  lastWeights: null,
  incognitoMode: false,
};

export function useSSESearch() {
  const [state, setState] = useState<SearchState>(DEFAULT_STATE);
  const [loaded, setLoaded] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Hydrate from IndexedDB on mount
  useEffect(() => {
    (async () => {
      const saved = await loadState();
      if (saved) {
        setState((prev) => ({
          ...prev,
          results: saved.results ?? [],
          bookmarks: saved.bookmarks ?? [],
          validations: saved.validations ?? [],
          exclusions: saved.exclusions ?? [],
          promotedPapers: saved.promotedPapers ?? [],
          shadowMergeFlags: saved.shadowMergeFlags ?? [],
          lastQuery: saved.lastQuery ?? "",
          lastMode: saved.lastMode ?? "discovery",
          lastWeights: saved.lastWeights ?? null,
          gapAnalysis: saved.gapAnalysis ?? null,
          incognitoMode: saved.incognitoMode ?? false,
        }));
      }
      setLoaded(true);
    })();

    // Setup tab-close wipe listeners
    const cleanup = setupTabCloseListeners();
    return cleanup;
  }, []);

  // Debounced save to IndexedDB (500ms)
  useEffect(() => {
    if (!loaded) return;
    if (state.incognitoMode) return;

    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      saveState({
        results: state.results,
        bookmarks: state.bookmarks,
        validations: state.validations,
        exclusions: state.exclusions,
        promotedPapers: state.promotedPapers,
        shadowMergeFlags: state.shadowMergeFlags,
        lastQuery: state.lastQuery,
        lastMode: state.lastMode,
        lastWeights: state.lastWeights,
        gapAnalysis: state.gapAnalysis,
        incognitoMode: state.incognitoMode,
        createdAt: new Date().toISOString(),
        lastSavedAt: new Date().toISOString(),
      });
    }, 500);

    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [
    loaded,
    state.incognitoMode,
    state.results,
    state.bookmarks,
    state.validations,
    state.exclusions,
    state.promotedPapers,
    state.lastQuery,
    state.lastMode,
    state.lastWeights,
    state.gapAnalysis,
  ]);

  // Update wipe behavior when incognito mode changes
  useEffect(() => {
    setWipeEnabled(!state.incognitoMode);
  }, [state.incognitoMode]);

  const search = useCallback(async (query: {
    raw_query: string;
    mode: string;
    weights?: any;
    max_results?: number;
  }) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setState({
      ...DEFAULT_STATE,
      isSearching: true,
      bookmarks: state.bookmarks,
      validations: state.validations,
      exclusions: state.exclusions,
      promotedPapers: state.promotedPapers,
      shadowMergeFlags: state.shadowMergeFlags,
      incognitoMode: state.incognitoMode,
      lastQuery: query.raw_query,
      lastMode: query.mode,
      lastWeights: query.weights ?? null,
    });

    try {
      const response = await fetch(`${API_URL}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(query),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7);
          } else if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr);
              handleSSEEvent(eventType, data);
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }
      setState((prev) => ({
        ...prev,
        isSearching: false,
        error: error instanceof Error ? error.message : String(error),
      }));
    }
  }, [state.bookmarks, state.validations, state.exclusions, state.promotedPapers, state.shadowMergeFlags, state.incognitoMode]);

  function handleSSEEvent(eventType: string, data: any) {
    switch (eventType) {
      case "source_progress":
        setState((prev) => ({
          ...prev,
          progress: [
            ...prev.progress.filter((p) => p.source !== data.source),
            { source: data.source, status: data.status, count: data.count },
          ],
        }));
        break;

      case "paper":
        setState((prev) => ({
          ...prev,
          results: [...prev.results, { source: data.source, ...data.paper }],
        }));
        break;

      case "results":
        setState((prev) => ({
          ...prev,
          searchId: data.searchId,
          totalRaw: data.totalRaw,
          totalDeduplicated: data.totalDeduplicated,
          duplicatesRemoved: data.duplicatesRemoved,
          durationMs: data.durationMs,
          gapAnalysis: data.gapAnalysis ?? prev.gapAnalysis,
          shadowMergeFlags: data.shadowMergeFlags ?? prev.shadowMergeFlags,
        }));
        break;

      case "done":
        setState((prev) => ({
          ...prev,
          isSearching: false,
        }));
        break;

      case "error":
        setState((prev) => ({
          ...prev,
          isSearching: false,
          error: data.message,
        }));
        break;
    }
  }

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
    setState((prev) => ({ ...prev, isSearching: false }));
  }, []);

  // ============================================
  // Source Record Extraction (for Shadow Ledger)
  // ============================================

  const getSourceRecords = useCallback((paper: Paper): Array<{ source: string; sourceId: string }> => {
    const records: Array<{ source: string; sourceId: string }> = [];

    // Primary source record
    const primarySource = paper._source ?? paper.source ?? "unknown";
    const primaryId = paper.DOI ?? paper.doi ?? paper.id ?? `${paper.title}-${primarySource}`;
    records.push({ source: primarySource, sourceId: primaryId });

    // Shadow merge records
    if (state.shadowMergeFlags) {
      for (const flag of state.shadowMergeFlags) {
        if (flag.pairedPaperId === primaryId || flag.pairedTitle === paper.title) {
          records.push({ source: flag.pairedSource, sourceId: flag.pairedPaperId });
        }
      }
    }

    return records;
  }, [state.shadowMergeFlags]);

  // ============================================
  // Bookmark Actions
  // ============================================

  const addBookmark = useCallback((paper: Paper) => {
    const bookmark: Bookmark = {
      paperId: paper.id ?? paper.doi ?? `${paper.title}-${paper.source}`,
      title: paper.title,
      doi: paper.doi,
      source: paper.source ?? "unknown",
      tier: paper.tier,
      relevanceScore: paper.relevance_score,
      addedAt: new Date().toISOString(),
    };
    setState((prev) => ({
      ...prev,
      bookmarks: [...prev.bookmarks, bookmark],
    }));
  }, []);

  const removeBookmark = useCallback((paperId: string) => {
    setState((prev) => ({
      ...prev,
      bookmarks: prev.bookmarks.filter((b) => b.paperId !== paperId),
    }));
  }, []);

  const isBookmarked = useCallback((paperId: string) => {
    return state.bookmarks.some((b) => b.paperId === paperId);
  }, [state.bookmarks]);

  const addValidation = useCallback((paperId: string, validatedBy: string, comment?: string) => {
    const validation: Validation = {
      paperId,
      validatedBy,
      validatedAt: new Date().toISOString(),
      comment,
    };
    setState((prev) => ({
      ...prev,
      validations: [...prev.validations, validation],
    }));
  }, []);

  // ============================================
  // Screening Actions (Two-Phase)
  // ============================================

  const excludePaper = useCallback((paper: Paper, reason: string, phase: "ta" | "fulltext") => {
    const sourceRecords = getSourceRecords(paper);
    const exclusion: Exclusion = {
      paperId: paper.id ?? paper.doi ?? `${paper.title}-${paper.source}`,
      sourceRecords,
      reason,
      timestamp: new Date().toISOString(),
      phase,
    };
    setState((prev) => ({
      ...prev,
      exclusions: [...prev.exclusions, exclusion],
    }));
  }, [getSourceRecords]);

  const promotePaper = useCallback((paper: Paper) => {
    const sourceRecords = getSourceRecords(paper);
    const promotion: PromotedPaper = {
      paperId: paper.id ?? paper.doi ?? `${paper.title}-${paper.source}`,
      sourceRecords,
      promotedFrom: "ta",
      promotedAt: new Date().toISOString(),
    };
    setState((prev) => ({
      ...prev,
      promotedPapers: [...prev.promotedPapers, promotion],
    }));
  }, [getSourceRecords]);

  // ============================================
  // Incognito Mode
  // ============================================

  const toggleIncognito = useCallback(() => {
    setState((prev) => ({
      ...prev,
      incognitoMode: !prev.incognitoMode,
    }));
  }, []);

  // ============================================
  // Clear Session
  // ============================================

  const clearSession = useCallback(async () => {
    await clearState();
    setState(DEFAULT_STATE);
  }, []);

  // ============================================
  // Session Manifest (Export & Import)
  // ============================================

  const exportManifest = useCallback(() => {
    const manifest = generateManifest({
      results: state.results,
      bookmarks: state.bookmarks,
      validations: state.validations,
      exclusions: state.exclusions,
      promotedPapers: state.promotedPapers,
      gapAnalysis: state.gapAnalysis,
      lastQuery: state.lastQuery,
      lastMode: state.lastMode,
      lastWeights: state.lastWeights,
    });
    exportManifestFile(manifest);
  }, [state]);

  const importManifest = useCallback(async (file: File): Promise<{ success: boolean; error?: string; stats?: any }> => {
    const text = await file.text();
    const result = parseManifest(text);
    if ("error" in result) {
      return { success: false, error: result.error };
    }

    const reconciliation = reconcileManifests(
      {
        papers: state.results,
        bookmarks: state.bookmarks,
        exclusions: state.exclusions,
        promotedPapers: state.promotedPapers,
      },
      result.manifest,
    );

    // For now, always merge (user can choose replace via UI later)
    const merged = applyReconciliation(
      {
        results: state.results,
        bookmarks: state.bookmarks,
        validations: state.validations,
        exclusions: state.exclusions,
        promotedPapers: state.promotedPapers,
        gapAnalysis: state.gapAnalysis,
        lastQuery: state.lastQuery,
        lastMode: state.lastMode,
        lastWeights: state.lastWeights,
      },
      result.manifest,
      "merge",
    );

    setState((prev) => ({
      ...prev,
      results: merged.results,
      bookmarks: merged.bookmarks,
      exclusions: merged.exclusions,
      promotedPapers: merged.promotedPapers,
      lastQuery: merged.lastQuery,
      lastMode: merged.lastMode,
      lastWeights: merged.lastWeights,
      gapAnalysis: merged.gapAnalysis,
    }));

    return { success: true, stats: reconciliation.stats };
  }, [state]);

  // ============================================
  // Forward-Only Discovery Feed
  // ============================================

  const [discoveryFeed, setDiscoveryFeed] = useState<any[]>([]);

  const checkDiscovery = useCallback(async (manifest: SessionManifest) => {
    if (!manifest.lastSavedAt) return;

    const dateFrom = manifest.lastSavedAt.split("T")[0];
    const augmentedQuery = {
      raw_query: manifest.queryParameters.raw_query,
      mode: manifest.queryParameters.mode,
      weights: manifest.queryParameters.weights,
      max_results: 50,
      filters: { date_from: dateFrom },
    };

    try {
      const response = await fetch(`${API_URL}/api/search/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(augmentedQuery),
      });

      if (!response.ok) return;
      const data = await response.json();

      // Filter to only papers NOT in the current session
      const currentIds = new Set(state.results.map((p: any) => p.doi ?? p.id));
      const newPapers = (data.results ?? []).filter((p: any) => {
        const id = p.doi ?? p.id;
        return id && !currentIds.has(id);
      });

      setDiscoveryFeed(newPapers);
    } catch {
      // Silently fail
    }
  }, [state.results]);

  const mergeDiscoveryFeed = useCallback(() => {
    setState((prev) => ({
      ...prev,
      results: [...prev.results, ...discoveryFeed],
    }));
    setDiscoveryFeed([]);
  }, [discoveryFeed]);

  const dismissDiscoveryFeed = useCallback(() => {
    setDiscoveryFeed([]);
  }, []);

  // ============================================
  // Export
  // ============================================

  const exportSession = useCallback((format: "json" | "csv" | "ris" | "zip") => {
    if (format === "ris") {
      downloadRIS(state.results, `scholarsearch-references-${Date.now()}.ris`);
      return;
    }

    if (format === "zip") {
      downloadArchive({
        query: state.lastQuery,
        mode: state.lastMode,
        results: state.results,
        bookmarks: state.bookmarks,
        validations: state.validations,
        exclusions: state.exclusions,
        promotedPapers: state.promotedPapers,
        shadowMergeFlags: state.shadowMergeFlags,
        gapAnalysis: state.gapAnalysis,
        lastQuery: state.lastQuery,
        lastMode: state.lastMode,
        lastWeights: state.lastWeights,
        totalRaw: state.totalRaw,
        duplicatesRemoved: state.duplicatesRemoved,
      });
      return;
    }

    const exportData = {
      version: "1.0",
      exportedAt: new Date().toISOString(),
      query: state.lastQuery,
      mode: state.lastMode,
      weights: state.lastWeights,
      bookmarks: state.bookmarks,
      validations: state.validations,
      exclusions: state.exclusions,
      promotedPapers: state.promotedPapers,
      papers: state.results,
      gapAnalysis: state.gapAnalysis,
    };

    if (format === "json") {
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scholarsearch-session-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      const headers = ["id", "title", "authors", "doi", "source", "tier", "relevance_score", "journal", "publication_date"];
      const rows = state.results.map((p) => [
        p.id ?? "",
        `"${(p.title ?? "").replace(/"/g, '""')}"`,
        `"${(p.authors ?? []).join("; ")}"`,
        p.doi ?? "",
        p.source ?? "",
        p.tier?.toString() ?? "",
        p.relevance_score?.toString() ?? "",
        `"${p.journal ?? ""}"`,
        p.publication_date ?? "",
      ]);
      const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scholarsearch-papers-${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }, [state.results, state.bookmarks, state.validations, state.exclusions, state.promotedPapers, state.lastQuery, state.lastMode, state.lastWeights, state.gapAnalysis]);

  return {
    ...state,
    loaded,
    search,
    cancel,
    addBookmark,
    removeBookmark,
    isBookmarked,
    addValidation,
    excludePaper,
    promotePaper,
    toggleIncognito,
    clearSession,
    exportSession,
    exportManifest,
    importManifest,
    discoveryFeed,
    checkDiscovery,
    mergeDiscoveryFeed,
    dismissDiscoveryFeed,
  };
}
