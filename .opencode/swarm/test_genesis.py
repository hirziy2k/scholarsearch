"""
Genesis Validation Suite
Proves hash chain integrity from empty database to populated state.
Validates the cryptographic anchor point for the entire ledger.
"""

import json
import time
import asyncio
import sqlite3
import hashlib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.mechanic_worker import (
    MechanicWorker,
    ReportPayload,
    HashChainValidator,
    compute_hash,
    CREATE_REPORTS_TABLE,
    CREATE_REPORTS_INDEXES,
)


GENESIS_HASH_SEED = "SWARM_CASCADE_GENESIS_BLOCK_v1"

GENESIS_REPORT = ReportPayload(
    query_hash="genesis_block",
    evidence_tier="HIGH_AUTHORITY",
    execution_time=0.0,
    report_data={
        "claim": "System initialized",
        "verdict": "GENESIS",
        "seed": GENESIS_HASH_SEED,
    },
    created_at=0.0,
)


class GenesisRedis:
    """Minimal Redis mock for genesis tests."""

    def __init__(self):
        self._lists: dict[str, list[str]] = {}

    async def lmove(self, source: str, dest: str, timeout: int = 0) -> str:
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
        try:
            self._lists[key].remove(value)
            removed = 1
        except ValueError:
            pass
        return removed


def create_empty_database() -> sqlite3.Connection:
    """Create a completely empty SQLite database."""
    db = sqlite3.connect(":memory:")
    cursor = db.cursor()
    cursor.execute(CREATE_REPORTS_TABLE)
    cursor.executescript(CREATE_REPORTS_INDEXES)
    db.commit()
    return db


def test_genesis_first_insert():
    """
    GENESIS TEST: Insert first record into empty database.
    Verify hash chain anchor is correctly established.
    """
    db = create_empty_database()
    redis = GenesisRedis()
    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()

    previous_hash = loop.run_until_complete(worker._get_last_hash())
    assert previous_hash is None, "Empty database should have no previous hash"

    success = loop.run_until_complete(worker._persist_with_hash(GENESIS_REPORT))
    assert success is True

    cursor = db.cursor()
    cursor.execute("SELECT previous_hash, current_hash FROM swarm_reports ORDER BY id LIMIT 1")
    row = cursor.fetchone()

    assert row[0] is None, "Genesis block should have NULL previous_hash"
    assert row[1] is not None, "Genesis block should have a current_hash"

    expected_hash = compute_hash(GENESIS_REPORT.to_json(), None)
    assert row[1] == expected_hash, f"Genesis hash mismatch: {row[1]} != {expected_hash}"

    print("PASS: test_genesis_first_insert")


def test_genesis_second_insert_chain():
    """
    GENESIS TEST: Insert second record, verify chain link.
    """
    db = create_empty_database()
    redis = GenesisRedis()
    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(worker._persist_with_hash(GENESIS_REPORT))

    second_report = ReportPayload(
        query_hash="second_block",
        evidence_tier="SUPPORTED",
        execution_time=10.0,
        report_data={"claim": "Second record", "chain_position": 2},
        created_at=time.time(),
    )

    success = loop.run_until_complete(worker._persist_with_hash(second_report))
    assert success is True

    cursor = db.cursor()
    cursor.execute("SELECT previous_hash, current_hash FROM swarm_reports ORDER BY id")
    rows = cursor.fetchall()

    assert len(rows) == 2

    genesis_hash = rows[0][1]
    second_previous = rows[1][0]
    second_current = rows[1][1]

    assert second_previous == genesis_hash, "Second record's previous_hash must match genesis hash"

    expected_second_hash = compute_hash(second_report.to_json(), genesis_hash)
    assert second_current == expected_second_hash, "Second record hash mismatch"

    print("PASS: test_genesis_second_insert_chain")


