/**
 * Proprietary Metadata ZIP Archive Generator
 * 
 * Generates a ZIP file containing ONLY ScholarSearch-generated metadata:
 * - session.scholarsearch (JSON manifest)
 * - references.ris (RIS file with L1 PDF tags)
 * - index.html (HTML summary)
 * - prisma-flowchart.txt (PRISMA-2020 funnel)
 * 
 * NEVER contains PDF binaries. PDFs are accessed via L1 tags in RIS
 * through Zotero/EndNote which handle batch downloading locally.
 */

import { generateRIS } from "./ris-export";

// ============================================
// Minimal ZIP Builder (no dependencies)
// ============================================

interface ZIPEntry {
  name: string;
  data: Uint8Array;
}

function crc32(data: Uint8Array): number {
  let crc = 0xFFFFFFFF;
  const table = new Uint32Array(256);

  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c;
  }

  for (let i = 0; i < data.length; i++) {
    crc = table[(crc ^ data[i]) & 0xFF] ^ (crc >>> 8);
  }

  return (crc ^ 0xFFFFFFFF) >>> 0;
}

function stringToBytes(str: string): Uint8Array {
  return new TextEncoder().encode(str);
}

function buildLocalFileHeader(entry: ZIPEntry, offset: number): Uint8Array {
  const nameBytes = stringToBytes(entry.name);
  const header = new Uint8Array(30 + nameBytes.length);
  const view = new DataView(header.buffer);

  view.setUint32(0, 0x04034b50, true); // Signature
  view.setUint16(4, 20, true); // Version needed
  view.setUint16(6, 0, true); // Flags
  view.setUint16(8, 0, true); // Compression: stored
  view.setUint16(10, 0, true); // Mod time
  view.setUint16(12, 0, true); // Mod date
  view.setUint32(14, crc32(entry.data), true); // CRC-32
  view.setUint32(18, entry.data.length, true); // Compressed size
  view.setUint32(22, entry.data.length, true); // Uncompressed size
  view.setUint16(26, nameBytes.length, true); // Name length
  view.setUint16(28, 0, true); // Extra field length

  header.set(nameBytes, 30);
  return header;
}

function buildCentralDirectoryEntry(entry: ZIPEntry, offset: number): Uint8Array {
  const nameBytes = stringToBytes(entry.name);
  const header = new Uint8Array(46 + nameBytes.length);
  const view = new DataView(header.buffer);

  view.setUint32(0, 0x02014b50, true); // Signature
  view.setUint16(4, 20, true); // Version made by
  view.setUint16(6, 20, true); // Version needed
  view.setUint16(8, 0, true); // Flags
  view.setUint16(10, 0, true); // Compression: stored
  view.setUint16(12, 0, true); // Mod time
  view.setUint16(14, 0, true); // Mod date
  view.setUint32(16, crc32(entry.data), true); // CRC-32
  view.setUint32(20, entry.data.length, true); // Compressed size
  view.setUint32(24, entry.data.length, true); // Uncompressed size
  view.setUint16(28, nameBytes.length, true); // Name length
  view.setUint16(30, 0, true); // Extra field length
  view.setUint16(32, 0, true); // File comment length
  view.setUint16(34, 0, true); // Disk number start
  view.setUint16(36, 0, true); // Internal file attributes
  view.setUint32(38, 0, true); // External file attributes
  view.setUint32(42, offset, true); // Relative offset of local header

  header.set(nameBytes, 46);
  return header;
}

function buildEndOfCentralDirectory(entryCount: number, cdSize: number, cdOffset: number): Uint8Array {
  const eocd = new Uint8Array(22);
  const view = new DataView(eocd.buffer);

  view.setUint32(0, 0x06054b50, true); // Signature
  view.setUint16(4, 0, true); // Disk number
  view.setUint16(6, 0, true); // Disk with central directory
  view.setUint16(8, entryCount, true); // Entries on this disk
  view.setUint16(10, entryCount, true); // Total entries
  view.setUint32(12, cdSize, true); // Central directory size
  view.setUint32(16, cdOffset, true); // Central directory offset
  view.setUint16(20, 0, true); // Comment length

  return eocd;
}

function buildZIP(entries: ZIPEntry[]): Blob {
  const parts: Uint8Array[] = [];
  const centralEntries: Uint8Array[] = [];
  let offset = 0;

  for (const entry of entries) {
    const localHeader = buildLocalFileHeader(entry, offset);
    parts.push(localHeader);
    parts.push(entry.data);

    const centralEntry = buildCentralDirectoryEntry(entry, offset);
    centralEntries.push(centralEntry);

    offset += localHeader.length + entry.data.length;
  }

  const cdOffset = offset;
  let cdSize = 0;
  for (const ce of centralEntries) {
    parts.push(ce);
    cdSize += ce.length;
  }

  const eocd = buildEndOfCentralDirectory(entries.length, cdSize, cdOffset);
  parts.push(eocd);

  // Convert Uint8Arrays to ArrayBuffer for Blob compatibility
  const blobParts: ArrayBuffer[] = [];
  for (const part of parts) {
    const buf = new ArrayBuffer(part.byteLength);
    new Uint8Array(buf).set(part);
    blobParts.push(buf);
  }
  return new Blob(blobParts, { type: "application/zip" });
}

