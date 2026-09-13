"use client";

import { useRef, useEffect, useState, useCallback } from "react";

export const EXCLUSION_REASONS = [
  { key: "1", reason: "Wrong population" },
  { key: "2", reason: "Wrong intervention" },
  { key: "3", reason: "Wrong outcome" },
  { key: "4", reason: "Wrong study design" },
  { key: "5", reason: "Wrong setting" },
  { key: "6", reason: "Duplicate (missed dedup)" },
  { key: "7", reason: "Not original research" },
  { key: "8", reason: "Insufficient data" },
  { key: "9", reason: "Insufficient sample size" },
  { key: "0", reason: "Custom reason..." },
] as const;

interface HotkeyCallbacks {
  onPromote: (paper: any) => void;
  onExclude: (paper: any, reason: string) => void;
  onToggleExpand: (paperId: string) => void;
}

interface HotkeyState {
  activeCardId: string | null;
  activeIndexRef: React.MutableRefObject<number>;
  isPaletteOpen: boolean;
  isModalOpen: boolean;
  setIsPaletteOpen: (open: boolean) => void;
}

export function useHotkeys(
  results: any[],
  callbacks: HotkeyCallbacks,
): HotkeyState {
  const activeIndexRef = useRef(0);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const paletteInputRef = useRef<HTMLInputElement | null>(null);

  const getPaperId = useCallback((paper: any): string => {
    return paper?.doi ?? paper?.id ?? paper?.title ?? "";
  }, []);

  const getLivePaperId = useCallback((): string | null => {
    const cards = document.querySelectorAll("[data-paper-id]");
    return cards[activeIndexRef.current]?.getAttribute("data-paper-id") ?? null;
  }, []);

  const updateActiveVisuals = useCallback((oldIndex: number, newIndex: number) => {
    const cards = document.querySelectorAll("[data-paper-id]");

    if (cards[oldIndex]) {
      cards[oldIndex].classList.remove("is-active-card");
    }

    if (cards[newIndex]) {
      cards[newIndex].classList.add("is-active-card");
      cards[newIndex].scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, []);

  const confirmExclusion = useCallback((reason: string) => {
    const liveId = getLivePaperId();
    const paper = results.find((p) => (p.doi ?? p.id ?? p.title) === liveId);
    if (paper && reason) {
      callbacks.onExclude(paper, reason);
    }
    setIsPaletteOpen(false);
  }, [results, callbacks, getLivePaperId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const tag = target?.tagName;
      const isInput = tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable;

      if (isPaletteOpen && isInput) {
        if (e.key === "Escape") {
          e.preventDefault();
          setIsPaletteOpen(false);
          return;
        }
        if (e.key >= "1" && e.key <= "8") {
          e.preventDefault();
          const match = EXCLUSION_REASONS.find((r) => r.key === e.key);
          if (match) confirmExclusion(match.reason);
          return;
        }
        return;
      }

      if (isInput) return;

      const len = results.length;
      if (len === 0) return;

      switch (e.key) {
        case "j":
        case "ArrowDown": {
          e.preventDefault();
          const old = activeIndexRef.current;
          const next = Math.min(old + 1, len - 1);
          activeIndexRef.current = next;
          updateActiveVisuals(old, next);
          setActiveCardId(getPaperId(results[next]));
          break;
        }
        case "k":
        case "ArrowUp": {
          e.preventDefault();
          const old = activeIndexRef.current;
          const prev = Math.max(old - 1, 0);
          activeIndexRef.current = prev;
          updateActiveVisuals(old, prev);
          setActiveCardId(getPaperId(results[prev]));
          break;
        }
        case " ": {
          e.preventDefault();
          const liveId = getLivePaperId();
          if (liveId) callbacks.onToggleExpand(liveId);
          setIsModalOpen((prev) => !prev);
          break;
        }
        case "p":
        case "P": {
          e.preventDefault();
          const liveId = getLivePaperId();
          const paper = results.find((p) => (p.doi ?? p.id ?? p.title) === liveId);
          if (paper) callbacks.onPromote(paper);
          break;
        }
        case "e":
        case "E": {
          e.preventDefault();
          const liveId = getLivePaperId();
          setActiveCardId(liveId);
          setIsPaletteOpen(true);
          break;
        }
        case "Escape": {
          if (isPaletteOpen) {
            setIsPaletteOpen(false);
          } else if (isModalOpen) {
            setIsModalOpen(false);
          }
          break;
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [results, callbacks, isPaletteOpen, isModalOpen, updateActiveVisuals, confirmExclusion, getPaperId, getLivePaperId]);

  useEffect(() => {
    if (isPaletteOpen && paletteInputRef.current) {
      paletteInputRef.current.focus();
    }
  }, [isPaletteOpen]);

  return { activeCardId, activeIndexRef, isPaletteOpen, isModalOpen, setIsPaletteOpen };
}
