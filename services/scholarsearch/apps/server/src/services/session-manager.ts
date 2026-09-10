// ============================================
// Session Manager
// ============================================
// Creates and manages search sessions in SQLite.
// Handles session creation, page storage, status updates,
// and TTL-based cleanup.

import { getDb } from "../db.js";
import { v4 as uuidv4 } from "uuid";

const DEFAULT_PAGE_SIZE = 10;
const SESSION_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

export interface CreateSessionInput {
  rawQuery: string;
  mode: string;
  methodology?: "systematic" | "exploratory";
  region?: string;
  filters?: Record<string, any>;
  weights?: Record<string, any>;
  sources?: string[];
  sourceHits?: Record<string, number>; // { openalex: 87, pubmed: 64, ... }
}

export async function createSession(input: CreateSessionInput) {
  const db = getDb();
  const searchId = uuidv4();

  const sourceStatuses = (input.sources ?? []).map((source) => ({
    source,
    status: "pending",
    resultCount: 0,
    hitCount: input.sourceHits?.[source] ?? 0,
    error: null,
  }));

  const totalPages = Object.values(input.sourceHits ?? {}).reduce(
    (sum, hits) => sum + Math.ceil(hits / DEFAULT_PAGE_SIZE),
    0,
  );

  const session = await db.searchSession.create({
    data: {
      searchId,
      rawQuery: input.rawQuery,
      mode: input.mode,
      methodology: input.methodology ?? null,
      region: input.region ?? null,
      filters: input.filters ? JSON.stringify(input.filters) : null,
      weights: input.weights ? JSON.stringify(input.weights) : null,
      status: "partial",
      sourceStatuses: JSON.stringify(sourceStatuses),
      totalPages,
      fetchedPages: 0,
      expiresAt: new Date(Date.now() + SESSION_TTL_MS),
    },
  });

  return session;
}

export async function getSession(searchId: string) {
  const db = getDb();
  return db.searchSession.findFirst({ where: { searchId } });
}

export async function getPages(searchId: string, source?: string) {
  const db = getDb();
  const session = await db.searchSession.findFirst({ where: { searchId } });
  if (!session) return null;

  const where: any = { sessionId: session.id };
  if (source) where.source = source;

  return db.searchPage.findMany({
    where,
    orderBy: [{ source: "asc" }, { pageNumber: "asc" }],
  });
}

export async function getPage(
  sessionId: string,
  source: string,
  pageNumber: number,
) {
  const db = getDb();
  return db.searchPage.findUnique({
    where: {
      sessionId_source_pageNumber: { sessionId, source, pageNumber },
    },
  });
}

export async function writePage(
  sessionId: string,
  source: string,
  pageNumber: number,
  rawResults: any[],
  hitCount: number,
) {
  const db = getDb();
  try {
    await db.searchPage.create({
      data: {
        sessionId,
        source,
        pageNumber,
        rawResults: JSON.stringify(rawResults),
        hitCount,
      },
    });
    return true;
  } catch (e: any) {
    if (e.code === "P2002") {
      // Unique constraint violation — another request already wrote this page.
      // Immutable insert: first write wins, duplicate silently discarded.
      return false;
    }
    throw e;
  }
}

export async function updateSessionStatus(
  searchId: string,
  status: "partial" | "complete" | "failed",
) {
  const db = getDb();
  return db.searchSession.update({
    where: { searchId },
    data: { status },
  });
}

export async function updateSourceStatus(
  searchId: string,
  source: string,
  update: { status?: string; resultCount?: number; error?: string },
) {
  const db = getDb();
  const session = await db.searchSession.findFirst({ where: { searchId } });
  if (!session) return;

  const statuses = JSON.parse(session.sourceStatuses) as any[];
  const idx = statuses.findIndex((s: any) => s.source === source);
  if (idx === -1) return;

  if (update.status) statuses[idx].status = update.status;
  if (update.resultCount !== undefined) statuses[idx].resultCount = update.resultCount;
  if (update.error) statuses[idx].error = update.error;

  await db.searchSession.update({
    where: { searchId },
    data: {
      sourceStatuses: JSON.stringify(statuses),
      fetchedPages: session.fetchedPages + 1,
    },
  });
}

export async function cleanupExpiredSessions() {
  const db = getDb();
  const deleted = await db.searchSession.deleteMany({
    where: {
      expiresAt: { lt: new Date() },
    },
  });
  return deleted.count;
}
