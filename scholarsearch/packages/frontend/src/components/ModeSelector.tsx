"use client";

import type { SearchMode } from "@scholarsearch/shared";

const MODES: Array<{ value: SearchMode; label: string; description: string }> = [
  { value: "discovery", label: "Discovery", description: "Broadest search" },
  { value: "evidence", label: "Evidence", description: "Peer-reviewed priority" },
  { value: "clinical", label: "Clinical", description: "PICO-aligned" },
  { value: "systematic_review", label: "Systematic Review", description: "High recall" },
  { value: "thesis", label: "Thesis", description: "Claim support" },
  { value: "adversarial", label: "Adversarial", description: "Contradictory evidence" },
  { value: "bibliometric", label: "Bibliometric", description: "Citation analysis" },
];

interface ModeSelectorProps {
  value: SearchMode;
  onChange: (mode: SearchMode) => void;
}

export function ModeSelector({ value, onChange }: ModeSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-gray-600">Mode:</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as SearchMode)}
        className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {MODES.map((mode) => (
          <option key={mode.value} value={mode.value}>
            {mode.label} — {mode.description}
          </option>
        ))}
      </select>
    </div>
  );
}
