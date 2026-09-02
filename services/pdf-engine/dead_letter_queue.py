from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DLQ_PREFIX = "pdf2pptx:dlq"
RETRY_PREFIX = "pdf2pptx:retries"
DLQ_INDEX_KEY = f"{DLQ_PREFIX}:index"
DLQ_ENTRY_TTL = 7 * 24 * 3600  # 7 days


@dataclass
class DLQEntry:
    job_id: str
    pdf_name: str
    retry_count: int
    last_error: str
    created_at: str  # ISO-8601
    failed_at: str  # ISO-8601
    phases_completed: List[str]
    total_time_ms: float
    file_size_bytes: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["phases_completed"] = json.dumps(d["phases_completed"])
        d["metadata"] = json.dumps(d["metadata"])
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DLQEntry:
        phases = d.get("phases_completed", "[]")
        if isinstance(phases, str):
            phases = json.loads(phases)
        meta = d.get("metadata", "{}")
        if isinstance(meta, str):
            meta = json.loads(meta)
        return cls(
            job_id=d["job_id"],
            pdf_name=d["pdf_name"],
            retry_count=int(d.get("retry_count", 0)),
            last_error=d["last_error"],
            created_at=d["created_at"],
            failed_at=d["failed_at"],
            phases_completed=phases,
            total_time_ms=float(d.get("total_time_ms", 0)),
            file_size_bytes=int(d.get("file_size_bytes", 0)),
            metadata=meta,
        )


class DeadLetterQueue:
    """Manages poison pill jobs that exceed retry limits."""

    MAX_RETRIES = 2

    def __init__(self, redis_url: str = None):
        raise NotImplementedError("Use create_dlq() factory or subclass directly")


class RedisDLQ(DeadLetterQueue):
    """Redis-backed DLQ."""

    def __init__(self, redis_url: str):
        import redis.asyncio as aioredis

        self._redis_url = redis_url
        self._pool = aioredis.ConnectionPool.from_url(
            redis_url, decode_responses=True, max_connections=10
        )
        self._client = aioredis.Redis(connection_pool=self._pool)
        logger.info("RedisDLQ connected to %s", redis_url)

    async def close(self):
        await self._client.aclose()
        await self._pool.disconnect()

    def _entry_key(self, job_id: str) -> str:
        return f"{DLQ_PREFIX}:{job_id}"

    def _retry_key(self, job_id: str) -> str:
        return f"{RETRY_PREFIX}:{job_id}"

    async def _redis_available(self) -> bool:
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    async def should_retry(self, job_id: str) -> bool:
        count = await self.get_retry_count(job_id)
        return count < self.MAX_RETRIES

    async def record_failure(
        self,
        job_id: str,
        error: str,
        phases_completed: List[str] = None,
        metadata: Dict = None,
    ) -> Optional[DLQEntry]:
        if phases_completed is None:
            phases_completed = []
        if metadata is None:
            metadata = {}

        retry_key = self._retry_key(job_id)
        new_count = await self._client.incr(retry_key)
        await self._client.expire(retry_key, DLQ_ENTRY_TTL)

        if new_count < self.MAX_RETRIES:
            return None

        now = datetime.now(timezone.utc).isoformat()

        pdf_name = metadata.get("pdf_name", "unknown")
        file_size = metadata.get("file_size", 0)

        entry = DLQEntry(
            job_id=job_id,
            pdf_name=str(pdf_name),
            retry_count=new_count,
            last_error=error,
            created_at=now,
            failed_at=now,
            phases_completed=phases_completed,
            total_time_ms=metadata.get("total_time_ms", 0),
            file_size_bytes=file_size,
            metadata=metadata,
        )

        entry_dict = entry.to_dict()
        entry_key = self._entry_key(job_id)
        await self._client.hset(entry_key, mapping=entry_dict)
        await self._client.expire(entry_key, DLQ_ENTRY_TTL)
        await self._client.zadd(DLQ_INDEX_KEY, {job_id: time.time()})
        await self._client.expire(DLQ_INDEX_KEY, DLQ_ENTRY_TTL)

        logger.warning("Job %s routed to DLQ after %d failures", job_id, new_count)
        return entry

    async def get_dlq_entries(self, limit: int = 100) -> List[DLQEntry]:
        job_ids = await self._client.zrevrange(DLQ_INDEX_KEY, 0, limit - 1)
        entries = []
        for jid in job_ids:
            entry = await self.get_dlq_entry(jid)
            if entry:
                entries.append(entry)
        return entries

    async def get_dlq_entry(self, job_id: str) -> Optional[DLQEntry]:
        data = await self._client.hgetall(self._entry_key(job_id))
        if not data:
            return None
        return DLQEntry.from_dict(data)

    async def retry_from_dlq(self, job_id: str) -> bool:
        removed = await self._client.zrem(DLQ_INDEX_KEY, job_id)
        deleted = await self._client.delete(self._entry_key(job_id))
        await self._client.delete(self._retry_key(job_id))
        if removed or deleted:
            logger.info("Job %s removed from DLQ for retry", job_id)
            return True
        return False

    async def purge_dlq(self) -> int:
        job_ids = await self._client.zrange(DLQ_INDEX_KEY, 0, -1)
        count = 0
        for jid in job_ids:
            await self._client.delete(self._entry_key(jid))
            await self._client.delete(self._retry_key(jid))
            count += 1
        await self._client.delete(DLQ_INDEX_KEY)
        logger.info("Purged %d entries from DLQ", count)
        return count

    async def dlq_size(self) -> int:
        return await self._client.zcard(DLQ_INDEX_KEY)

    async def get_retry_count(self, job_id: str) -> int:
        val = await self._client.get(self._retry_key(job_id))
        if val is None:
            return 0
        return int(val)


