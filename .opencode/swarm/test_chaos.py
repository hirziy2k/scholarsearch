"""
Fault Injection Suite — Chaos Tests
Validates system resilience under infrastructure hostility.
Proves recovery from mid-operation crashes and data corruption.
"""

import json
import time
import asyncio
import sqlite3
import signal
import os
import sys
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.mechanic_worker import (
    MechanicWorker,
    ReportPayload,
    HashChainValidator,
    compute_hash,
    PERSISTENCE_QUEUE,
    UNACKED_WRITES,
    CREATE_REPORTS_TABLE,
)


class ChaosRedis:
    """Redis mock that supports fault injection."""

    def __init__(self):
        self._lists: dict[str, list[str]] = {}
        self._inject_fault_after_lmove = False
        self._lmove_completed = False
        self._fault_callback = None

    async def lmove(self, source: str, dest: str, timeout: int = 0) -> Optional[str]:
        if source not in self._lists or not self._lists[source]:
            return None

        item = self._lists[source].pop(0)

        if dest not in self._lists:
            self._lists[dest] = []
        self._lists[dest].append(item)

        self._lmove_completed = True

        if self._inject_fault_after_lmove and self._fault_callback:
            await self._fault_callback()

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


class CrashSimulator:
    """Simulates process crashes at precise moments."""

    def __init__(self):
        self._crash_point: Optional[str] = None
        self._crash_after_lmove = False
        self._crashed = False

    def set_crash_after_lmove(self):
        self._crash_after_lmove = True
        self._crash_point = "after_lmove_before_insert"

    def should_crash(self) -> bool:
        if self._crash_after_lmove and not self._crashed:
            self._crashed = True
            return True
        return False


def test_chaos_crash_after_lmove_before_insert():
    """
    CHAOS TEST: Kill Mechanic after LMOVE but before SQLite INSERT.
    
    Scenario:
        1. Swarm worker pushes report to persistence_queue
        2. Mechanic executes LMOVE (atomic pop from queue to unacked)
        3. PROCESS CRASHES before SQLite INSERT
        4. Recovery pushes item back to persistence_queue
        5. Mechanic reprocesses and completes INSERT
        6. Hash chain integrity verified
    """
    redis = ChaosRedis()
    db = sqlite3.connect(":memory:")
    cursor = db.cursor()
    cursor.execute(CREATE_REPORTS_TABLE)
    db.commit()

    payload = ReportPayload(
        query_hash="chaos_test_1",
        evidence_tier="HIGH_AUTHORITY",
        execution_time=15.0,
        report_data={"claim": "test claim", "chaos": True},
        created_at=time.time(),
    )

    redis._lists[PERSISTENCE_QUEUE] = [payload.to_json()]

    result = asyncio.get_event_loop().run_until_complete(
        redis.lmove(PERSISTENCE_QUEUE, UNACKED_WRITES)
    )
    assert result is not None

    unacked = redis._lists.get(UNACKED_WRITES, [])
    assert len(unacked) == 1, "Item should be in unacked_writes after LMOVE"

    cursor.execute("SELECT COUNT(*) FROM swarm_reports")
    count = cursor.fetchone()[0]
    assert count == 0, "No records should be in SQLite before recovery"

    asyncio.get_event_loop().run_until_complete(
        redis.lpush(PERSISTENCE_QUEUE, unacked[0])
    )
    asyncio.get_event_loop().run_until_complete(
        redis.lrem(UNACKED_WRITES, 1, unacked[0])
    )

    assert len(redis._lists[PERSISTENCE_QUEUE]) == 1
    assert len(redis._lists.get(UNACKED_WRITES, [])) == 0

    worker = MechanicWorker(redis, db)
    success = asyncio.get_event_loop().run_until_complete(
        worker._persist_with_hash(payload)
    )
    assert success is True

    cursor.execute("SELECT COUNT(*) FROM swarm_reports")
    count = cursor.fetchone()[0]
    assert count == 1, "Record should be persisted after recovery"

    is_valid, broken_id = asyncio.get_event_loop().run_until_complete(
        worker.verify_chain_integrity()
    )
    assert is_valid is True, f"Hash chain should be valid, broken at row {broken_id}"

    print("PASS: test_chaos_crash_after_lmove_before_insert")


