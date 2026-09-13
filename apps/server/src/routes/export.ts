import type { FastifyInstance } from "fastify";
import { getDb } from "../db.js";
import { checkExportGate, recordExportAttempt, type ExportFormat } from "../services/export-gate.js";

export async function exportRoutes(app: FastifyInstance) {
  /**
   * POST /api/search/:searchId/export
   *
   * Request export with gate check. Returns export status or block reason.
   * For blocked RIS/CSV in evidence mode, suggests Clinical Brief PDF.
   */
  app.post<{
    Params: { searchId: string };
    Body: { format: ExportFormat };
  }>("/search/:searchId/export", async (request, reply) => {
    const { searchId } = request.params;
    const { format } = request.body;

    if (!["ris", "csv", "json", "pdf"].includes(format)) {
      return reply.status(400).send({ error: "Invalid format. Must be: ris | csv | json | pdf" });
    }

    const db = getDb();
    const session = await db.searchSession.findFirst({ where: { searchId } });
    if (!session) {
      return reply.status(404).send({ error: "Session not found" });
    }

    // Parse source statuses
    const sourceStatuses = (JSON.parse(session.sourceStatuses) as Array<{
      source: string;
      status: string;
      resultCount: number;
    }>).map((s) => ({
      ...s,
      status: s.status as "complete" | "error" | "pending",
    }));

    // Check export gate
    const gateResult = checkExportGate(session.mode, format, sourceStatuses);

    // Record attempt
    await recordExportAttempt(
      searchId,
      format,
      gateResult,
      sourceStatuses.reduce((sum, s) => sum + s.resultCount, 0),
    );

    if (!gateResult.allowed) {
      return reply.status(403).send({
        export: {
          allowed: false,
          format,
          blockedReason: gateResult.blockedReason,
          downgradeTo: gateResult.downgradeTo,
          watermark: gateResult.watermark,
        },
        suggestion: gateResult.downgradeTo
          ? `Try exporting as ${gateResult.downgradeTo.toUpperCase()} instead — a watermarked Clinical Brief will be generated.`
          : null,
      });
    }

    // For allowed exports, return the gate result with generation metadata
    return reply.send({
      export: {
        allowed: true,
        format,
        watermark: gateResult.watermark,
        reason: gateResult.reason,
        resultCount: sourceStatuses.reduce((sum, s) => sum + s.resultCount, 0),
      },
      message: gateResult.watermark
        ? "Export will be watermarked as Clinical Brief due to partial source availability."
        : "Export ready for generation.",
    });
  });

  /**
   * GET /api/search/:searchId/export/history
   *
   * Returns export history for a session.
   */
  app.get<{
    Params: { searchId: string };
  }>("/search/:searchId/export/history", async (request, reply) => {
    const { searchId } = request.params;
    const db = getDb();

    const session = await db.searchSession.findFirst({ where: { searchId } });
    if (!session) {
      return reply.status(404).send({ error: "Session not found" });
    }

    const exports = await db.exportRecord.findMany({
      where: { sessionId: session.id },
      orderBy: { createdAt: "desc" },
    });

    return reply.send({
      searchId,
      exports: exports.map((e) => ({
        id: e.id,
        format: e.format,
        status: e.status,
        blockedReason: e.blockedReason,
        watermarked: e.watermarked,
        resultCount: e.resultCount,
        createdAt: e.createdAt,
        completedAt: e.completedAt,
      })),
    });
  });
}
