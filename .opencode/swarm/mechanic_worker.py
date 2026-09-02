"""
Mechanic Worker — SQLite Persistence Layer
Atomic processing queue, STRICT schema enforcement,
and cryptographic hash chaining for tamper-evident storage.
"""

import json
import hashlib
import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


# Queue keys
PERSISTENCE_QUEUE = "persistence_queue"
UNACKED_WRITES = "unacked_writes"
DEAD_LETTER_QUEUE = "mechanic_dlq"

# SQLite schema version for migration tracking
SCHEMA_VERSION = 1


class WriteStatus(Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True)
class ReportPayload:
    query_hash: str
    evidence_tier: str
    execution_time: float
    report_data: dict
    created_at: float
    previous_hash: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps({
            "query_hash": self.query_hash,
            "evidence_tier": self.evidence_tier,
            "execution_time": self.execution_time,
            "report_data": self.report_data,
            "created_at": self.created_at,
        }, sort_keys=True)

    @classmethod
    def from_json(cls, data: str) -> "ReportPayload":
        parsed = json.loads(data)
        return cls(
            query_hash=parsed["query_hash"],
            evidence_tier=parsed["evidence_tier"],
            execution_time=parsed["execution_time"],
            report_data=parsed["report_data"],
            created_at=parsed["created_at"],
        )


@dataclass(frozen=True)
class PersistedReport:
    row_id: int
    query_hash: str
    evidence_tier: str
    execution_time: float
    report_json: str
    previous_hash: Optional[str]
    current_hash: str
    created_at: float
    persisted_at: float

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "query_hash": self.query_hash,
            "evidence_tier": self.evidence_tier,
            "execution_time": self.execution_time,
            "report_json": self.report_json,
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash,
            "created_at": self.created_at,
            "persisted_at": self.persisted_at,
        }


# SQLite schema with STRICT mode and generated columns
CREATE_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS swarm_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT GENERATED ALWAYS AS (
        json_extract(report_json, '$.query_hash')
    ) STORED NOT NULL,
    evidence_tier TEXT GENERATED ALWAYS AS (
        json_extract(report_json, '$.evidence_tier')
    ) STORED NOT NULL,
    execution_time REAL GENERATED ALWAYS AS (
        json_extract(report_json, '$.execution_time')
    ) STORED NOT NULL,
    report_json TEXT NOT NULL,
    previous_hash TEXT,
    current_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    persisted_at REAL NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1
) STRICT;
"""

CREATE_REPORTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_swarm_reports_query_hash
    ON swarm_reports(query_hash);
CREATE INDEX IF NOT EXISTS idx_swarm_reports_evidence_tier
    ON swarm_reports(evidence_tier);
CREATE INDEX IF NOT EXISTS idx_swarm_reports_created_at
    ON swarm_reports(created_at);
CREATE INDEX IF NOT EXISTS idx_swarm_reports_current_hash
    ON swarm_reports(current_hash);
"""

CREATE_DLQ_TABLE = """
CREATE TABLE IF NOT EXISTS mechanic_dlq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload_json TEXT NOT NULL,
    error_reason TEXT NOT NULL,
    created_at REAL NOT NULL,
    retry_count INTEGER DEFAULT 0,
    last_retry_at REAL
) STRICT;
"""


def compute_hash(payload_json: str, previous_hash: Optional[str]) -> str:
    """
    Compute SHA-256 hash chain link.
    """
    data = payload_json
    if previous_hash:
        data += previous_hash
    return hashlib.sha256(data.encode()).hexdigest()


class HashChainValidator:
    """
    Validates cryptographic hash chain integrity.
    """

    @staticmethod
    def validate_chain(rows: list[dict]) -> tuple[bool, Optional[int]]:
        """
        Validate hash chain from start to finish.

        Returns:
            (is_valid, first_broken_row_id) or (True, None) if valid.
        """
        previous_hash = None

        for row in rows:
            expected_hash = compute_hash(
                row["report_json"], previous_hash
            )

            if row["current_hash"] != expected_hash:
                return False, row["id"]

            if row["previous_hash"] != previous_hash:
                return False, row["id"]

            previous_hash = row["current_hash"]

        return True, None

    @staticmethod
    def validate_single(
        report_json: str,
        previous_hash: Optional[str],
        current_hash: str,
    ) -> bool:
        """Validate a single row's hash."""
        expected = compute_hash(report_json, previous_hash)
        return expected == current_hash


