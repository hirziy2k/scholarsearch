import { PrismaClient } from "@prisma/client";

// ============================================
// Singleton Prisma Client with WAL Configuration
// ============================================
// SQLite WAL mode allows concurrent reads with one writer.
// busy_timeout prevents SQLITE_BUSY errors under concurrent load.
// For Turso (libSQL), WAL and busy_timeout are handled by the driver.

const isSQLite = (process.env.DB_PROVIDER ?? "sqlite") === "sqlite";

const prisma = new PrismaClient({
  log: process.env.NODE_ENV === "development" ? ["warn", "error"] : ["error"],
});

// Initialize WAL mode and busy timeout for SQLite
let initialized = false;

export async function initDatabase(): Promise<PrismaClient> {
  if (initialized) return prisma;

  if (isSQLite) {
    await prisma.$executeRawUnsafe("PRAGMA journal_mode=WAL");
    await prisma.$executeRawUnsafe("PRAGMA busy_timeout=5000");
    await prisma.$executeRawUnsafe("PRAGMA synchronous=NORMAL");
  }

  initialized = true;
  return prisma;
}

export function getDb(): PrismaClient {
  if (!initialized) {
    throw new Error("Database not initialized. Call initDatabase() first.");
  }
  return prisma;
}

export async function closeDatabase(): Promise<void> {
  await prisma.$disconnect();
  initialized = false;
}
