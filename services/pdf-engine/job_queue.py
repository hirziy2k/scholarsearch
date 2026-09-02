"""
Persistent Job Queue
====================

Redis-backed (with in-memory fallback) job queue for the PDF-to-PPTX
conversion API.  Survives pod evictions, restarts, and memory pressure
when Redis is available; degrades gracefully to an in-memory dict otherwise.

Quickstart
----------
    python job_queue.py            # standalone smoke test
    # or import and use:
    queue = create_queue()        # auto-selects backend
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Job:
    job_id: str
    status: str = "queued"  # queued | processing | completed | failed | cancelled
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    pdf_name: str = ""
    file_path: str = ""
    output_path: Optional[str] = None
    webhook_url: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None

    # -- serialisation helpers -------------------------------------------------

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "Job":
        d = json.loads(raw)
        return cls(**d)


# ---------------------------------------------------------------------------
# Abstract queue interface
# ---------------------------------------------------------------------------

class JobQueue(ABC):
    @abstractmethod
    async def enqueue(self, job: Job) -> str:
        ...

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Job]:
        ...

    @abstractmethod
    async def update_job(self, job_id: str, **fields: Any) -> None:
        ...

    @abstractmethod
    async def set_status(self, job_id: str, status: str) -> None:
        ...

    @abstractmethod
    async def complete_job(self, job_id: str, result: dict) -> None:
        ...

    @abstractmethod
    async def fail_job(self, job_id: str, error: str) -> None:
        ...

    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    async def list_jobs(self, status: Optional[str] = None, limit: int = 100) -> List[Job]:
        ...

    @abstractmethod
    async def queue_size(self) -> int:
        ...

    @abstractmethod
    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        ...

    # -- locking (optional, noop for memory) ----------------------------------

    async def acquire_lock(self, job_id: str) -> bool:
        return True

    async def release_lock(self, job_id: str) -> None:
        pass


# ---------------------------------------------------------------------------
# Redis implementation
# ---------------------------------------------------------------------------

class RedisJobQueue(JobQueue):
    """Redis-backed persistent job queue using ``redis.asyncio``."""

    _PREFIX = "pdf2pptx"
    _DEFAULT_TTL = 86400  # 24 h
    _LOCK_TTL = 30  # seconds
    _DEFAULT_REDIS_URL = "redis://localhost:6379"

    def __init__(self, redis_url: Optional[str] = None) -> None:
        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "redis.asyncio is required for RedisJobQueue.  "
                "Install with: pip install redis"
            ) from exc

        self._url = redis_url or os.getenv("REDIS_URL", self._DEFAULT_REDIS_URL)
        self._pool = aioredis.ConnectionPool.from_url(
            self._url, max_connections=10, decode_responses=True
        )
        self._redis = aioredis.Redis(connection_pool=self._pool)
        self._ttl = self._DEFAULT_TTL
        logger.info("RedisJobQueue connected to %s", self._url)

    # -- key helpers ----------------------------------------------------------

    def _job_key(self, job_id: str) -> str:
        return f"{self._PREFIX}:jobs:{job_id}"

    def _lock_key(self, job_id: str) -> str:
        return f"{self._PREFIX}:lock:{job_id}"

    def _index_key(self, status: str) -> str:
        return f"{self._PREFIX}:{status}"

    def _ts(self) -> float:
        return time.time()

    # -- public API -----------------------------------------------------------

    async def enqueue(self, job: Job) -> str:
        if not job.created_at:
            job.created_at = datetime.now(timezone.utc).isoformat()
        if not job.job_id:
            job.job_id = str(uuid.uuid4())

        pipe = self._redis.pipeline(transaction=True)
        pipe.set(self._job_key(job.job_id), job.to_json(), ex=self._ttl)
        pipe.zadd(self._index_key("queue"), {job.job_id: self._ts()})
        await pipe.execute()
        return job.job_id

    async def get_job(self, job_id: str) -> Optional[Job]:
        raw = await self._redis.get(self._job_key(job_id))
        if raw is None:
            return None
        return Job.from_json(raw)

    async def update_job(self, job_id: str, **fields: Any) -> None:
        raw = await self._redis.get(self._job_key(job_id))
        if raw is None:
            return
        job = Job.from_json(raw)
        for k, v in fields.items():
            if hasattr(job, k):
                setattr(job, k, v)
        await self._redis.set(self._job_key(job_id), job.to_json(), ex=self._ttl)

    async def set_status(self, job_id: str, status: str) -> None:
        raw = await self._redis.get(self._job_key(job_id))
        if raw is None:
            return
        job = Job.from_json(raw)
        old_status = job.status
        job.status = status

        pipe = self._redis.pipeline(transaction=True)
        pipe.set(self._job_key(job_id), job.to_json(), ex=self._ttl)

        # move between sorted-set indexes
        old_idx = self._index_key(old_status)
        new_idx = self._index_key(status)
        pipe.zrem(old_idx, job_id)
        pipe.zadd(new_idx, {job_id: self._ts()})

        await pipe.execute()

    async def complete_job(self, job_id: str, result: dict) -> None:
        raw = await self._redis.get(self._job_key(job_id))
        if raw is None:
            return
        job = Job.from_json(raw)
        job.status = "completed"
        job.result = result
        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.progress = 1.0

        pipe = self._redis.pipeline(transaction=True)
        pipe.set(self._job_key(job_id), job.to_json(), ex=self._ttl)
        pipe.zrem(self._index_key("queued"), job_id)
        pipe.zrem(self._index_key("processing"), job_id)
        pipe.zadd(self._index_key("completed"), {job_id: self._ts()})
        await pipe.execute()

    async def fail_job(self, job_id: str, error: str) -> None:
        raw = await self._redis.get(self._job_key(job_id))
        if raw is None:
            return
        job = Job.from_json(raw)
        job.status = "failed"
        job.error = error
        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.progress = 1.0

        pipe = self._redis.pipeline(transaction=True)
        pipe.set(self._job_key(job_id), job.to_json(), ex=self._ttl)
        pipe.zrem(self._index_key("queued"), job_id)
        pipe.zrem(self._index_key("processing"), job_id)
        pipe.zadd(self._index_key("failed"), {job_id: self._ts()})
        await pipe.execute()

    async def cancel_job(self, job_id: str) -> bool:
        raw = await self._redis.get(self._job_key(job_id))
        if raw is None:
            return False
        job = Job.from_json(raw)
        if job.status in ("completed", "failed", "cancelled"):
            return False

        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc).isoformat()

        pipe = self._redis.pipeline(transaction=True)
        pipe.set(self._job_key(job_id), job.to_json(), ex=self._ttl)
        pipe.zrem(self._index_key("queued"), job_id)
        pipe.zrem(self._index_key("processing"), job_id)
        pipe.zadd(self._index_key("cancelled"), {job_id: self._ts()})
        await pipe.execute()
        return True

    async def list_jobs(self, status: Optional[str] = None, limit: int = 100) -> List[Job]:
        if status:
            ids = await self._redis.zrange(self._index_key(status), 0, limit - 1)
        else:
            # combine all known indexes
            ids: list[str] = []  # type: ignore[no-redef]
            for s in ("queued", "processing", "completed", "failed", "cancelled"):
                part = await self._redis.zrange(self._index_key(s), 0, limit - 1)
                ids.extend(part)
            ids = ids[:limit]

        jobs: List[Job] = []
        if not ids:
            return jobs
        raw_list = await self._redis.mget(self._job_key(jid) for jid in ids)
        for raw in raw_list:
            if raw is not None:
                jobs.append(Job.from_json(raw))
        return jobs

    async def queue_size(self) -> int:
        return await self._redis.zcard(self._index_key("queued"))

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        cutoff = self._ts() - (max_age_hours * 3600)
        removed = 0
        for suffix in ("queue", "processing", "completed", "failed", "cancelled"):
            idx = self._index_key(suffix)
            stale = await self._redis.zrangebyscore(idx, "-inf", cutoff)
            if stale:
                pipe = self._redis.pipeline(transaction=True)
                for jid in stale:
                    pipe.delete(self._job_key(jid))
                pipe.zrem(idx, *stale)
                await pipe.execute()
                removed += len(stale)
        return removed

    # -- distributed locking --------------------------------------------------

    async def acquire_lock(self, job_id: str) -> bool:
        result = await self._redis.set(
            self._lock_key(job_id), "1", nx=True, ex=self._LOCK_TTL
        )
        return result is not None

    async def release_lock(self, job_id: str) -> None:
        await self._redis.delete(self._lock_key(job_id))


# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------

class MemoryJobQueue(JobQueue):
    """Dict-backed in-memory job queue.

    Emitted as a fallback when Redis is unreachable.
    """

    def __init__(self) -> None:
        logger.warning(
            "Redis unavailable \u2014 jobs will not survive restarts.  "
            "Set REDIS_URL to enable persistence."
        )
        self._jobs: Dict[str, Job] = {}
        self._indexes: Dict[str, List[str]] = {
            "queue": [],
            "processing": [],
            "completed": [],
            "failed": [],
            "cancelled": [],
        }
        self._lock = asyncio.Lock()

    # -- helpers --------------------------------------------------------------

    def _remove_from_all_indexes(self, job_id: str) -> None:
        for ids in self._indexes.values():
            if job_id in ids:
                ids.remove(job_id)

    # -- public API -----------------------------------------------------------

    async def enqueue(self, job: Job) -> str:
        async with self._lock:
            if not job.created_at:
                job.created_at = datetime.now(timezone.utc).isoformat()
            if not job.job_id:
                job.job_id = str(uuid.uuid4())
            self._jobs[job.job_id] = job
            self._indexes["queue"].append(job.job_id)
            return job.job_id

    async def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def update_job(self, job_id: str, **fields: Any) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for k, v in fields.items():
                if hasattr(job, k):
                    setattr(job, k, v)

    async def set_status(self, job_id: str, status: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            old = job.status
            job.status = status
            self._remove_from_all_indexes(job_id)
            self._indexes.setdefault(status, []).append(job_id)

    async def complete_job(self, job_id: str, result: dict) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "completed"
            job.result = result
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.progress = 1.0
            self._remove_from_all_indexes(job_id)
            self._indexes["completed"].append(job_id)

    async def fail_job(self, job_id: str, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "failed"
            job.error = error
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.progress = 1.0
            self._remove_from_all_indexes(job_id)
            self._indexes["failed"].append(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in ("completed", "failed", "cancelled"):
                return False
            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            self._remove_from_all_indexes(job_id)
            self._indexes["cancelled"].append(job_id)
            return True

    async def list_jobs(self, status: Optional[str] = None, limit: int = 100) -> List[Job]:
        if status:
            ids = self._indexes.get(status, [])[:limit]
        else:
            ids = []
            for s in ("queued", "processing", "completed", "failed", "cancelled"):
                ids.extend(self._indexes.get(s, []))
            ids = ids[:limit]
        return [self._jobs[jid] for jid in ids if jid in self._jobs]

    async def queue_size(self) -> int:
        return len(self._indexes.get("queue", []))

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        async with self._lock:
            stale_ids: list[str] = []
            for jid, job in self._jobs.items():
                try:
                    created = datetime.fromisoformat(job.created_at).timestamp()
                except (ValueError, TypeError):
                    continue
                if created < cutoff:
                    stale_ids.append(jid)
            for jid in stale_ids:
                self._remove_from_all_indexes(jid)
                del self._jobs[jid]
                removed += 1
        return removed


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_queue(redis_url: Optional[str] = None) -> JobQueue:
    """Create the best available queue backend.

    Tries Redis first; falls back to an in-memory dict on any error.
    """
    url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        q = RedisJobQueue(redis_url=url)
        return q
    except Exception as exc:
        logger.warning(
            "Could not initialise Redis queue (%s). Falling back to memory.", exc
        )
        return MemoryJobQueue()


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    async def _demo() -> None:
        queue = create_queue()
        print(f"Backend: {type(queue).__name__}")

        # Create 5 jobs
        job_ids: list[str] = []
        for i in range(5):
            job = Job(
                job_id="",
                pdf_name=f"report_{i}.pdf",
                file_path=f"/tmp/report_{i}.pdf",
            )
            jid = await queue.enqueue(job)
            job_ids.append(jid)
            print(f"  enqueued {jid}")

        # Complete each
        for jid in job_ids:
            await queue.set_status(jid, "processing")
            await queue.update_job(jid, progress=0.5)
            await queue.complete_job(jid, {"output_path": f"/tmp/{jid}.pptx"})
            print(f"  completed {jid}")

        # List all completed
        completed = await queue.list_jobs(status="completed")
        print(f"Completed jobs: {len(completed)}")

        # Queue size (should be 0)
        sz = await queue.queue_size()
        print(f"Queue size: {sz}")

        # Cleanup
        removed = await queue.cleanup_old_jobs(max_age_hours=0)
        print(f"Cleaned up {removed} old jobs")

        final = await queue.list_jobs()
        print(f"Jobs remaining: {len(final)}")

    asyncio.run(_demo())
