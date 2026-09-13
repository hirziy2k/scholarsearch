/**
 * IndexedDB Session Persistence with TTL and Incognito Mode
 * 
 * Provides durable session storage for ScholarSearch with:
 * - 24-hour TTL (auto-wipe on staleness)
 * - Tab-close wipe (60s hidden timer + beforeunload)
 * - Incognito mode (skips all writes)
 * - Clear session function
 */

import { openDB, type IDBPDatabase } from "idb";

const DB_NAME = "scholarsearch-session";
const DB_VERSION = 1;
const STORE_NAME = "state";
const STATE_KEY = "current";
const TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const HIDDEN_WIPE_MS = 60 * 1000; // 60 seconds

interface PersistedState {
  results: any[];
  bookmarks: any[];
  validations: any[];
  exclusions: any[];
  promotedPapers: any[];
  lastQuery: string;
  lastMode: string;
  lastWeights: any;
  gapAnalysis: any;
  shadowMergeFlags: any[];
  incognitoMode: boolean;
  createdAt: string;
  lastSavedAt: string;
}

let dbInstance: IDBPDatabase | null = null;
let hiddenTimer: ReturnType<typeof setTimeout> | null = null;
let wipeEnabled = true;

async function getDB(): Promise<IDBPDatabase> {
  if (!dbInstance) {
    dbInstance = await openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME);
        }
      },
    });
  }
  return dbInstance;
}

/**
 * Load persisted state from IndexedDB.
 * Returns null if no state exists or if state is older than TTL.
 */
export async function loadState(): Promise<PersistedState | null> {
  try {
    const db = await getDB();
    const stored = await db.get(STORE_NAME, STATE_KEY);
    if (!stored) return null;

    // Check TTL
    const createdAt = new Date(stored.createdAt).getTime();
    if (Date.now() - createdAt > TTL_MS) {
      // State is stale — wipe it
      await clearState();
      return null;
    }

    return stored as PersistedState;
  } catch {
    return null;
  }
}

/**
 * Save state to IndexedDB.
 * Skips write if incognitoMode is true.
 */
export async function saveState(state: PersistedState): Promise<void> {
  if (state.incognitoMode) return;
  if (!wipeEnabled) return;

  try {
    const db = await getDB();
    const toSave = {
      ...state,
      lastSavedAt: new Date().toISOString(),
    };
    await db.put(STORE_NAME, toSave, STATE_KEY);
  } catch {
    // Silently fail — state remains in memory
  }
}

/**
 * Clear all persisted state from IndexedDB.
 */
export async function clearState(): Promise<void> {
  try {
    const db = await getDB();
    await db.delete(STORE_NAME, STATE_KEY);
  } catch {
    // Silently fail
  }
}

/**
 * Start the tab-close wipe timer.
 * Called when the browser tab becomes hidden.
 */
export function startHiddenTimer(): void {
  if (hiddenTimer) clearTimeout(hiddenTimer);
  hiddenTimer = setTimeout(async () => {
    if (wipeEnabled) {
      await clearState();
    }
  }, HIDDEN_WIPE_MS);
}

/**
 * Cancel the tab-close wipe timer.
 * Called when the browser tab becomes visible again.
 */
export function cancelHiddenTimer(): void {
  if (hiddenTimer) {
    clearTimeout(hiddenTimer);
    hiddenTimer = null;
  }
}

/**
 * Setup tab-close event listeners.
 * Call once on mount.
 */
export function setupTabCloseListeners(): () => void {
  const handleVisibility = () => {
    if (document.hidden) {
      startHiddenTimer();
    } else {
      cancelHiddenTimer();
    }
  };

  const handleBeforeUnload = () => {
    if (wipeEnabled) {
      // Synchronous wipe attempt using sendBeacon or synchronous XHR
      // Note: IndexedDB delete is async, but we attempt it anyway
      try {
        const dbRequest = indexedDB.open(DB_NAME, DB_VERSION);
        dbRequest.onsuccess = () => {
          const db = dbRequest.result;
          const tx = db.transaction(STORE_NAME, "readwrite");
          tx.objectStore(STORE_NAME).delete(STATE_KEY);
          tx.oncomplete = () => db.close();
        };
      } catch {
        // Best effort — browser may not complete before unload
      }
    }
  };

  document.addEventListener("visibilitychange", handleVisibility);
  window.addEventListener("beforeunload", handleBeforeUnload);

  return () => {
    document.removeEventListener("visibilitychange", handleVisibility);
    window.removeEventListener("beforeunload", handleBeforeUnload);
    cancelHiddenTimer();
  };
}

/**
 * Disable or enable wipe behavior.
 * Used by incognito mode toggle.
 */
export function setWipeEnabled(enabled: boolean): void {
  wipeEnabled = enabled;
}
