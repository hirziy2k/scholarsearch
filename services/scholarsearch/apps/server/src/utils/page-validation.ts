// ============================================
// Page Payload Validation
// ============================================
// Validates raw API response payloads before they touch the ORM layer.
// Prevents poisoned cache from truncated or malformed responses.

export interface PageValidationResult {
  valid: boolean;
  reason?: string;
  truncated?: boolean;
}

const PAGE_SIZE = 10; // Matches default maxResults in mcp-server

export function validatePagePayload(
  results: any[],
  pageNumber: number,
  hitCount: number,
  pageSize: number = PAGE_SIZE,
): PageValidationResult {
  // Final page is exempt from length check
  const isFinalPage =
    results.length <= pageSize &&
    pageNumber * pageSize >= hitCount;

  // Empty results on page 1 = source unavailable
  if (results.length === 0 && pageNumber === 1) {
    return {
      valid: false,
      reason: "Empty first page — source may be unavailable",
    };
  }

  // Structural check FIRST: each result must have at least a title or DOI
  for (const r of results) {
    if (!r.title && !r.Title && !r.doi && !r.DOI && !r.externalIds?.DOI) {
      return {
        valid: false,
        reason: "Result missing both title and DOI — corrupted payload",
      };
    }
  }

  // Truncation check: non-final page with significantly fewer results than expected
  // Only flag as truncated if less than 50% of expected (allows for natural variation)
  if (!isFinalPage && results.length < pageSize * 0.5) {
    return {
      valid: false,
      reason: `Truncated page: received ${results.length} results, expected ${pageSize}`,
      truncated: true,
    };
  }

  return { valid: true };
}
