"use client";

import { useRef, useEffect, useState, useCallback, useLayoutEffect } from "react";
import { ResultCard } from "./ResultCard";

interface ResultListProps {
  results: any[];
  query: string;
  onBookmark?: (paper: any) => void;
  isBookmarked?: (paperId: string) => boolean;
  activeIndexRef: React.MutableRefObject<number>;
}

export function ResultList({ results, query, onBookmark, isBookmarked, activeIndexRef }: ResultListProps) {
  const observerRef = useRef<IntersectionObserver | null>(null);
  const [visibleCards, setVisibleCards] = useState<Set<string>>(new Set());
  const cardRefsMap = useRef<Map<string, HTMLDivElement>>(new Map());

  // Re-paint hook: re-apply is-active-card after every render, before browser paint
  useLayoutEffect(() => {
    const cards = document.querySelectorAll("[data-paper-id]");
    const activeIdx = activeIndexRef.current;

    // Clear all first
    cards.forEach((card) => card.classList.remove("is-active-card"));

    // Re-apply to current
    if (cards[activeIdx]) {
      cards[activeIdx].classList.add("is-active-card");
    }
  }); // No deps — fires on EVERY render to survive SSE re-renders

  // Singleton IntersectionObserver
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        setVisibleCards((prev) => {
          const next = new Set(prev);
          for (const entry of entries) {
            const id = entry.target.getAttribute("data-paper-id");
            if (!id) continue;
            if (entry.isIntersecting) {
              next.add(id);
            } else {
              next.delete(id);
            }
          }
          return next;
        });
      },
      { threshold: 0.1, rootMargin: "50px" },
    );

    return () => {
      observerRef.current?.disconnect();
      observerRef.current = null;
    };
  }, []);

  // Register/unregister cards with the singleton observer
  const registerCard = useCallback((ref: HTMLDivElement | null, paperId: string) => {
    const observer = observerRef.current;
    if (!observer) return;

    if (ref) {
      ref.setAttribute("data-paper-id", paperId);
      observer.observe(ref);
      cardRefsMap.current.set(paperId, ref);
    } else {
      const existing = cardRefsMap.current.get(paperId);
      if (existing) {
        observer.unobserve(existing);
        cardRefsMap.current.delete(paperId);
      }
    }
  }, []);

  // Clean up observer entries for removed papers
  useEffect(() => {
    const currentIds = new Set(results.map((p: any) => p.doi ?? p.DOI ?? `${p.title}-${p.source}`));
    const observer = observerRef.current;
    if (!observer) return;

    for (const [id, ref] of cardRefsMap.current) {
      if (!currentIds.has(id)) {
        observer.unobserve(ref);
        cardRefsMap.current.delete(id);
      }
    }

    // Prune visibleCards of stale entries
    setVisibleCards((prev) => {
      const next = new Set<string>();
      for (const id of prev) {
        if (currentIds.has(id)) next.add(id);
      }
      return next;
    });
  }, [results]);

  if (results.length === 0) {
    return (
      <div className="py-12 text-center text-[#9A9A9A]">
        {query
          ? "no results — try adjusting your query"
          : "enter a search query to find academic literature"}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#1A1A1A]">
          results ({results.length})
        </h2>
      </div>

      <div className="space-y-4">
        {results.map((paper, index) => {
          const paperId = paper.doi ?? paper.DOI ?? `${paper.title}-${paper.source}`;
          return (
            <ResultCard
              key={paperId}
              paper={paper}
              index={index}
              onBookmark={onBookmark}
              isBookmarked={isBookmarked?.(paperId)}
              isVisible={visibleCards.has(paperId)}
              registerCard={registerCard}
            />
          );
        })}
      </div>
    </div>
  );
}
