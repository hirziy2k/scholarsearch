"use client";

import { useState, useEffect } from "react";

interface Bookmark {
  paperId: string;
  title?: string;
  source?: string;
  addedAt?: string;
}

export default function OfflinePage() {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [exclusions, setExclusions] = useState<any[]>([]);

  useEffect(() => {
    try {
      const request = indexedDB.open("scholarsearch-session");
      request.onsuccess = () => {
        const db = request.result;
        if (db.objectStoreNames.contains("state")) {
          const tx = db.transaction("state", "readonly");
          const store = tx.objectStore("state");
          const get = store.get("persisted");
          get.onsuccess = () => {
            const data = get.result;
            if (data?.bookmarks) setBookmarks(data.bookmarks);
            if (data?.exclusions) setExclusions(data.exclusions);
          };
        }
      };
    } catch {
      // IndexedDB not available
    }
  }, []);

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-[#1A1A1A]">ScholarSearch</h1>
        <p className="mt-2 text-sm text-[#6B6B6B]">
          you are offline — showing your locally saved session
        </p>
      </div>

      {bookmarks.length > 0 && (
        <div className="rounded-lg border border-[#E8E8E6] bg-[#FAFAF8] p-4">
          <h2 className="text-sm font-semibold text-[#1A1A1A] mb-2">
            saved papers ({bookmarks.length})
          </h2>
          <ul className="space-y-1">
            {bookmarks.map((b, i) => (
              <li key={i} className="text-xs font-mono text-[#3D3D3D]">
                {b.title ?? b.paperId}
                {b.source && <span className="text-[#9A9A9A] ml-1">({b.source})</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {exclusions.length > 0 && (
        <div className="rounded-lg border border-[#E8E8E6] bg-[#FAFAF8] p-4">
          <h2 className="text-sm font-semibold text-[#1A1A1A] mb-2">
            exclusions ({exclusions.length})
          </h2>
          <ul className="space-y-1">
            {exclusions.map((ex, i) => (
              <li key={i} className="text-xs font-mono text-[#3D3D3D]">
                <span className="text-[#9A9A9A]">{ex.reason}</span>
                <span className="ml-1">{ex.paperId}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {bookmarks.length === 0 && exclusions.length === 0 && (
        <div className="rounded-lg border border-dashed border-[#E8E8E6] bg-[#FAFAF8] p-6 text-center">
          <p className="text-sm text-[#9A9A9A]">
            no saved data found — your session will appear here once you search and bookmark papers
          </p>
        </div>
      )}

      <div className="text-center text-xs text-[#9A9A9A] font-mono">
        reconnect to resume searching · your PRISMA ledger is safe in IndexedDB
      </div>
    </div>
  );
}
