"use client";

import { useState, useCallback, useRef } from "react";

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
}

export function useSSESearch() {
  const [state, setState] = useState<SearchState>({
    results: [],
    isSearching: false,
    progress: [],
    error: null,
    searchId: null,
    totalRaw: 0,
    totalDeduplicated: 0,
    duplicatesRemoved: 0,
    durationMs: 0,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  const search = useCallback(async (query: {
    raw_query: string;
    mode: string;
    weights?: any;
    max_results?: number;
  }) => {
    // Abort any previous search
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setState({
      results: [],
      isSearching: true,
      progress: [],
      error: null,
      searchId: null,
      totalRaw: 0,
      totalDeduplicated: 0,
      duplicatesRemoved: 0,
      durationMs: 0,
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

        // Process SSE events
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
        return; // Search was cancelled
      }
      setState((prev) => ({
        ...prev,
        isSearching: false,
        error: error instanceof Error ? error.message : String(error),
      }));
    }
  }, []);

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

  return {
    ...state,
    search,
    cancel,
  };
}
