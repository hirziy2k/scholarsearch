/**
 * RIS Export Generator
 * 
 * Generates RIS (Research Information Systems) format files from ScholarSearch results.
 * RIS is the universal exchange format for reference managers (Zotero, Mendeley, EndNote).
 * 
 * Includes L1 tags (PDF URLs) so Zotero can batch-download PDFs locally
 * through the user's institutional VPN.
 */

interface Paper {
  [key: string]: any;
}

interface RISExportOptions {
  papers: Paper[];
  filename?: string;
}

/**
 * Extract authors from a paper in a format suitable for RIS AU tags.
 */
function extractAuthors(paper: Paper): string[] {
  const authors = paper.authors ?? paper.authorships ?? paper.author ?? [];
  if (!Array.isArray(authors) || authors.length === 0) return [];

  return authors.map((a: any) => {
    if (typeof a === "string") return a;
    const given = a.given ?? a.firstName ?? "";
    const family = a.family ?? a.lastName ?? "";
    const name = a.name ?? a.Name ?? a.display_name ?? "";

    if (given && family) return `${family}, ${given}`;
    if (name) return name;
    return "Unknown";
  });
}

/**
 * Extract the primary title from a paper.
 */
function getTitle(paper: Paper): string {
  const t = paper.title;
  if (Array.isArray(t) && t.length > 0) return t[0]!;
  if (typeof t === "string") return t;
  return paper.Title ?? "Untitled";
}

/**
 * Extract the journal/container title.
 */
function getJournal(paper: Paper): string {
  return paper.journal ?? paper.containerTitle ?? paper.container_title ?? paper.journalName ?? "";
}

/**
 * Extract keywords from a paper.
 */
function getKeywords(paper: Paper): string[] {
  if (Array.isArray(paper.keywords)) return paper.keywords;
  if (Array.isArray(paper.subject)) return paper.subject;
  if (typeof paper.keywords === "string") return paper.keywords.split(/[;,]/).map((s: string) => s.trim());
  return [];
}

/**
 * Get the best PDF URL for a paper.
 * Priority: openAccessPdf.url > fullTextUrl > doiUrl
 */
function getPdfUrl(paper: Paper): string | null {
  if (paper.openAccessPdf?.url) return paper.openAccessPdf.url;
  if (paper.fullTextUrl) return paper.fullTextUrl;
  return null;
}

/**
 * Get the DOI URL for a paper.
 */
function getDoiUrl(paper: Paper): string | null {
  const doi = paper.DOI ?? paper.doi ?? null;
  return doi ? `https://doi.org/${doi}` : null;
}

/**
 * Escape special RIS characters.
 * RIS uses semicolons as tag delimiters in some fields.
 */
function escapeRIS(text: string): string {
  return text.replace(/\n/g, " ").replace(/\r/g, "");
}

/**
 * Generate a single RIS record for a paper.
 */
function generateRISRecord(paper: Paper): string {
  const lines: string[] = [];

  // Type — default to journal article
  lines.push(`TY  - ${paper.type === "journal-article" ? "JOUR" : paper.publicationType ?? "JOUR"}`);

  // Title
  lines.push(`TI  - ${escapeRIS(getTitle(paper))}`);

  // Authors
  const authors = extractAuthors(paper);
  for (const author of authors) {
    lines.push(`AU  - ${escapeRIS(author)}`);
  }

  // Year
  const year = paper.year ?? paper.pubYear ?? paper.publication_year;
  if (year) {
    lines.push(`PY  - ${year}`);
  }

  // DOI
  const doi = paper.DOI ?? paper.doi ?? null;
  if (doi) {
    lines.push(`DO  - ${doi}`);
  }

  // Journal
  const journal = getJournal(paper);
  if (journal) {
    lines.push(`JO  - ${escapeRIS(journal)}`);
    lines.push(`TA  - ${escapeRIS(journal)}`);
  }

  // Volume, Issue, Pages
  if (paper.volume) lines.push(`VL  - ${paper.volume}`);
  if (paper.issue) lines.push(`IS  - ${paper.issue}`);
  if (paper.pages) {
    const pages = typeof paper.pages === "string" ? paper.pages : `${paper.pages}`;
    lines.push(`SP  - ${pages}`);
  }

  // Abstract
  if (paper.abstract) {
    lines.push(`AB  - ${escapeRIS(paper.abstract)}`);
  }

  // Keywords
  const keywords = getKeywords(paper);
  for (const kw of keywords) {
    if (kw) lines.push(`KW  - ${escapeRIS(kw)}`);
  }

  // PDF URL (L1 tag — Zotero reads this for batch download)
  const pdfUrl = getPdfUrl(paper);
  if (pdfUrl) {
    lines.push(`L1  - ${pdfUrl}`);
  }

  // DOI URL (L2 tag — fallback for reference managers)
  const doiUrl = getDoiUrl(paper);
  if (doiUrl) {
    lines.push(`L2  - ${doiUrl}`);
    lines.push(`UR  - ${doiUrl}`);
  }

  // Publisher
  if (paper.publisher) {
    lines.push(`PB  - ${escapeRIS(paper.publisher)}`);
  }

  // End of record
  lines.push("ER  - ");

  return lines.join("\n");
}

/**
 * Generate a complete RIS file from search results.
 */
export function generateRIS(papers: Paper[]): string {
  const records = papers.map(generateRISRecord);
  return records.join("\n\n");
}

/**
 * Trigger a download of the RIS file.
 */
export function downloadRIS(papers: Paper[], filename?: string): void {
  const ris = generateRIS(papers);
  const blob = new Blob([ris], { type: "application/x-research-info-systems" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename ?? `scholarsearch-references-${Date.now()}.ris`;
  a.click();
  URL.revokeObjectURL(url);
}