class MechanicWorker:
    """
    Atomic persistence worker with reliable queue pattern.
    """

    def __init__(
        self,
        redis_client,
        sqlite_connection,
        max_retries: int = 3,
    ):
        self._redis = redis_client
        self._db = sqlite_connection
        self._max_retries = max_retries
        self._running = False
        self._validator = HashChainValidator()

    async def initialize(self) -> None:
        """Create tables and indexes."""
        cursor = self._db.cursor()
        cursor.execute(CREATE_REPORTS_TABLE)
        cursor.executescript(CREATE_REPORTS_INDEXES)
        cursor.execute(CREATE_DLQ_TABLE)
        self._db.commit()

    async def start(self) -> None:
        """Start the worker loop."""
        self._running = True
        await asyncio.gather(
            self._process_loop(),
            self._recovery_loop(),
        )

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False

    async def _process_loop(self) -> None:
        """Main processing loop with atomic queue operations."""
        while self._running:
            try:
                result = await self._redis.lmove(
                    PERSISTENCE_QUEUE,
                    UNACKED_WRITES,
                    timeout=5,
                )

                if not result:
                    continue

                payload_json = (
                    result.decode() if isinstance(result, bytes) else result
                )

                try:
                    payload = ReportPayload.from_json(payload_json)
                except (json.JSONDecodeError, KeyError) as e:
                    await self._send_to_dlq(payload_json, f"Parse error: {e}")
                    continue

                success = await self._persist_with_hash(payload)

                if success:
                    await self._redis.lrem(UNACKED_WRITES, 1, payload_json)
                else:
                    await self._send_to_dlq(payload_json, "SQLite write failed")

            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(1)

    async def _persist_with_hash(self, payload: ReportPayload) -> bool:
        """Persist report with hash chain."""
        try:
            previous_hash = await self._get_last_hash()
            current_hash = compute_hash(payload.to_json(), previous_hash)
            persisted_at = time.time()

            cursor = self._db.cursor()
            cursor.execute(
                """
                INSERT INTO swarm_reports
                (report_json, previous_hash, current_hash, created_at, persisted_at, schema_version)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.to_json(),
                    previous_hash,
                    current_hash,
                    payload.created_at,
                    persisted_at,
                    SCHEMA_VERSION,
                ),
            )
            self._db.commit()
            return True

        except Exception:
            self._db.rollback()
            return False

    async def _get_last_hash(self) -> Optional[str]:
        """Get the hash of the most recent report."""
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT current_hash FROM swarm_reports ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else None

    async def _send_to_dlq(self, payload_json: str, reason: str) -> None:
        """Send failed payload to dead letter queue."""
        try:
            cursor = self._db.cursor()
            cursor.execute(
                """
                INSERT INTO mechanic_dlq (payload_json, error_reason, created_at)
                VALUES (?, ?, ?)
                """,
                (payload_json, reason, time.time()),
            )
            self._db.commit()

            await self._redis.lrem(UNACKED_WRITES, 1, payload_json)

        except Exception:
            pass

    async def _recovery_loop(self) -> None:
        """Check for orphaned items in unacked_writes."""
        while self._running:
            try:
                await asyncio.sleep(30)

                unacked_items = await self._redis.lrange(UNACKED_WRITES, 0, -1)

                for item in unacked_items:
                    payload_json = (
                        item.decode() if isinstance(item, bytes) else item
                    )

                    cursor = self._db.cursor()
                    cursor.execute(
                        "SELECT id FROM swarm_reports WHERE report_json = ?",
                        (payload_json,),
                    )

                    if cursor.fetchone():
                        await self._redis.lrem(UNACKED_WRITES, 1, payload_json)
                    else:
                        await self._redis.lpush(PERSISTENCE_QUEUE, payload_json)
                        await self._redis.lrem(UNACKED_WRITES, 1, payload_json)

            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def verify_chain_integrity(self) -> tuple[bool, Optional[int]]:
        """Verify the entire hash chain is intact."""
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT id, report_json, previous_hash, current_hash FROM swarm_reports ORDER BY id"
        )
        rows = [
            {
                "id": r[0],
                "report_json": r[1],
                "previous_hash": r[2],
                "current_hash": r[3],
            }
            for r in cursor.fetchall()
        ]

        return self._validator.validate_chain(rows)

    async def get_report_by_hash(
        self, query_hash: str
    ) -> Optional[PersistedReport]:
        """Retrieve a report by query hash."""
        cursor = self._db.cursor()
        cursor.execute(
            """
            SELECT id, query_hash, evidence_tier, execution_time,
                   report_json, previous_hash, current_hash,
                   created_at, persisted_at
            FROM swarm_reports
            WHERE query_hash = ?
            ORDER BY persisted_at DESC
            LIMIT 1
            """,
            (query_hash,),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return PersistedReport(
            row_id=row[0],
            query_hash=row[1],
            evidence_tier=row[2],
            execution_time=row[3],
            report_json=row[4],
            previous_hash=row[5],
            current_hash=row[6],
            created_at=row[7],
            persisted_at=row[8],
        )

    async def get_dlq_items(self, limit: int = 50) -> list[dict]:
        """Retrieve dead letter queue items."""
        cursor = self._db.cursor()
        cursor.execute(
            """
            SELECT id, payload_json, error_reason, created_at, retry_count
            FROM mechanic_dlq
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        return [
            {
                "id": r[0],
                "payload_json": r[1],
                "error_reason": r[2],
                "created_at": r[3],
                "retry_count": r[4],
            }
            for r in cursor.fetchall()
        ]

    async def retry_dlq_item(self, item_id: int) -> bool:
        """Retry a dead letter queue item."""
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT payload_json, retry_count FROM mechanic_dlq WHERE id = ?",
            (item_id,),
        )
        row = cursor.fetchone()

        if not row:
            return False

        payload_json, retry_count = row

        if retry_count >= self._max_retries:
            return False

        cursor.execute(
            """
            UPDATE mechanic_dlq
            SET retry_count = retry_count + 1, last_retry_at = ?
            WHERE id = ?
            """,
            (time.time(), item_id),
        )
        self._db.commit()

        await self._redis.lpush(PERSISTENCE_QUEUE, payload_json)
        return True
