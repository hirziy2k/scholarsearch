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
        placeholder="Enter your research question (e.g., Does dry eye disease affect night driving?)"
        className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-base shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        disabled={isSearching}
      />
      <button
        onClick={onSearch}
        disabled={isSearching || !value.trim()}
        className="rounded-lg bg-blue-600 px-6 py-3 text-base font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSearching ? (
          <span className="flex items-center gap-2">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Searching...
          </span>
        ) : (
          "Search"
        )}
      </button>
    </div>
  );
}
