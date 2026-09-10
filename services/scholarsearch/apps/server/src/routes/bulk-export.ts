import type { FastifyInstance } from "fastify";
import { executeBulkExport, type BulkExportOptions } from "../services/bulk-export.js";

export async function bulkExportRoutes(app: FastifyInstance) {
  /**
   * GET /api/search/:searchId/bulk-export?format=ris
   *
   * Headless bulk export with HTTP chunked streaming.
   * Returns 200 OK immediately, streams results as pages are fetched.
   * Rate-limited: 200ms between page fetches per source.
   * Safety cap: 500 pages per source (5000 results max).
   */
  app.get<{
    Params: { searchId: string };
    Querystring: { format?: string };
  }>("/search/:searchId/bulk-export", async (request, reply) => {
    const { searchId } = request.params;
    const format = (request.query.format ?? "ris") as "ris" | "csv" | "json";

    if (!["ris", "csv", "json"].includes(format)) {
      return reply.status(400).send({ error: "Invalid format. Must be: ris | csv | json" });
    }

    // Execute streaming export — does not return a JSON body
    await executeBulkExport({ searchId, format, reply });
  });
}
