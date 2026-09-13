"use client";

import React from "react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
  isSearching: boolean;
}

export function SearchBar({ value, onChange, onSearch, isSearching }: SearchBarProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !isSearching) {
      onSearch();
    }
  };

  return (
    <div className="flex gap-3">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="research question..."
        className="flex-1 rounded-lg border border-[#E8E8E6] bg-white px-4 py-3 text-base text-[#1A1A1A] shadow-sm focus:border-[#1A1A1A] focus:outline-none focus:ring-1 focus:ring-[#1A1A1A]/20 placeholder:text-[#9A9A9A]"
        disabled={isSearching}
      />
      <button
        onClick={onSearch}
        disabled={isSearching || !value.trim()}
        className="rounded-lg bg-[#1A1A1A] px-6 py-3 text-base font-medium text-[#FAFAF8] shadow-sm hover:bg-[#3D3D3D] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isSearching ? (
          <span className="flex items-center gap-2">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            searching...
          </span>
        ) : (
          "search"
        )}
      </button>
    </div>
  );
}
