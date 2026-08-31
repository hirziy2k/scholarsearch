"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { EXCLUSION_REASONS } from "../hooks/useHotkeys";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (reason: string) => void;
}

export function CommandPalette({ isOpen, onClose, onSelect }: CommandPaletteProps) {
  const [filter, setFilter] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = EXCLUSION_REASONS.filter((r) =>
    r.reason.toLowerCase().includes(filter.toLowerCase()),
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [filter]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setFilter("");
    }
  }, [isOpen]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filtered.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (filtered[selectedIndex]) {
          onSelect(filtered[selectedIndex].reason);
        }
        break;
      case "Escape":
        e.preventDefault();
        onClose();
        break;
    }
  }, [filtered, selectedIndex, onSelect, onClose]);

  if (!isOpen) return null;

  return (
    <>
      <div className="command-palette-backdrop" onClick={onClose} />
      <div className="command-palette">
        <input
          ref={inputRef}
          type="text"
          placeholder="filter reasons..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="max-h-48 overflow-y-auto">
          {filtered.map((r, i) => (
            <div
              key={r.key}
              className={`command-palette-option ${i === selectedIndex ? "active" : ""}`}
              onClick={() => onSelect(r.reason)}
            >
              <span className="key">{r.key}</span>
              <span className="label">{r.reason}</span>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="command-palette-option">
              <span className="label text-[#6B6B6B]">no matching reasons</span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
