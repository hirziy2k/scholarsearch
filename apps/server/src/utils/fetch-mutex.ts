// ============================================
// In-Memory Fetch Mutex
// ============================================
// Prevents redundant API calls when multiple clients poll for the same page.
// Maps a composite key to the in-flight promise. If a second request arrives
// for the same key, it awaits the existing promise instead of initiating
// a new network call. Entry cleaned up via .finally() regardless of outcome.

const inflight = new Map<string, Promise<any>>();

export async function fetchWithMutex<T>(
  key: string,
  fetcher: () => Promise<T>,
): Promise<T> {
  if (inflight.has(key)) {
    return inflight.get(key)! as Promise<T>;
  }

  const promise = fetcher().finally(() => {
    inflight.delete(key);
  });

  inflight.set(key, promise as Promise<any>);
  return promise;
}

export function getInflightCount(): number {
  return inflight.size;
}
