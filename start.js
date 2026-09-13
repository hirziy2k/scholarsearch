#!/usr/bin/env node

/**
 * ScholarSearch Production Startup
 * Starts backend (port 3001) and frontend (port 3000) concurrently.
 */

const { spawn } = require("child_process");
const path = require("path");

const ROOT = __dirname;
const BACKEND_DIR = path.join(ROOT, "apps", "server");
const FRONTEND_DIR = path.join(ROOT, "apps", "client");

const PORTS = {
  backend: parseInt(process.env.BACKEND_PORT ?? "3001", 10),
  frontend: parseInt(process.env.FRONTEND_PORT ?? "3000", 10),
};

function log(service, msg) {
  const ts = new Date().toISOString().slice(11, 19);
  console.log(`[${ts}] [${service}] ${msg}`);
}

function startService(name, cmd, args, cwd, env = {}) {
  const fullEnv = { ...process.env, ...env };
  const child = spawn(cmd, args, {
    cwd,
    env: fullEnv,
    stdio: ["ignore", "pipe", "pipe"],
    shell: process.platform === "win32",
  });

  child.stdout?.on("data", (data) => {
    data.toString().split("\n").filter(Boolean).forEach((line) => {
      log(name, line);
    });
  });

  child.stderr?.on("data", (data) => {
    data.toString().split("\n").filter(Boolean).forEach((line) => {
      log(name, line);
    });
  });

  child.on("exit", (code) => {
    log(name, `exited with code ${code}`);
    if (code !== 0) {
      log("system", `${name} failed, shutting down...`);
      process.exit(1);
    }
  });

  return child;
}

// Start backend
log("system", "starting backend...");
const backend = startService(
  "backend",
  "node",
  ["dist/server.js"],
  BACKEND_DIR,
  {
    PORT: PORTS.backend.toString(),
    HOST: "0.0.0.0",
    NODE_ENV: "production",
    FRONTEND_URL: `http://localhost:${PORTS.frontend}`,
  },
);

// Start frontend after a short delay (let backend initialize)
setTimeout(() => {
  log("system", "starting frontend...");
  const frontend = startService(
    "frontend",
    "node",
    ["../node_modules/next/dist/bin/next", "start", "-p", PORTS.frontend.toString()],
    FRONTEND_DIR,
    {
      NODE_ENV: "production",
      NEXT_PUBLIC_API_URL: `http://localhost:${PORTS.backend}`,
    },
  );

  // Graceful shutdown
  const shutdown = (signal) => {
    log("system", `received ${signal}, shutting down...`);
    backend.kill(signal);
    frontend.kill(signal);
    setTimeout(() => process.exit(0), 2000);
  };

  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));
}, 1500);

log("system", "ScholarSearch starting...");
log("system", `backend: http://localhost:${PORTS.backend}`);
log("system", `frontend: http://localhost:${PORTS.frontend}`);
