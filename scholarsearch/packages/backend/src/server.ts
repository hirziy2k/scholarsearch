import Fastify from "fastify";
import cors from "@fastify/cors";
import { searchRoutes } from "./routes/search.js";
import { healthRoutes } from "./routes/health.js";

const PORT = parseInt(process.env.PORT ?? "3001", 10);
const HOST = process.env.HOST ?? "0.0.0.0";

async function main() {
  const app = Fastify({
    logger: {
      level: process.env.LOG_LEVEL ?? "info",
      transport:
        process.env.NODE_ENV === "development"
          ? { target: "pino-pretty", options: { colorize: true } }
          : undefined,
    },
  });

  // CORS
  await app.register(cors, {
    origin: process.env.FRONTEND_URL ?? "http://localhost:3000",
    methods: ["GET", "POST", "PUT", "DELETE"],
  });

  // Routes
  await app.register(healthRoutes);
  await app.register(searchRoutes, { prefix: "/api" });

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