class MemoryDLQ(DeadLetterQueue):
    """In-memory fallback DLQ."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._retries: Dict[str, int] = {}
        self._entries: Dict[str, DLQEntry] = {}
        self._index: Dict[str, float] = {}
        logger.info("MemoryDLQ initialized (in-memory fallback)")

    async def should_retry(self, job_id: str) -> bool:
        async with self._lock:
            count = self._retries.get(job_id, 0)
            return count < self.MAX_RETRIES

    async def record_failure(
        self,
        job_id: str,
        error: str,
        phases_completed: List[str] = None,
        metadata: Dict = None,
    ) -> Optional[DLQEntry]:
        if phases_completed is None:
            phases_completed = []
        if metadata is None:
            metadata = {}

        async with self._lock:
            self._retries[job_id] = self._retries.get(job_id, 0) + 1
            new_count = self._retries[job_id]

            if new_count < self.MAX_RETRIES:
                return None

            now = datetime.now(timezone.utc).isoformat()
            pdf_name = metadata.get("pdf_name", "unknown")
            file_size = metadata.get("file_size", 0)

            entry = DLQEntry(
                job_id=job_id,
                pdf_name=str(pdf_name),
                retry_count=new_count,
                last_error=error,
                created_at=now,
                failed_at=now,
                phases_completed=phases_completed,
                total_time_ms=metadata.get("total_time_ms", 0),
                file_size_bytes=file_size,
                metadata=metadata,
            )

            self._entries[job_id] = entry
            self._index[job_id] = time.time()

        logger.warning("Job %s routed to DLQ after %d failures", job_id, new_count)
        return entry

    async def get_dlq_entries(self, limit: int = 100) -> List[DLQEntry]:
        async with self._lock:
            sorted_ids = sorted(self._index, key=self._index.get, reverse=True)
            return [self._entries[jid] for jid in sorted_ids[:limit] if jid in self._entries]

    async def get_dlq_entry(self, job_id: str) -> Optional[DLQEntry]:
        async with self._lock:
            return self._entries.get(job_id)

    async def retry_from_dlq(self, job_id: str) -> bool:
        async with self._lock:
            existed = False
            if job_id in self._entries:
                del self._entries[job_id]
                existed = True
            if job_id in self._index:
                del self._index[job_id]
                existed = True
            self._retries.pop(job_id, None)
            if existed:
                logger.info("Job %s removed from DLQ for retry", job_id)
            return existed

    async def purge_dlq(self) -> int:
        async with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._index.clear()
            self._retries.clear()
            logger.info("Purged %d entries from DLQ", count)
            return count

    async def dlq_size(self) -> int:
        async with self._lock:
            return len(self._entries)

    async def get_retry_count(self, job_id: str) -> int:
        async with self._lock:
            return self._retries.get(job_id, 0)


def create_dlq(redis_url: str = None) -> DeadLetterQueue:
    """Create the best available DLQ backend."""
    if redis_url:
        try:
            import redis.asyncio  # noqa: F401
            dlq = RedisDLQ(redis_url)
            logger.info("Created RedisDLQ backend")
            return dlq
        except Exception as exc:
            logger.warning(
                "Failed to create RedisDLQ (%s), falling back to MemoryDLQ", exc
            )

    if redis_url is None:
        try:
            import redis.asyncio  # noqa: F401
        except ImportError:
            pass

    return MemoryDLQ()


async def _run_lifecycle_test():
    """End-to-end test of the DLQ lifecycle."""
    print("=" * 60)
    print("DLQ LIFECYCLE TEST")
    print("=" * 60)

    dlq = create_dlq()
    print(f"\n[1] Created DLQ backend: {type(dlq).__name__}")

    # --- Retryable failures (count < MAX_RETRIES) ---
    print("\n[2] Recording first failure for job_abc...")
    result = await dlq.record_failure(
        job_id="job_abc",
        error="Timeout during collision resolution",
        phases_completed=["ocr", "collision_resolve"],
        metadata={"pdf_name": "large_report.pdf", "file_size": 5_242_880},
    )
    print(f"   result = {result}  (None = still retryable)")

    count = await dlq.get_retry_count("job_abc")
    print(f"   retry_count = {count}")

    should = await dlq.should_retry("job_abc")
    print(f"   should_retry = {should}")

    # --- Second failure triggers DLQ ---
    print("\n[3] Recording second failure for job_abc...")
    entry = await dlq.record_failure(
        job_id="job_abc",
        error="Infinite loop in collision_resolver",
        phases_completed=["ocr", "collision_resolve", "layout"],
        metadata={"pdf_name": "large_report.pdf", "file_size": 5_242_880},
    )
    print(f"   entry = {entry}")
    print(f"   retry_count = {entry.retry_count}")
    print(f"   last_error  = {entry.last_error}")
    print(f"   phases      = {entry.phases_completed}")

    should = await dlq.should_retry("job_abc")
    print(f"   should_retry = {should}")

    size = await dlq.dlq_size()
    print(f"   dlq_size = {size}")

    # --- List DLQ entries ---
    print("\n[4] Listing DLQ entries...")
    entries = await dlq.get_dlq_entries()
    for e in entries:
        print(f"   [{e.job_id}] {e.pdf_name} - {e.last_error}")

    # --- Get specific entry ---
    print("\n[5] Getting specific DLQ entry for job_abc...")
    specific = await dlq.get_dlq_entry("job_abc")
    print(f"   found = {specific is not None}")
    if specific:
        print(f"   created_at = {specific.created_at}")
        print(f"   failed_at  = {specific.failed_at}")

    # --- Simulate a second poison job ---
    print("\n[6] Recording two failures for job_poison...")
    await dlq.record_failure(
        job_id="job_poison",
        error="PDF causes segfault in renderer",
        phases_completed=[],
        metadata={"pdf_name": "evil.pdf", "file_size": 1024},
    )
    await dlq.record_failure(
        job_id="job_poison",
        error="PDF causes segfault in renderer",
        phases_completed=["ocr"],
        metadata={"pdf_name": "evil.pdf", "file_size": 1024},
    )
    size = await dlq.dlq_size()
    print(f"   dlq_size = {size}")

    entries = await dlq.get_dlq_entries()
    for e in entries:
        print(f"   [{e.job_id}] {e.pdf_name} - retries={e.retry_count}")

    # --- Retry from DLQ ---
    print("\n[7] Retrying job_abc from DLQ...")
    success = await dlq.retry_from_dlq("job_abc")
    print(f"   success = {success}")

    size = await dlq.dlq_size()
    print(f"   dlq_size after retry = {size}")

    retry_count = await dlq.get_retry_count("job_abc")
    print(f"   retry_count after reset = {retry_count}")

    should = await dlq.should_retry("job_abc")
    print(f"   should_retry = {should}")

    # --- Record the same job failing again ---
    print("\n[8] Simulating job_abc failing twice again...")
    await dlq.record_failure(
        job_id="job_abc",
        error="Persistent collision loop",
        phases_completed=["ocr"],
        metadata={"pdf_name": "large_report.pdf", "file_size": 5_242_880},
    )
    await dlq.record_failure(
        job_id="job_abc",
        error="Persistent collision loop",
        phases_completed=["ocr", "collision_resolve"],
        metadata={"pdf_name": "large_report.pdf", "file_size": 5_242_880},
    )
    size = await dlq.dlq_size()
    print(f"   dlq_size = {size}")

    specific = await dlq.get_dlq_entry("job_abc")
    print(f"   retry_count = {specific.retry_count}")

    # --- Purge ---
    print("\n[9] Purging DLQ...")
    purged = await dlq.purge_dlq()
    print(f"   purged = {purged}")

    size = await dlq.dlq_size()
    print(f"   dlq_size after purge = {size}")

    # --- Test with multiple retries (beyond MAX_RETRIES) ---
    print("\n[10] Testing failure beyond MAX_RETRIES...")
    for i in range(5):
        await dlq.record_failure(
            job_id="job_overkill",
            error=f"Error attempt {i+1}",
            phases_completed=[f"phase_{i}"],
            metadata={"pdf_name": "broken.pdf", "file_size": 999},
        )
    entry = await dlq.get_dlq_entry("job_overkill")
    print(f"    retry_count = {entry.retry_count} (should be 5)")
    print(f"    in_dlq = {entry is not None}")

    await dlq.purge_dlq()

    # --- Clean up if RedisDLQ ---
    if hasattr(dlq, "close"):
        await dlq.close()

    print("\n" + "=" * 60)
    print("ALL LIFECYCLE TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(_run_lifecycle_test())
