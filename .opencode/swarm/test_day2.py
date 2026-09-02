"""
Tests for Day 2 operational components.
"""

import json
import time
import sqlite3
import csv
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.baseline_normalizer import BaselineNormalizer, CronScheduler
from swarm.audit_export import AuditExporter, AuditRecord, compute_hash


def create_test_database() -> sqlite3.Connection:
    """Create test database with sample data."""
    db = sqlite3.connect(":memory:")
    cursor = db.cursor()

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

    db.commit()
    return db


def test_baseline_normalizer():
    db = create_test_database()
    cursor = db.cursor()

    for i in range(5):
        cursor.execute("""
            INSERT INTO query_baselines (query_hash, baseline_average, total_occurrences)
            VALUES (?, ?, ?)
        """, (f"query_{i}", float(i + 1) * 10, (i + 1) * 100))
    db.commit()

    normalizer = BaselineNormalizer(db)
    results = normalizer.normalize_all_baselines(current_volume=1000)

    assert len(results) == 5
    assert all(r.new_baseline != r.old_baseline for r in results)

    stats = normalizer.get_platform_stats()
    assert stats["tracked_queries"] == 5

    print("PASS: test_baseline_normalizer")


def test_cron_scheduler():
    db = create_test_database()
    normalizer = BaselineNormalizer(db)
    scheduler = CronScheduler(normalizer, interval_days=30)

    assert scheduler.should_run() is True

    scheduler.execute(current_volume=500)

    assert scheduler.should_run() is False

    print("PASS: test_cron_scheduler")


def test_audit_export_chain():
    db = create_test_database()
    cursor = db.cursor()

    genesis_json = json.dumps({"claim": "genesis"}, sort_keys=True)
    genesis_hash = compute_hash(genesis_json, None)

    cursor.execute("""
        INSERT INTO swarm_reports
        (query_hash, evidence_tier, execution_time, report_json,
         previous_hash, current_hash, created_at, persisted_at, schema_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("genesis", "HIGH_AUTHORITY", 0.0, genesis_json,
          None, genesis_hash, 0.0, 1.0, 1))

    second_json = json.dumps({"claim": "second"}, sort_keys=True)
    second_hash = compute_hash(second_json, genesis_hash)

    cursor.execute("""
        INSERT INTO swarm_reports
        (query_hash, evidence_tier, execution_time, report_json,
         previous_hash, current_hash, created_at, persisted_at, schema_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("second", "SUPPORTED", 1.0, second_json,
          genesis_hash, second_hash, 1.0, 2.0, 1))

    db.commit()

    exporter = AuditExporter.__new__(AuditExporter)
    exporter._db_path = ":memory:"

    original_connect = sqlite3.connect
    sqlite3.connect = lambda *args, **kwargs: db

    try:
        export = exporter.export_full_chain()
        assert export.total_records == 2
        assert export.chain_valid is True
        assert export.first_broken_row is None
    finally:
        sqlite3.connect = original_connect

    print("PASS: test_audit_export_chain")


def test_audit_export_csv():
    db = create_test_database()
    cursor = db.cursor()

    for i in range(3):
        report_json = json.dumps({"claim": f"claim_{i}"}, sort_keys=True)
        previous_hash = None if i == 0 else compute_hash(
            json.dumps({"claim": f"claim_{i-1}"}, sort_keys=True),
            None if i == 1 else compute_hash(json.dumps({"claim": f"claim_{i-1}"}, sort_keys=True), None)
        )
        current_hash = compute_hash(report_json, previous_hash)

        cursor.execute("""
            INSERT INTO swarm_reports
            (query_hash, evidence_tier, execution_time, report_json,
             previous_hash, current_hash, created_at, persisted_at, schema_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (f"query_{i}", "HIGH_AUTHORITY", float(i), report_json,
              previous_hash, current_hash, float(i), float(i + 1), 1))

    db.commit()

    exporter = AuditExporter.__new__(AuditExporter)
    exporter._db_path = ":memory:"

    original_connect = sqlite3.connect
    sqlite3.connect = lambda *args, **kwargs: db

    try:
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), "test_audit.csv")
        exporter.export_csv(output_path)

        with open(output_path) as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 4
        assert rows[0][0] == "row_id"
    finally:
        sqlite3.connect = original_connect

    print("PASS: test_audit_export_csv")


def test_audit_export_json():
    db = create_test_database()
    cursor = db.cursor()

    report_json = json.dumps({"claim": "test"}, sort_keys=True)
    current_hash = compute_hash(report_json, None)

    cursor.execute("""
        INSERT INTO swarm_reports
        (query_hash, evidence_tier, execution_time, report_json,
         previous_hash, current_hash, created_at, persisted_at, schema_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("test", "HIGH_AUTHORITY", 1.0, report_json,
          None, current_hash, 1.0, 2.0, 1))

    db.commit()

    exporter = AuditExporter.__new__(AuditExporter)
    exporter._db_path = ":memory:"

    original_connect = sqlite3.connect
    sqlite3.connect = lambda *args, **kwargs: db

    try:
        import tempfile
        output_path = os.path.join(tempfile.gettempdir(), "test_audit.json")
        exporter.export_json(output_path)

        with open(output_path) as f:
            data = json.load(f)

        assert "metadata" in data
        assert "records" in data
        assert data["metadata"]["total_records"] == 1
        assert data["metadata"]["chain_valid"] is True
    finally:
        sqlite3.connect = original_connect

    print("PASS: test_audit_export_json")


if __name__ == "__main__":
    test_baseline_normalizer()
    test_cron_scheduler()
    test_audit_export_chain()
    test_audit_export_csv()
    test_audit_export_json()
    print("\n=== ALL DAY 2 TESTS PASSED ===")
