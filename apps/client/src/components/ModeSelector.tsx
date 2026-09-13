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
  { value: "openness", label: "Openness", description: "OA/code/dataset priority" },
];

interface ModeSelectorProps {
  value: SearchMode;
  onChange: (mode: SearchMode) => void;
}

export function ModeSelector({ value, onChange }: ModeSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-[#6B6B6B]">mode:</span>
      <select
        value={value}
        onChange={(e) => onChange((e.target as HTMLSelectElement).value as SearchMode)}
        className="rounded-md border border-[#E8E8E6] bg-white px-3 py-1.5 text-sm text-[#1A1A1A] shadow-sm focus:border-[#1A1A1A] focus:outline-none focus:ring-1 focus:ring-[#1A1A1A]/20"
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