// ============================================
// PRISMA Flowchart Generator
// ============================================

function generatePRISMAFlowchart(state: {
  results: any[];
  exclusions: any[];
  promotedPapers: any[];
  shadowMergeFlags: any[];
  totalRaw: number;
  duplicatesRemoved: number;
}): string {
  const { results, exclusions, promotedPapers, shadowMergeFlags, totalRaw, duplicatesRemoved } = state;

  // Count records per source from all results (before dedup)
  const sourceCounts: Record<string, number> = {};
  for (const paper of results) {
    const source = paper._source ?? paper.source ?? "unknown";
    sourceCounts[source] = (sourceCounts[source] ?? 0) + 1;
  }

  // Count shadow merge records (additional physical records per merged card)
  let shadowCount = 0;
  for (const flag of shadowMergeFlags) {
    shadowCount++;
  }

  const totalScreened = results.length;
  const taExclusions = exclusions.filter((e: any) => e.phase === "ta");
  const fullTextExclusions = exclusions.filter((e: any) => e.phase === "fulltext");
  const taExclusionCount = taExclusions.reduce((sum: number, e: any) => sum + (e.sourceRecords?.length ?? 1), 0);
  const fullTextExclusionCount = fullTextExclusions.reduce((sum: number, e: any) => sum + (e.sourceRecords?.length ?? 1), 0);
  const promotedCount = promotedPapers.length;
  const includedCount = promotedCount - fullTextExclusions.length;

  const lines = [
    "PRISMA-2020 Flowchart",
    "=====================",
    "",
    "Records identified:",
  ];

  for (const [source, count] of Object.entries(sourceCounts).sort((a, b) => b[1] - a[1])) {
    lines.push(`  ${source} (n=${count})`);
  }

  lines.push(
    "",
    `Records removed before screening:`,
    `  Duplicate records removed (n=${duplicatesRemoved})`,
    `  Shadow merge records (n=${shadowCount})`,
    "",
    `Records screened (T/A phase):`,
    `  Total records (n=${totalScreened})`,
    `  Excluded at T/A (n=${taExclusionCount})`,
    `  Promoted to Full-Text (n=${promotedCount})`,
    "",
    `Full-Text Review:`,
    `  Assessed for eligibility (n=${promotedCount})`,
    `  Excluded at Full-Text (n=${fullTextExclusionCount})`,
    "",
    `Included in review:`,
    `  Final included (n=${Math.max(0, includedCount)})`,
  );

  // List exclusion reasons
  if (taExclusions.length > 0 || fullTextExclusions.length > 0) {
    lines.push("", "Exclusion reasons:");
    const reasonCounts: Record<string, number> = {};
    for (const e of [...taExclusions, ...fullTextExclusions]) {
      reasonCounts[e.reason] = (reasonCounts[e.reason] ?? 0) + 1;
    }
    for (const [reason, count] of Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])) {
      lines.push(`  ${reason} (n=${count})`);
    }
  }

  return lines.join("\n");
}

// ============================================
// HTML Index Generator
// ============================================