def test_genesis_tamper_detection():
    """
    GENESIS TEST: Tamper with genesis record, verify chain breaks.
    """
    db = create_empty_database()
    redis = GenesisRedis()
    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(worker._persist_with_hash(GENESIS_REPORT))

    second_report = ReportPayload(
        query_hash="tamper_test",
        evidence_tier="HIGH_AUTHORITY",
        execution_time=5.0,
        report_data={"claim": "Will be orphaned"},
        created_at=time.time(),
    )
    loop.run_until_complete(worker._persist_with_hash(second_report))

    cursor = db.cursor()
    cursor.execute("SELECT id, report_json FROM swarm_reports ORDER BY id LIMIT 1")
    row = cursor.fetchone()

    tampered_json = row[1].replace("System initialized", "TAMPERED CONTENT")
    cursor.execute("UPDATE swarm_reports SET report_json = ? WHERE id = ?", (tampered_json, row[0]))
    db.commit()

    is_valid, broken_id = loop.run_until_complete(worker.verify_chain_integrity())
    assert is_valid is False, "Chain should be broken after tampering"
    assert broken_id is not None, "Should identify broken row"

    print("PASS: test_genesis_tamper_detection")


def test_genesis_empty_to_populated_cycle():
    """
    GENESIS TEST: Full cycle from empty DB to 10 records.
    Verify complete chain integrity at each step.
    """
    db = create_empty_database()
    redis = GenesisRedis()
    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()

    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM swarm_reports")
    assert cursor.fetchone()[0] == 0, "Database should start empty"

    for i in range(10):
        payload = ReportPayload(
            query_hash=f"record_{i}",
            evidence_tier="HIGH_AUTHORITY" if i % 2 == 0 else "SUPPORTED",
            execution_time=float(i),
            report_data={"index": i, "sequence": i + 1},
            created_at=time.time() + i,
        )
        success = loop.run_until_complete(worker._persist_with_hash(payload))
        assert success is True, f"Failed to insert record {i}"

        is_valid, _ = loop.run_until_complete(worker.verify_chain_integrity())
        assert is_valid is True, f"Chain broken after inserting record {i}"

    cursor.execute("SELECT COUNT(*) FROM swarm_reports")
    assert cursor.fetchone()[0] == 10

    is_valid, broken_id = loop.run_until_complete(worker.verify_chain_integrity())
    assert is_valid is True, f"Final chain validation failed at row {broken_id}"

    print("PASS: test_genesis_empty_to_populated_cycle")


def test_genesis_hash_determinism():
    """
    GENESIS TEST: Verify hash computation is deterministic.
    """
    payload_json = GENESIS_REPORT.to_json()

    h1 = compute_hash(payload_json, None)
    h2 = compute_hash(payload_json, None)
    h3 = compute_hash(payload_json, None)

    assert h1 == h2 == h3, "Hash computation must be deterministic"

    h4 = compute_hash(payload_json, h1)
    assert h4 != h1, "Chained hash must differ from unchained"

    print("PASS: test_genesis_hash_determinism")


def test_genesis_validator_comprehensive():
    """
    GENESIS TEST: Comprehensive validation of entire chain.
    """
    db = create_empty_database()
    redis = GenesisRedis()
    worker = MechanicWorker(redis, db)
    loop = asyncio.get_event_loop()

    records = []
    for i in range(20):
        payload = ReportPayload(
            query_hash=f"comprehensive_{i}",
            evidence_tier=["HIGH_AUTHORITY", "SUPPORTED", "CONFLICTED"][i % 3],
            execution_time=float(i * 2),
            report_data={"index": i, "data": f"Record {i} content"},
            created_at=time.time() + i,
        )
        loop.run_until_complete(worker._persist_with_hash(payload))
        records.append(payload)

    cursor = db.cursor()
    cursor.execute("""
        SELECT id, report_json, previous_hash, current_hash 
        FROM swarm_reports ORDER BY id
    """)
    rows = [
        {"id": r[0], "report_json": r[1], "previous_hash": r[2], "current_hash": r[3]}
        for r in cursor.fetchall()
    ]

    is_valid, broken_id = HashChainValidator.validate_chain(rows)
    assert is_valid is True, f"Chain invalid at row {broken_id}"
    assert len(rows) == 20

    cursor.execute("SELECT COUNT(*) FROM swarm_reports")
    assert cursor.fetchone()[0] == 20

    print("PASS: test_genesis_validator_comprehensive")


if __name__ == "__main__":
    test_genesis_first_insert()
    test_genesis_second_insert_chain()
    test_genesis_tamper_detection()
    test_genesis_empty_to_populated_cycle()
    test_genesis_hash_determinism()
    test_genesis_validator_comprehensive()
    print("\n=== ALL GENESIS TESTS PASSED ===")
