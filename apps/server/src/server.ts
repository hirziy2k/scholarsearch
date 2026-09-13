import Fastify from "fastify";
import cors from "@fastify/cors";
import { searchRoutes } from "./routes/search.js";
import { healthRoutes } from "./routes/health.js";
import { pollingRoutes } from "./routes/polling.js";
import { adjudicationRoutes } from "./routes/adjudication.js";
import { exportRoutes } from "./routes/export.js";
import { bulkExportRoutes } from "./routes/bulk-export.js";
import { initDatabase, closeDatabase } from "./db.js";

const PORT = parseInt(process.env.PORT ?? "3001", 10);
const HOST = process.env.HOST ?? "0.0.0.0";

async function main() {
  // Initialize database (WAL mode, busy_timeout)
  await initDatabase();

  const app = Fastify({
    logger: {
      level: process.env.LOG_LEVEL ?? "info",
      transport:
        process.env.NODE_ENV === "development"
          ? { target: "pino-pretty", options: { colorize: true } }
          : undefined,
    },
  });

  // Graceful shutdown
  app.addHook("onClose", async () => {
    await closeDatabase();
  });

  // CORS
  await app.register(cors, {
    origin: process.env.FRONTEND_URL ?? "http://localhost:3000",
    methods: ["GET", "POST", "PUT", "DELETE"],
  });

  // Routes
  await app.register(healthRoutes);
  await app.register(searchRoutes, { prefix: "/api" });
  await app.register(pollingRoutes, { prefix: "/api" });
  await app.register(adjudicationRoutes, { prefix: "/api" });
  await app.register(exportRoutes, { prefix: "/api" });
  await app.register(bulkExportRoutes, { prefix: "/api" });

  // Start server
  try {
    await app.listen({ port: PORT, host: HOST });
    app.log.info(`ScholarSearch backend running on http://${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

main();
