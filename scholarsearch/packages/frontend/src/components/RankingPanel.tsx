"use client";

import type { RankingWeights } from "@scholarsearch/shared";

interface RankingPanelProps {
  weights: RankingWeights;
  onChange: (weights: RankingWeights) => void;
}

const WEIGHT_LABELS: Array<{ key: keyof RankingWeights; label: string }> = [
  { key: "relevance", label: "Relevance" },
  { key: "semantic_similarity", label: "Semantic Similarity" },
  { key: "keyword_match", label: "Keyword Match" },
  { key: "peer_review", label: "Peer Review" },
  { key: "study_design", label: "Study Design" },
  { key: "citation_impact", label: "Citations" },
  { key: "journal_quality", label: "Journal Quality" },
  { key: "recency", label: "Recency" },
  { key: "oa_availability", label: "OA Availability" },
];

export function RankingPanel({ weights, onChange }: RankingPanelProps) {
  const handleChange = (key: keyof RankingWeights, value: number) => {
    onChange({ ...weights, [key]: value });
  };

  const total = Object.values(weights).reduce((sum, v) => sum + v, 0);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Ranking Weights</h3>
        <span
          className={`text-xs ${Math.abs(total - 1) < 0.01 ? "text-green-600" : "text-amber-600"}`}
        >
          Total: {total.toFixed(2)} {Math.abs(total - 1) < 0.01 ? "✓" : "(should be 1.00)"}
        </span>
      </div>

      <div className="space-y-4">
        {WEIGHT_LABELS.map(({ key, label }) => (
          <div key={key} className="flex items-center gap-4">
            <label className="w-40 text-sm text-gray-600">{label}</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={weights[key]}
              onChange={(e) => handleChange(key, parseFloat(e.target.value))}
              className="flex-1"
            />
            <span className="w-12 text-right text-sm font-mono text-gray-900">
              {weights[key].toFixed(2)}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex justify-end">
        <button
          onClick={() =>
            onChange({
              relevance: 0.25,
              semantic_similarity: 0.20,
              keyword_match: 0.15,
              peer_review: 0.10,
              study_design: 0.10,
              citation_impact: 0.10,
              journal_quality: 0.10,
              recency: 0.10,
              oa_availability: 0.05,
            })
          }
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
