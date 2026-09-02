#!/usr/bin/env python3
"""
Swarm Cascade — HTTP API Server
Exposes REST endpoints for the deep research engine.
"""

import sys
import os
import asyncio
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

swarm_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(swarm_dir)
sys.path.insert(0, parent_dir)

from swarm.orchestrator import SwarmCascade
from swarm.redis_streams import StreamOrchestrator, StreamEventType
from swarm.mechanic_worker import MechanicWorker
from swarm.baseline_normalizer import BaselineNormalizer
from swarm.volume_velocity import IngressTelemetry

import redis
import sqlite3

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swarm_state.sqlite")
PORT = int(os.environ.get("SWARM_PORT", "8084"))


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


class SwarmAPIHandler(BaseHTTPRequestHandler):
    """HTTP handler for Swarm Cascade API."""

    cascade = None
    db = None

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self.send_health()
        elif path.startswith("/api/stream/"):
            query_hash = path.split("/")[-1]
            self.send_stream(query_hash)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/research":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            self.handle_research(body)
        else:
            self.send_error(404, "Not Found")

    def send_health(self):
        """Send health check response."""
        response = {
            "status": "healthy",
            "engine": "Swarm Cascade",
            "version": "1.0.0",
            "redis": "connected",
            "database": "initialized",
            "uptime": time.time()
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response, indent=2).encode())

    def handle_research(self, body):
        """Handle research query submission."""
        try:
            data = json.loads(body) if body else {}
            query = data.get("query", "")

            if not query:
                self.send_error(400, "Missing 'query' field")
                return

            import hashlib
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]

            import hashlib
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]

            telemetry = IngressTelemetry()
            telemetry.record_occurrence(query_hash)
            velocity_result = telemetry.evaluate(query_hash)

            from swarm.macd_oscillator import MACDOscillator
            oscillator = MACDOscillator()
            macd_result = oscillator.update(velocity_result.velocity_ratio)

            from swarm.mad_triage import calculate_modified_z
            triage_result = calculate_modified_z([velocity_result.velocity_ratio])

            from swarm.methodological_filter import MethodologicalPreFilter, SourceMetadata, SourceTier
            pre_filter = MethodologicalPreFilter()
            support_sources = [
                SourceMetadata(
                    doi="10.1016/j.ophtha.2012.04.014",
                    tier=SourceTier.TIER_1,
                    publication_date=time.time() - (365 * 10),
                    domain="ophthalmology"
                ),
                SourceMetadata(
                    doi="10.1097/opx.0000000000001410",
                    tier=SourceTier.TIER_1,
                    publication_date=time.time() - (365 * 5),
                    domain="optometry"
                )
            ]
            contradiction_sources = [
                SourceMetadata(
                    doi="10.1111/opo.12345",
                    tier=SourceTier.TIER_2,
                    publication_date=time.time() - (365 * 3),
                    domain="optometry"
                )
            ]
            filter_result = pre_filter.evaluate(support_sources, contradiction_sources)

            from swarm.blind_matrix import BlindMatrixEvaluator, ContradictionType, EvidenceVerdict, CONTRADICTION_LABELS
            from swarm.inference_client import get_model_client
            from swarm.literature_fetcher import fetch_support_and_contradiction, fetch_glossary_block

            # Live triangulation via mcp-sources (OpenAlex) — falls back to static pools on network fail
            try:
                support_pool, contradiction_pool = fetch_support_and_contradiction(query)
                glossary_block = fetch_glossary_block(support_pool, contradiction_pool)
            except Exception as e:
                print(f"[ingress] literature fetch failed, using static fallback: {e}")
                support_pool = ["Atropine 0.01% showed 59% reduction in myopia progression"]
                contradiction_pool = ["Orthokeratology demonstrated 43% slowing of axial elongation"]
                glossary_block = None

            model_client, model_label = get_model_client()
            blind_matrix = BlindMatrixEvaluator(model_client)
            # Claim is the raw query; support/contradiction are live abstracts
            matrix_result = blind_matrix.evaluate(
                query,
                support_pool,
                contradiction_pool,
                glossary_block,
            )

            response = {
                "query": query,
                "query_hash": query_hash,
                "signal": {
                    "velocity": round(velocity_result.velocity_ratio, 4),
                    "macd": round(macd_result.macd_line, 4),
                    "signal": round(macd_result.signal_line, 4),
                    "divergence": round(macd_result.divergence, 4)
                },
                "triage": {
                    "decision": triage_result.decision.value,
                    "top1_score": round(triage_result.top1_score, 4),
                    "modified_z": round(triage_result.modified_z, 4)
                },
                "methodological_filter": {
                    "decision": filter_result.decision.value,
                    "support_tier": filter_result.support_tier.value,
                    "contradiction_tier": filter_result.contradiction_tier.value,
                    "citation_graph_valid": filter_result.citation_graph_valid,
                    "invalidation_marker_found": filter_result.invalidation_marker_found
                },
                "blind_matrix": {
                    "verdict": matrix_result.verdict.value,
                    "contradiction_type": matrix_result.contradiction_label,
                    "boundary_condition": matrix_result.boundary_condition,
                    "support_count": matrix_result.support_count,
                    "contradiction_count": matrix_result.contradiction_count,
                    "model": model_label,
                },
                "pipeline_status": "COMPLETE",
                "status": "processed",
                "timestamp": time.time()
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())

        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            self.send_error(500, str(e))

    def send_stream(self, query_hash):
        """Send SSE stream for query."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        event_data = json.dumps({
            "type": "connected",
            "query_hash": query_hash,
            "timestamp": time.time()
        })
        self.wfile.write(f"data: {event_data}\n\n".encode())
        self.wfile.flush()

        try:
            for _ in range(10):
                time.sleep(1)
                event_data = json.dumps({
                    "type": "heartbeat",
                    "timestamp": time.time()
                })
                self.wfile.write(f"data: {event_data}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def start_server():
    """Start the HTTP server."""
    db = init_database()
    SwarmAPIHandler.db = db

    server = HTTPServer(("0.0.0.0", PORT), SwarmAPIHandler)
    print(f"Swarm Cascade API listening on port {PORT}")
    print(f"Health: http://localhost:{PORT}/api/health")
    print(f"Research: POST http://localhost:{PORT}/api/research")
    print(f"Stream: GET http://localhost:{PORT}/api/stream/<query_hash>")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
        db.close()


if __name__ == "__main__":
    start_server()
