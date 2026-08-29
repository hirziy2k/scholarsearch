import type { FastifyInstance } from "fastify";

export async function healthRoutes(app: FastifyInstance) {
  app.get("/health", async () => {
    return {
      status: "ok",
      timestamp: new Date().toISOString(),
      service: "scholarsearch-backend",
      version: "0.1.0",
    };
  });
}
