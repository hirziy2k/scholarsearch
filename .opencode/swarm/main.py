#!/usr/bin/env python3
"""
Swarm Cascade — Main Entry Point
Launches the production-grade deep research engine.
"""

import sys
import os
import asyncio

swarm_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(swarm_dir)
sys.path.insert(0, parent_dir)

from swarm.orchestrator import SwarmCascade
from swarm.redis_streams import StreamOrchestrator, StreamEventType
from swarm.mechanic_worker import MechanicWorker
from swarm.baseline_normalizer import BaselineNormalizer, CronScheduler
from swarm.volume_velocity import IngressTelemetry

import redis
import sqlite3


REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swarm_state.sqlite")


def init_database():
    """Initialize Swarm-specific SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS swarm_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_hash TEXT NOT NULL,
            evidence_tier TEXT NOT NULL,
            execution_time REAL NOT NULL,
            report_json TEXT NOT NULL,
            previous_hash TEXT,
            current_hash TEXT NOT NULL,
            created_at REAL NOT NULL,
            persisted_at REAL NOT NULL,
            schema_version INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_baselines (
            query_hash TEXT PRIMARY KEY,
            baseline_average REAL NOT NULL,
            total_occurrences INTEGER NOT NULL,
            last_normalized_at REAL,
            normalization_count INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mechanic_dlq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload_json TEXT NOT NULL,
            error_reason TEXT NOT NULL,
            created_at REAL NOT NULL,
            retry_count INTEGER DEFAULT 0,
            last_retry_at REAL
        )
    """)

    conn.commit()
    return conn


async def main():
    """Main entry point for Swarm Cascade."""
    print("=" * 60)
    print("SWARM CASCADE - Production Deep Research Engine")
    print("=" * 60)

    print(f"\n[1/5] Initializing database at {DB_PATH}...")
    db = init_database()
    print("      [OK] SQLite ready")

    print(f"\n[2/5] Connecting to Redis at {REDIS_URL}...")
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print("      [OK] Redis connected")
    except Exception as e:
        print(f"      [FAIL] Redis connection failed: {e}")
        print("      -> Start Redis: redis-server")
        return

    print("\n[3/5] Initializing components...")
    telemetry = IngressTelemetry()
    stream_orchestrator = StreamOrchestrator(redis_client)
    mechanic = MechanicWorker(redis_client, db)
    normalizer = BaselineNormalizer(db)
    print("      [OK] All components ready")

    print("\n[4/5] Starting Mechanic Worker...")
    mechanic_task = asyncio.create_task(mechanic.start())
    print("      [OK] Mechanic running")

    print("\n[5/5] Swarm Cascade ONLINE")
    print("=" * 60)
    print("\nEndpoints:")
    print("  POST /api/research      - Submit research query")
    print("  GET  /api/stream/<hash> - SSE stream")
    print("  GET  /api/health        - Health check")
    print("\nPress Ctrl+C to shutdown")
    print("=" * 60)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down Swarm Cascade...")
        await mechanic.stop()
        mechanic_task.cancel()
        db.close()
        print("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
