/**
 * Anchor Finder Web Worker
 * 
 * Resolves fuzzy anchor positions for micro-summary claims against abstracts.
 * Runs off the main thread to avoid blocking UI during Levenshtein computation.
 * 
 * Protocol:
 * - Input: { type: "resolve", paperId, abstract, claims }
 * - Output: { type: "resolved", paperId, anchors }
 * - Cancel: { type: "cancel", paperId }
 */

// Inline Levenshtein to avoid import issues in worker context
function levenshtein(a: string, b: string): number {
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;

  const matrix: number[][] = [];
  for (let i = 0; i <= b.length; i++) matrix[i] = [i];
  for (let j = 0; j <= a.length; j++) matrix[0][j] = j;

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      const cost = b.charAt(i - 1) === a.charAt(j - 1) ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost,
      );
    }
  }
  return matrix[b.length][a.length];
}

function levenshteinSimilarity(a: string, b: string): number {
  const maxLen = Math.max(a.length, b.length);
  if (maxLen === 0) return 1;
  return 1 - levenshtein(a, b) / maxLen;
}

function findFuzzyAnchor(
  abstract: string,
  claim: string,
  threshold: number = 0.7,
): { start: number; end: number; similarity: number } | null {
  if (!abstract || !claim) return null;

  const claimLen = claim.length;
  const abstractLower = abstract.toLowerCase();
  const claimLower = claim.toLowerCase();

  // Exact substring match first
  const exactIndex = abstractLower.indexOf(claimLower);
  if (exactIndex !== -1) {
    return { start: exactIndex, end: exactIndex + claimLen, similarity: 1 };
  }

  // Sliding window
  const windowStep = Math.max(1, Math.floor(claimLen / 4));
  let bestMatch: { start: number; end: number; similarity: number } | null = null;

  for (let i = 0; i <= abstract.length - claimLen; i += windowStep) {
    const window = abstractLower.substring(i, i + claimLen);
    const similarity = levenshteinSimilarity(claimLower, window);

    if (similarity >= threshold) {
      const expandRange = Math.floor(claimLen * 0.2);
      const start = Math.max(0, i - expandRange);
      const end = Math.min(abstract.length, i + claimLen + expandRange);

      for (let j = start; j <= i; j++) {
        for (let k = i + claimLen; k <= end; k++) {
          const candidate = abstractLower.substring(j, k);
          const sim = levenshteinSimilarity(claimLower, candidate);
          if (sim > (bestMatch?.similarity ?? 0)) {
            bestMatch = { start: j, end: k, similarity: sim };
          }
        }
      }

      if (!bestMatch) {
        bestMatch = { start: i, end: i + claimLen, similarity };
      }
    }
  }

  return bestMatch;
}

// Track cancelled paper IDs
const cancelled = new Set<string>();

self.onmessage = (e: MessageEvent) => {
  const { type, paperId, abstract, claims } = e.data;

  if (type === "cancel") {
    cancelled.add(paperId);
    return;
  }

  if (type === "resolve") {
    // Check if already cancelled
    if (cancelled.has(paperId)) {
      cancelled.delete(paperId);
      return;
    }

    const anchors: Array<{ claim: string; start: number; end: number }> = [];

    for (const claim of claims) {
      // Check cancellation between claims
      if (cancelled.has(paperId)) {
        cancelled.delete(paperId);
        return;
      }

      const match = findFuzzyAnchor(abstract, claim);
      if (match) {
        anchors.push({
          claim,
          start: match.start,
          end: match.end,
        });
      } else {
        anchors.push({ claim, start: -1, end: -1 });
      }
    }

    self.postMessage({ type: "resolved", paperId, anchors });
  }
};