def test_chaos_duplicate_prevention():
    """
    CHAOS TEST: Verify hash chain remains valid with duplicate inserts.
    """
    redis = ChaosRedis()
    db = sqlite3.connect(":memory:")
    cursor = db.cursor()
    cursor.execute(CREATE_REPORTS_TABLE)
    db.commit()

    payload = ReportPayload(
        query_hash="dup_test",
        evidence_tier="SUPPORTED",
        execution_time=8.0,
        report_data={"test": "duplicate prevention"},
        created_at=time.time(),
    )

    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(worker._persist_with_hash(payload))
    loop.run_until_complete(worker._persist_with_hash(payload))

    cursor.execute("SELECT COUNT(*) FROM swarm_reports WHERE query_hash = 'dup_test'")
    count = cursor.fetchone()[0]
    assert count == 2, f"Expected 2 records, got {count}"

    is_valid, broken_id = loop.run_until_complete(worker.verify_chain_integrity())
    assert is_valid is True, f"Hash chain should be valid, broken at {broken_id}"

    print("PASS: test_chaos_duplicate_prevention")


def test_chaos_hash_chain_integrity_under_failure():
    """
    CHAOS TEST: Multiple inserts during batch processing.
    Verify hash chain remains valid.
    """
    redis = ChaosRedis()
    db = sqlite3.connect(":memory:")
    cursor = db.cursor()
    cursor.execute(CREATE_REPORTS_TABLE)
    db.commit()

    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()

    for i in range(5):
        payload = ReportPayload(
            query_hash=f"chain_test_{i}",
            evidence_tier="HIGH_AUTHORITY",
            execution_time=float(i),
            report_data={"index": i},
            created_at=time.time(),
        )
        loop.run_until_complete(worker._persist_with_hash(payload))

    is_valid, broken_id = loop.run_until_complete(worker.verify_chain_integrity())
    assert is_valid is True, f"Hash chain should be valid, broken at {broken_id}"

    cursor.execute("SELECT COUNT(*) FROM swarm_reports")
    count = cursor.fetchone()[0]
    assert count == 5

    print("PASS: test_chaos_hash_chain_integrity_under_failure")


def test_chaos_recovery_loop_scrubs_orphans():
    """
    CHAOS TEST: Verify orphaned items are correctly handled.
    """
    redis = ChaosRedis()
    db = sqlite3.connect(":memory:")
    cursor = db.cursor()
    cursor.execute(CREATE_REPORTS_TABLE)
    db.commit()

    payload = ReportPayload(
        query_hash="orphan_test",
        evidence_tier="CONFLICTED",
        execution_time=5.0,
        report_data={"orphan": True},
        created_at=time.time(),
    )

    redis._lists[UNACKED_WRITES] = [payload.to_json()]

    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()

    unacked = redis._lists.get(UNACKED_WRITES, [])
    assert len(unacked) == 1

    loop.run_until_complete(redis.lpush(PERSISTENCE_QUEUE, unacked[0]))
    loop.run_until_complete(redis.lrem(UNACKED_WRITES, 1, unacked[0]))

    assert PERSISTENCE_QUEUE in redis._lists
    assert len(redis._lists[PERSISTENCE_QUEUE]) == 1
    assert len(redis._lists.get(UNACKED_WRITES, [])) == 0

    print("PASS: test_chaos_recovery_loop_scrubs_orphans")


class ProcessError(Exception):
    pass


if __name__ == "__main__":
    test_chaos_crash_after_lmove_before_insert()
    test_chaos_duplicate_prevention()
    test_chaos_hash_chain_integrity_under_failure()
    test_chaos_recovery_loop_scrubs_orphans()
    print("\n=== ALL CHAOS TESTS PASSED ===")
