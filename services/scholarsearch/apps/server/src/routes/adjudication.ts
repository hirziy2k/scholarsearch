import type { FastifyInstance } from "fastify";
import { getDb } from "../db.js";
import { extractTrialIds } from "../services/metadata-verification.js";
import { verifyTrialRegistrations, getCTGovCircuitStatus } from "../services/ctgov-verifier.js";
import { applyEquityOverride, isRegionalRegistry } from "../services/geo-equity-override.js";

export async function adjudicationRoutes(app: FastifyInstance) {
  /**
   * POST /api/search/:searchId/paper/:paperId/adjudicate
   *
   * Handles researcher adjudication of papers with regional/unverified evidence.
   * Actions: confirm | exclude | flag_for_review
   *
   * Stores the decision in the AuditLog and updates the paper's metadata
   * for downstream export gating.
   */
  app.post<{
    Params: { searchId: string; paperId: string };
    Body: {
      action: "confirm" | "exclude" | "flag_for_review";
      reason?: string;
      researcherNote?: string;
    };
  }>("/search/:searchId/paper/:paperId/adjudicate", async (request, reply) => {
    const { searchId, paperId } = request.params;
    const { action, reason, researcherNote } = request.body;

    if (!["confirm", "exclude", "flag_for_review"].includes(action)) {
      return reply.status(400).send({
        error: "Invalid action. Must be: confirm | exclude | flag_for_review",
      });
    }

    const db = getDb();

    // Verify session exists
    const session = await db.searchSession.findFirst({ where: { searchId } });
    if (!session) {
      return reply.status(404).send({ error: "Session not found" });
    }

    // Verify paper exists in this session
    const paper = await db.searchResult.findFirst({
      where: { id: paperId, sessionId: session.id },
    });
    if (!paper) {
      return reply.status(404).send({ error: "Paper not found in this session" });
    }

    // Extract trial IDs from the paper's metadata
    const trialIds = extractTrialIds({
      title: paper.title,
      abstract: paper.abstract ?? undefined,
      keywords: JSON.parse(paper.keywords),
    });

    // Verify with CT.gov if NCT IDs present
    const ctgovResults = await verifyTrialRegistrations(trialIds, paper.title);

    // Check regional registry status
    const fromRegional = trialIds.some((t) => isRegionalRegistry(t.registry));

    // Apply equity override to current scores
    const currentScores = JSON.parse(paper.rankingScores);
    const equityResult = applyEquityOverride({
      country: paper.country ?? undefined,
      publisherCountry: paper.publisher ?? undefined,
      trialVerified: ctgovResults.some((r) => r.verificationStatus === "verified"),
      fromRegionalRegistry: fromRegional,
      currentScores,
      userRegion: session.region ?? undefined,
    });

    // Record adjudication in audit log
    await db.auditLog.create({
      data: {
        action: "adjudicate",
        details: JSON.stringify({
          sessionId: searchId,
          paperId,
          paperTitle: paper.title.substring(0, 100),
          action,
          reason: reason ?? null,
          researcherNote: researcherNote ?? null,
          trialIds: trialIds.map((t) => ({ registry: t.registry, id: t.id })),
          ctgovResults: ctgovResults.map((r) => ({
            nctId: r.nctId,
            status: r.verificationStatus,
            titleMatch: r.titleMatch,
          })),
          equityOverride: {
            applied: equityResult.overrideApplied,
            reason: equityResult.reason,
            regions: equityResult.triggeredRegions,
          },
        }),
        source: "adjudication",
        success: true,
      },
    });

    // Update paper scores if equity override was applied
    if (equityResult.overrideApplied) {
      await db.searchResult.update({
        where: { id: paperId },
        data: {
          rankingScores: JSON.stringify(equityResult.adjustedScores),
        },
      });
    }

    return reply.send({
      adjudication: {
        paperId,
        action,
        trialRegistration: {
          ids: trialIds.map((t) => ({ registry: t.registry, id: t.id })),
          ctgovVerification: ctgovResults.map((r) => ({
            nctId: r.nctId,
            found: r.found,
            titleMatch: r.titleMatch,
            status: r.verificationStatus,
          })),
        },
        equityOverride: {
          applied: equityResult.overrideApplied,
          reason: equityResult.reason,
          regions: equityResult.triggeredRegions,
          adjustedScores: equityResult.overrideApplied
            ? equityResult.adjustedScores
            : null,
        },
        circuitStatus: getCTGovCircuitStatus(),
      },
    });
  });

  /**
   * GET /api/search/:searchId/verification-summary
   *
   * Returns a summary of verification status across all papers in a session.
   * Used by the frontend to display regional triage badges.
   */
  app.get<{
    Params: { searchId: string };
  }>("/search/:searchId/verification-summary", async (request, reply) => {
    const { searchId } = request.params;
    const db = getDb();

    const session = await db.searchSession.findFirst({ where: { searchId } });
    if (!session) {
      return reply.status(404).send({ error: "Session not found" });
    }

    const papers = await db.searchResult.findMany({
      where: { sessionId: session.id },
      select: {
        id: true,
        title: true,
        doi: true,
        country: true,
        keywords: true,
        rankingScores: true,
      },
    });

    let verified = 0;
    let unverified = 0;
    let regional = 0;
    let withTrialIds = 0;

    for (const paper of papers) {
      const trialIds = extractTrialIds({
        title: paper.title,
        keywords: JSON.parse(paper.keywords),
      });

      if (trialIds.length > 0) {
        withTrialIds++;
        const fromRegional = trialIds.some((t) => isRegionalRegistry(t.registry));
        if (fromRegional) {
          regional++;
        } else {
          verified++;
        }
      } else {
        unverified++;
      }
    }

    return reply.send({
      sessionId: searchId,
      totalPapers: papers.length,
      verificationStatus: {
        withTrialIds,
        verified,
        unverified,
        regional,
      },
      ctgovCircuit: getCTGovCircuitStatus(),
    });
  });
}