function generateIndexHTML(state: {
  query: string;
  mode: string;
  results: any[];
  bookmarks: any[];
  exclusions: any[];
  promotedPapers: any[];
  gapAnalysis: any;
}): string {
  const { query, mode, results, bookmarks, exclusions, promotedPapers, gapAnalysis } = state;

  const getPdfUrl = (paper: any): string | null => {
    if (paper.openAccessPdf?.url) return paper.openAccessPdf.url;
    if (paper.fullTextUrl) return paper.fullTextUrl;
    return null;
  };

  const papersHTML = results.map((paper) => {
    const title = paper.title ?? "Untitled";
    const authors = (paper.authors ?? paper.authorships ?? []).slice(0, 3).map((a: any) =>
      typeof a === "string" ? a : (a.name ?? a.display_name ?? `${a.given ?? ""} ${a.family ?? ""}`.trim())
    ).join(", ");
    const year = paper.year ?? paper.pubYear ?? "";
    const doi = paper.DOI ?? paper.doi ?? "";
    const pdfUrl = getPdfUrl(paper);

    return `
    <div style="margin-bottom: 24px; padding: 16px; border: 1px solid #E8E8E6; border-radius: 8px;">
      <h3 style="margin: 0 0 8px 0; font-size: 16px;">
        ${doi ? `<a href="https://doi.org/${doi}">${title}</a>` : title}
      </h3>
      <p style="margin: 0 0 4px 0; color: #6B6B6B; font-size: 14px;">${authors} · ${year}</p>
      <p style="margin: 0; font-family: monospace; font-size: 12px; color: #9A9A9A;">${doi}</p>
      ${pdfUrl ? `<p style="margin: 8px 0 0 0;"><a href="${pdfUrl}">Download PDF</a></p>` : ""}
    </div>`;
  }).join("\n");

  const gapsHTML = gapAnalysis?.gaps?.length > 0
    ? `<h2>Research Gap Analysis</h2>
       <p>${gapAnalysis.bannerText ?? ""}</p>
       <ul>${gapAnalysis.gaps.map((g: any) => `<li><strong>${g.missing}</strong>: ${g.suggestion}</li>`).join("\n")}</ul>`
    : "";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ScholarSearch Session: ${query}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 0 auto; padding: 24px; color: #1A1A1A; }
    h1 { font-size: 24px; margin-bottom: 8px; }
    h2 { font-size: 20px; margin-top: 32px; margin-bottom: 16px; }
    .meta { color: #6B6B6B; font-size: 14px; margin-bottom: 24px; }
    .stats { display: flex; gap: 16px; margin-bottom: 24px; }
    .stat { padding: 12px; border: 1px solid #E8E8E6; border-radius: 8px; }
    .stat-value { font-size: 24px; font-weight: 600; }
    .stat-label { font-size: 12px; color: #9A9A9A; }
    a { color: #1A1A1A; }
  </style>
</head>
<body>
  <h1>ScholarSearch Session</h1>
  <div class="meta">
    <p>Query: <strong>${query}</strong> | Mode: <strong>${mode}</strong></p>
    <p>Exported: ${new Date().toISOString()}</p>
  </div>

  <div class="stats">
    <div class="stat">
      <div class="stat-value">${results.length}</div>
      <div class="stat-label">Papers</div>
    </div>
    <div class="stat">
      <div class="stat-value">${bookmarks.length}</div>
      <div class="stat-label">Bookmarked</div>
    </div>
    <div class="stat">
      <div class="stat-value">${exclusions.length}</div>
      <div class="stat-label">Excluded</div>
    </div>
    <div class="stat">
      <div class="stat-value">${promotedPapers.length}</div>
      <div class="stat-label">Promoted</div>
    </div>
  </div>

  <h2>Papers</h2>
  ${papersHTML}

  ${gapsHTML}

  <hr style="margin: 32px 0; border: none; border-top: 1px solid #E8E8E6;">
  <p style="color: #9A9A9A; font-size: 12px;">
    Generated by ScholarSearch. PDFs are not included in this archive.
    Use the references.ris file with Zotero or EndNote to batch-download PDFs
    through your institutional access.
  </p>
</body>
</html>`;
}

// ============================================
// Main Export Function
// ============================================

interface ArchiveState {
  query: string;
  mode: string;
  results: any[];
  bookmarks: any[];
  validations: any[];
  exclusions: any[];
  promotedPapers: any[];
  shadowMergeFlags: any[];
  gapAnalysis: any;
  lastQuery: string;
  lastMode: string;
  lastWeights: any;
  totalRaw: number;
  duplicatesRemoved: number;
  queryVersionHash?: any;
}

/**
 * Generate a proprietary metadata ZIP archive.
 * Contains RIS, manifest, HTML index, and PRISMA flowchart.
 * NO PDFs.
 */
export function generateArchive(state: ArchiveState): Blob {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");

  // 1. RIS file
  const ris = generateRIS(state.results);
  const risEntry: ZIPEntry = { name: "references.ris", data: stringToBytes(ris) };

  // 2. Session manifest
  const manifest = {
    version: "1.0",
    createdAt: new Date().toISOString(),
    queryParameters: {
      raw_query: state.lastQuery,
      mode: state.lastMode,
      weights: state.lastWeights,
    },
    queryVersionHash: state.queryVersionHash ?? null,
    papers: state.results.map((p: any) => ({
      paperId: p.id ?? p.doi ?? `${p.title}-${p.source}`,
      doi: p.DOI ?? p.doi ?? null,
      title: p.title,
      source: p._source ?? p.source,
    })),
    bookmarks: state.bookmarks,
    validations: state.validations,
    exclusions: state.exclusions,
    promotedPapers: state.promotedPapers,
    gapAnalysis: state.gapAnalysis,
  };
  const manifestEntry: ZIPEntry = {
    name: "session.scholarsearch",
    data: stringToBytes(JSON.stringify(manifest, null, 2)),
  };

  // 3. HTML index
  const html = generateIndexHTML(state);
  const htmlEntry: ZIPEntry = { name: "index.html", data: stringToBytes(html) };

  // 4. PRISMA flowchart
  const prisma = generatePRISMAFlowchart({
    results: state.results,
    exclusions: state.exclusions,
    promotedPapers: state.promotedPapers,
    shadowMergeFlags: state.shadowMergeFlags,
    totalRaw: state.totalRaw,
    duplicatesRemoved: state.duplicatesRemoved,
  });
  const prismaEntry: ZIPEntry = { name: "prisma-flowchart.txt", data: stringToBytes(prisma) };

  // Build ZIP
  return buildZIP([risEntry, manifestEntry, htmlEntry, prismaEntry]);
}

/**
 * Trigger download of the archive ZIP.
 */
export function downloadArchive(state: ArchiveState): void {
  const blob = generateArchive(state);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `scholarsearch-${state.lastQuery}-${Date.now()}.zip`;
  a.click();
  URL.revokeObjectURL(url);
}
