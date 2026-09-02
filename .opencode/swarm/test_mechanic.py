"""
Tests for the Mechanic Worker persistence layer.
"""

import json
import time
import asyncio
import sqlite3
import sys
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.mechanic_worker import (
    MechanicWorker,
    ReportPayload,
    PersistedReport,
    HashChainValidator,
    compute_hash,
    CREATE_REPORTS_TABLE,
    CREATE_DLQ_TABLE,
)


class MockRedis:
    """Mock Redis for testing atomic queue operations."""

    def __init__(self):
        self._lists: dict[str, list[str]] = {}

    async def lmove(self, source: str, dest: str, timeout: int = 0) -> Optional[str]:
        if source not in self._lists or not self._lists[source]:
            return None

        item = self._lists[source].pop(0)

        if dest not in self._lists:
            self._lists[dest] = []
        self._lists[dest].append(item)

        return item

    async def lrem(self, key: str, count: int, value: str) -> int:
        if key not in self._lists:
            return 0

        removed = 0
        while count == 0 or removed < count:
            try:
                self._lists[key].remove(value)
                removed += 1
            except ValueError:
                break
        return removed

    async def lpush(self, key: str, value: str) -> int:
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].insert(0, value)
        return len(self._lists[key])

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        if key not in self._lists:
            return []
        if end == -1:
            return self._lists[key][start:]
        return self._lists[key][start:end+1]


def test_report_payload_serialization():
    payload = ReportPayload(
        query_hash="abc123",
        evidence_tier="HIGH_AUTHORITY",
        execution_time=15.5,
        report_data={"claim": "test", "verdict": "HIGH_AUTHORITY"},
        created_at=time.time(),
    )

    json_str = payload.to_json()
    restored = ReportPayload.from_json(json_str)

    assert restored.query_hash == "abc123"
    assert restored.evidence_tier == "HIGH_AUTHORITY"
    assert restored.execution_time == 15.5
    print("PASS: test_report_payload_serialization")


def test_hash_computation():
    h1 = compute_hash("test_payload", None)
    h2 = compute_hash("test_payload", None)
    assert h1 == h2

    h3 = compute_hash("test_payload", h1)
    assert h3 != h1

    h4 = compute_hash("test_payload", "different_hash")
    assert h4 != h3

    print("PASS: test_hash_computation")


def test_hash_chain_validator_valid():
    rows = [
        {"id": 1, "report_json": "payload1", "previous_hash": None, "current_hash": compute_hash("payload1", None)},
        {"id": 2, "report_json": "payload2", "previous_hash": compute_hash("payload1", None), "current_hash": compute_hash("payload2", compute_hash("payload1", None))},
    ]

    is_valid, broken_id = HashChainValidator.validate_chain(rows)
    assert is_valid is True
    assert broken_id is None
    print("PASS: test_hash_chain_validator_valid")


def test_hash_chain_validator_broken():
    rows = [
        {"id": 1, "report_json": "payload1", "previous_hash": None, "current_hash": compute_hash("payload1", None)},
        {"id": 2, "report_json": "payload2", "previous_hash": compute_hash("payload1", None), "current_hash": "TAMPERED_HASH"},
    ]

    is_valid, broken_id = HashChainValidator.validate_chain(rows)
    assert is_valid is False
    assert broken_id == 2
    print("PASS: test_hash_chain_validator_broken")


def test_mechanic_persist_with_hash():
    redis = MockRedis()
    db = sqlite3.connect(":memory:")

    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker.initialize())

    payload = ReportPayload(
        query_hash="test_query",
        evidence_tier="HIGH_AUTHORITY",
        execution_time=12.3,
        report_data={"claim": "vitamin D helps", "verdict": "HIGH_AUTHORITY"},
        created_at=time.time(),
    )

    success = loop.run_until_complete(worker._persist_with_hash(payload))
    assert success is True

    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM swarm_reports")
    count = cursor.fetchone()[0]
    assert count == 1

    cursor.execute("SELECT current_hash, previous_hash FROM swarm_reports")
    row = cursor.fetchone()
    assert row[0] is not None
    assert row[1] is None

    print("PASS: test_mechanic_persist_with_hash")


def test_mechanic_hash_chain_growth():
    redis = MockRedis()
    db = sqlite3.connect(":memory:")

    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker.initialize())

    for i in range(5):
        payload = ReportPayload(
            query_hash=f"query_{i}",
            evidence_tier="HIGH_AUTHORITY",
            execution_time=float(i),
            report_data={"index": i},
            created_at=time.time(),
        )
        loop.run_until_complete(worker._persist_with_hash(payload))

    is_valid, broken_id = loop.run_until_complete(worker.verify_chain_integrity())
    assert is_valid is True
    assert broken_id is None

    print("PASS: test_mechanic_hash_chain_growth")


def test_mechanic_atomic_queue_flow():
    redis = MockRedis()
    db = sqlite3.connect(":memory:")

    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(worker.initialize())

    payload = ReportPayload(
        query_hash="queue_test",
        evidence_tier="SUPPORTED",
        execution_time=8.0,
        report_data={"test": True},
        created_at=time.time(),
    )

    loop.run_until_complete(
        redis.lpush("persistence_queue", payload.to_json())
    )

    result = loop.run_until_complete(
        redis.lmove("persistence_queue", "unacked_writes")
    )
    assert result is not None

    success = loop.run_until_complete(worker._persist_with_hash(payload))
    assert success is True

    loop.run_until_complete(redis.lrem("unacked_writes", 1, payload.to_json()))

    report = loop.run_until_complete(worker.get_report_by_hash("queue_test"))
    assert report is not None
    assert report.query_hash == "queue_test"

    print("PASS: test_mechanic_atomic_queue_flow")


def test_mechanic_dlq_routing():
    redis = MockRedis()
    db = sqlite3.connect(":memory:")

    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_event_loop() if hasattr(asyncio, 'get_event_event_loop') else asyncio.get_event_loop()
    loop.run_until_complete(worker.initialize())

    malformed_json = "NOT_VALID_JSON"

    loop.run_until_complete(worker._send_to_dlq(malformed_json, "Parse error"))

    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM mechanic_dlq")
    count = cursor.fetchone()[0]
    assert count == 1

    dlq_items = loop.run_until_complete(worker.get_dlq_items())
    assert len(dlq_items) == 1
    assert dlq_items[0]["error_reason"] == "Parse error"

    print("PASS: test_mechanic_dlq_routing")


if __name__ == "__main__":
    test_report_payload_serialization()
    test_hash_computation()
    test_hash_chain_validator_valid()
    test_hash_chain_validator_broken()
    test_mechanic_persist_with_hash()
    test_mechanic_hash_chain_growth()
    test_mechanic_atomic_queue_flow()
    test_mechanic_dlq_routing()
    print("\n=== ALL MECHANIC TESTS PASSED ===")
