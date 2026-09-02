"""
Liveness Heartbeat Mutex with Lua CAS
Prevents poisoned locks and split-brain scenarios in distributed Swarm execution.
"""

import time
import uuid
import asyncio
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable


# Lua script for atomic check-and-set
# Returns 1 if lock extended, 0 if lock belongs to another owner
LUA_CAS_HEARTBEAT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    redis.call("EXPIRE", KEYS[1], ARGV[2])
    return 1
else
    return 0
end
"""

# Lua script for safe release (only release if I own it)
LUA_SAFE_RELEASE = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


@dataclass(frozen=True)
class MutexState:
    lock_key: str
    owner_uuid: str
    acquired_at: float
    ttl_seconds: int
    is_mine: bool

    def to_dict(self) -> dict:
        return {
            "lock_key": self.lock_key,
            "owner_uuid": self.owner_uuid,
            "acquired_at": self.acquired_at,
            "ttl_seconds": self.ttl_seconds,
            "is_mine": self.is_mine,
        }


class HeartbeatMutex:
    """
    Distributed mutex with automatic expiration and ownership verification.

    Uses Lua CAS scripts to prevent split-brain scenarios where
    delayed heartbeats extend another owner's lock.
    """

    def __init__(
        self,
        redis_client,
        key_prefix: str = "in_flight",
        ttl_seconds: int = 5,
        heartbeat_interval: float = 3.0,
    ):
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds
        self._heartbeat_interval = heartbeat_interval

        self._owner_uuid: Optional[str] = None
        self._lock_key: Optional[str] = None
        self._acquired_at: Optional[float] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    def _make_key(self, query_hash: str) -> str:
        return f"{self._key_prefix}:{query_hash}"

    async def acquire(
        self,
        query_hash: str,
        on_expire: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> bool:
        """
        Attempt to acquire lock for a query hash.

        Args:
            query_hash: Hash identifying the query.
            on_expire: Callback if lock expires during operation.

        Returns:
            True if lock acquired, False if another worker holds it.
        """
        self._owner_uuid = str(uuid.uuid4())
        self._lock_key = self._make_key(query_hash)
        self._acquired_at = time.time()

        result = await self._redis.set(
            self._lock_key,
            self._owner_uuid,
            ex=self._ttl_seconds,
            nx=True,
        )

        if result:
            self._running = True
            self._heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(query_hash, on_expire)
            )
            return True

        return False

    async def release(self) -> bool:
        """Release lock only if I still own it."""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if not self._lock_key or not self._owner_uuid:
            return False

        result = await self._redis.eval(
            LUA_SAFE_RELEASE,
            1,
            self._lock_key,
            self._owner_uuid,
        )

        self._owner_uuid = None
        self._lock_key = None
        self._acquired_at = None

        return bool(result)

    async def _heartbeat_loop(
        self,
        query_hash: str,
        on_expire: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """Extend lock every heartbeat_interval seconds."""
        try:
            while self._running:
                await asyncio.sleep(self._heartbeat_interval)

                if not self._running or not self._lock_key:
                    break

                result = await self._redis.eval(
                    LUA_CAS_HEARTBEAT,
                    1,
                    self._lock_key,
                    self._owner_uuid,
                    self._ttl_seconds,
                )

                if not result:
                    self._running = False
                    if on_expire:
                        await on_expire()
                    break

        except asyncio.CancelledError:
            pass

    def get_state(self) -> Optional[MutexState]:
        """Return current mutex state for debugging."""
        if not self._lock_key or not self._owner_uuid:
            return None

        return MutexState(
            lock_key=self._lock_key,
            owner_uuid=self._owner_uuid,
            acquired_at=self._acquired_at or 0.0,
            ttl_seconds=self._ttl_seconds,
            is_mine=self._running,
        )


class LockManager:
    """
    Manages multiple HeartbeatMutex instances for concurrent queries.
    """

    def __init__(self, redis_client, **mutex_kwargs):
        self._redis = redis_client
        self._mutex_kwargs = mutex_kwargs
        self._locks: dict[str, HeartbeatMutex] = {}

    def get_mutex(self, query_hash: str) -> HeartbeatMutex:
        if query_hash not in self._locks:
            self._locks[query_hash] = HeartbeatMutex(
                self._redis, **self._mutex_kwargs
            )
        return self._locks[query_hash]

    async def try_acquire(
        self,
        query_hash: str,
        on_expire: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> tuple[bool, HeartbeatMutex]:
        mutex = self.get_mutex(query_hash)
        acquired = await mutex.acquire(query_hash, on_expire)
        return acquired, mutex

    async def release_all(self) -> None:
        for mutex in self._locks.values():
            await mutex.release()
        self._locks.clear()
