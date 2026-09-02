/**
 * Levenshtein distance between two strings.
 * Used for fuzzy anchor matching in the Web Worker.
 */
export function levenshtein(a: string, b: string): number {
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;

  const matrix: number[][] = [];

  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i];
  }
  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j;
  }

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

/**
 * Normalized Levenshtein similarity (0-1, where 1 is identical).
 */
export function levenshteinSimilarity(a: string, b: string): number {
  const maxLen = Math.max(a.length, b.length);
  if (maxLen === 0) return 1;
  return 1 - levenshtein(a, b) / maxLen;
}

/**
 * Find the best fuzzy match of a claim within an abstract.
 * Returns the start/end character offsets of the best match.
 */
export function findFuzzyAnchor(
  abstract: string,
  claim: string,
  threshold: number = 0.7,
): { start: number; end: number; similarity: number } | null {
  if (!abstract || !claim) return null;

  const claimLen = claim.length;
  const abstractLower = abstract.toLowerCase();
  const claimLower = claim.toLowerCase();

  // Sliding window approach: check windows of claim-length in the abstract
  const windowStep = Math.max(1, Math.floor(claimLen / 4));
  let bestMatch: { start: number; end: number; similarity: number } | null = null;

  for (let i = 0; i <= abstract.length - claimLen; i += windowStep) {
    const window = abstractLower.substring(i, i + claimLen);
    const similarity = levenshteinSimilarity(claimLower, window);

    if (similarity >= threshold) {
      // Refine: expand window to find best local match
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

  // Also try exact substring match first
  const exactIndex = abstractLower.indexOf(claimLower);
  if (exactIndex !== -1) {
    return { start: exactIndex, end: exactIndex + claimLen, similarity: 1 };
  }

  return bestMatch;
}
