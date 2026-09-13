/**
 * Deterministic DOI Batch Verification with Abstract Hash-Diff
 * 
 * Checks for retractions and silent corrections by:
 * 1. Batch-querying Crossref + OpenAlex for current metadata
 * 2. Hashing fetched abstracts against manifest cached abstracts
 * 3. Flagging mismatches as "Unannounced Revision/Erratum"
 * 
 * Never re-executes broad AST queries — uses deterministic DOI lookups only.
 */

import { createHash } from "crypto";
import { CrossrefClient, OpenAlexClient } from "@scholarsearch/mcp-sources";

// ============================================
// Types
// ============================================

export interface ManifestPaper {
  paperId: string;
  doi: string;
  title: string;
  abstractHash: string;
  cachedAbstract: string;
}

export interface DOIVerificationResult {
  verified: number;
  retracted: Array<{
    doi: string;
    retractedBy?: string;
    notice: string;
  }>;
  unannouncedRevisions: Array<{
    doi: string;
    title: string;
    abstractDiff: { oldHash: string; newHash: string };
  }>;
  metadataUpdated: Array<{
    doi: string;
    field: string;
    oldValue: string;
    newValue: string;
  }>;
  notFound: string[];
  timestamp: string;
}

// ============================================
// Abstract Hashing
// ============================================

/**
 * Compute SHA-256 hash of abstract text.
 * Used for manifest creation and comparison.
 */
export function hashAbstract(abstract: string): string {
  if (!abstract) return "";
  return createHash("sha256").update(abstract.trim().toLowerCase()).digest("hex");
}

// ============================================
// DOI Verification
// ============================================

const crossref = new CrossrefClient();
const openalex = new OpenAlexClient();

/**
 * Batch verify DOIs against live API data.
 * Detects retractions, silent revisions, and metadata updates.
 */
export async function verifyDOIs(
  papers: ManifestPaper[],
): Promise<DOIVerificationResult> {
  const result: DOIVerificationResult = {
    verified: 0,
    retracted: [],
    unannouncedRevisions: [],
    metadataUpdated: [],
    notFound: [],
    timestamp: new Date().toISOString(),
  };

  if (papers.length === 0) return result;

  const dois = papers.map(p => p.doi.toLowerCase());
  const paperMap = new Map(papers.map(p => [p.doi.toLowerCase(), p]));

  // Batch query both sources
  const [crossrefResults, openalexResults] = await Promise.all([
    crossref.batchResolveDois(dois),
    openalex.batchResolveDois(dois),
  ]);

  for (const doi of dois) {
    const manifest = paperMap.get(doi);
    if (!manifest) continue;

    const crossrefData = crossrefResults[doi];
    const openalexData = openalexResults[doi];

    // Check if DOI exists in any source
    if (!crossrefData && !openalexData) {
      result.notFound.push(doi);
      continue;
    }

    // Check for retraction
    const isRetracted = checkRetraction(crossrefData, openalexData);
    if (isRetracted) {
      result.retracted.push({
        doi,
        retractedBy: isRetracted.retractedBy,
        notice: isRetracted.notice,
      });
      continue;
    }

    // Check for abstract hash mismatch (silent revision)
    const newAbstract = extractAbstract(crossrefData, openalexData);
    if (newAbstract && manifest.cachedAbstract) {
      const newHash = hashAbstract(newAbstract);
      if (newHash !== manifest.abstractHash && newHash !== "") {
        result.unannouncedRevisions.push({
          doi,
          title: manifest.title,
          abstractDiff: {
            oldHash: manifest.abstractHash,
            newHash,
          },
        });
        continue;
      }
    }

    // Check for metadata updates
    const metaUpdates = checkMetadataUpdates(doi, crossrefData, openalexData, manifest);
    if (metaUpdates.length > 0) {
      result.metadataUpdated.push(...metaUpdates);
      continue;
    }

    result.verified++;
  }

  return result;
}

// ============================================
// Helper Functions
// ============================================

interface RetractionCheck {
  retractedBy?: string;
  notice: string;
}

function checkRetraction(
  crossrefData: Record<string, any> | undefined,
  openalexData: Record<string, any> | undefined,
): RetractionCheck | null {
  if (crossrefData) {
    const type = crossrefData.type?.toLowerCase() ?? "";
    if (type.includes("retraction")) {
      return {
        notice: `Crossref type: ${crossrefData.type}`,
      };
    }

    const title = (crossrefData.title?.[0] ?? "").toLowerCase();
    if (title.includes("retraction") || title.includes("retracted")) {
      return {
        notice: "Retraction keyword in title",
      };
    }
  }

  if (openalexData) {
    const type = openalexData.type?.toLowerCase() ?? "";
    if (type.includes("retraction")) {
      return {
        notice: `OpenAlex type: ${openalexData.type}`,
      };
    }
  }

  return null;
}

function extractAbstract(
  crossrefData: Record<string, any> | undefined,
  openalexData: Record<string, any> | undefined,
): string | null {
  if (crossrefData?.abstract) {
    return crossrefData.abstract.replace(/<[^>]*>/g, "").trim();
  }

  if (openalexData?.abstract_inverted_index) {
    return decodeOpenAlexAbstract(openalexData.abstract_inverted_index);
  }

  return null;
}

function decodeOpenAlexAbstract(invertedIndex: Record<string, number[]>): string {
  if (!invertedIndex || typeof invertedIndex !== "object") return "";

  const words: Array<{ word: string; position: number }> = [];

  for (const [word, positions] of Object.entries(invertedIndex)) {
    if (!Array.isArray(positions)) continue;
    for (const pos of positions) {
      words.push({ word, position: pos });
    }
  }

  words.sort((a, b) => a.position - b.position);
  return words.map(w => w.word).join(" ");
}

function checkMetadataUpdates(
  doi: string,
  crossrefData: Record<string, any> | undefined,
  openalexData: Record<string, any> | undefined,
  manifest: ManifestPaper,
): Array<{ doi: string; field: string; oldValue: string; newValue: string }> {
  const updates: Array<{ doi: string; field: string; oldValue: string; newValue: string }> = [];
  // Future: compare specific metadata fields
  return updates;
}
