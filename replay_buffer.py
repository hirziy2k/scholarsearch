import asyncio
import json
import time
from typing import List, Optional, AsyncGenerator
from dataclasses import dataclass

_redis = None
try:
    import redis.asyncio as redis
    _redis = redis
except ImportError:
    _redis = None


def _now():
    return time.time()


@dataclass
class Event:
    id: str
    type: str
    data: dict
    timestamp: float


class ReplayBuffer:
    """Persist SSE events to a temporary store so reconnecting clients
    can replay historical events before subscribing to live updates.

    For each job, stores the last 200 events in a bounded list.
    When a client reconnects, it instantly gets all past events,
    then seamlessly transitions to the live stream.
    """

    MAX_EVENTS_PER_JOB = 200
    EVENT_TTL_SECONDS = 3600  # 1 hour

    def __init__(self, redis_url: str = None):
        """Redis for distributed, memory dict fallback."""
        self._memory = {}
        self._ttl = {}
        self._redis = None
        self._redis_url = redis_url
        if redis_url and _redis is not None:
            self._redis = _redis.from_url(redis_url)

    # ---- helpers ----

    def _job_key(self, job_id: str) -> str:
        return f"replay:{job_id}"

    def _job_ttl_key(self, job_id: str) -> str:
        return f"replay_ttl:{job_id}"

    def _now(self) -> float:
        return time.time()

    async def append(self, job_id: str, event_type: str, data: dict,
                     event_id: str = None):
        """Append an event to the buffer.

        For Redis: LPUSH to list, trim to MAX_EVENTS, set TTL
        For memory: append to list, pop if > MAX
        """
        payload = {
            "id": event_id or self._gen_id(),
            "type": event_type,
            "data": data,
            "ts": self._now(),
        }
        if self._redis:
            key = self._job_key(job_id)
            ttl_key = self._job_ttl_key(job_id)
            await self._redis.lpush(key, json.dumps(payload))
            await self._redis.ltrim(key, 0, self.MAX_EVENTS_PER_JOB - 1)
            await self._redis.set(ttl_key, 1, ex=self.EVENT_TTL_SECONDS)
            return

        job = self._memory.get(job_id, [])
        job.append(payload)
        if len(job) > self.MAX_EVENTS_PER_JOB:
            del job[:-self.MAX_EVENTS_PER_JOB]
        self._memory[job_id] = job
        self._ttl[job_id] = self._now() + self.EVENT_TTL_SECONDS

    async def get_all(self, job_id: str, since_id: str = None) -> List[dict]:
        """Get all buffered events for a job.

        If since_id is provided, only return events after that ID.
        Used for partial replay (e.g., client got events 1-50, needs 51-N).
        """
        if self._redis:
            key = self._job_key(job_id)
            raw = await self._redis.lrange(key, 0, self.MAX_EVENTS_PER_JOB - 1)
            events = [json.loads(item) for item in raw]
            # LPUSH stores newest-first; return chronological
            events.reverse()
        else:
            events = list(self._memory.get(job_id, []))

        if since_id:
            idx = self._index_of(events, since_id)
            if idx is not None:
                events = events[idx + 1:]
            else:
                events = [e for e in events if not self._is_at_or_before(e, since_id)]

        return events

    async def get_current_phase(self, job_id: str) -> Optional[str]:
        """Get the current phase name for quick status."""
        events = await self.get_all(job_id)
        phase = None
        for event in events:
            if event.get("type") == "phase" or event.get("type") == "phase_change":
                phase = event.get("data", {}).get("phase") or event.get("data", {}).get("name")
            if event.get("type") == "status":
                data = event.get("data", {})
                phase = data.get("phase") or data.get("status") or phase
        return phase

    async def cleanup(self, job_id: str):
        """Remove all events for a job (after completion)."""
        if self._redis:
            key = self._job_key(job_id)
            ttl_key = self._job_ttl_key(job_id)
            await self._redis.delete(key, ttl_key)
            return
        self._memory.pop(job_id, None)
        self._ttl.pop(job_id, None)

    async def cleanup_expired(self) -> int:
        """Remove all expired job buffers. Returns count."""
        count = 0
        now = self._now()
        expired = [job for job, t in self._ttl.items() if t <= now]
        for job in expired:
            self._memory.pop(job, None)
            self._ttl.pop(job, None)
            count += 1

        if self._redis and _redis is not None:
            keys = []
            try:
                async for _ in self._redis.scan_iter(match="replay:*"):
                    keys.append(_)
            except Exception:
                pass
            for key in keys:
                try:
                    ttl = await self._redis.ttl(key)
                    if ttl < 0 and ttl != -1:
                        await self._redis.delete(key)
                        count += 1
                except Exception:
                    pass
        return count

    # ---- internal helpers ----

    @staticmethod
    def _gen_id() -> str:
        return f"evt-{int(time.time() * 1000)}-{int(id(object()) & 0xFFFF)}"

    @staticmethod
    def _index_of(events: List[dict], event_id: str) -> Optional[int]:
        for idx, event in enumerate(events):
            if event.get("id") == event_id:
                return idx
        return None

    @staticmethod
    def _is_at_or_before(event: dict, event_id: str) -> bool:
        return event.get("id") == event_id


class SSEReplayManager:
    """Combine ReplayBuffer with the live JobStreamManager.

    When a client connects to /v1/jobs/{id}/stream:
    1. Get all buffered historical events
    2. Replay them instantly (burst of events)
    3. Then subscribe to the live stream
    4. Client UI fast-forwards to current state, then updates live
    """

    def __init__(self, buffer: ReplayBuffer, stream_manager):
        self.buffer = buffer
        self.stream = stream_manager

    async def replay_and_subscribe(self, job_id: str,
                                    since_id: str = None) -> AsyncGenerator[str, None]:
        """Full replay-then-subscribe flow.

        Yields SSE-formatted strings:
        - First: replayed historical events (type: "replay")
        - Then: live events (type: "live")
        - Finally: "replay_complete" marker when transition happens
        """
        # 1. Get buffered events
        history = await self.buffer.get_all(job_id, since_id)

        for event in history:
            yield self._format_sse(event, is_replay=True)

        # 2. Yield replay_complete marker
        yield self._format_sse({
            "event": "replay_complete",
            "data": {
                "replayed_count": len(history),
                "phase": await self.buffer.get_current_phase(job_id),
            },
        }, is_replay=False)

        # 3. Subscribe to live stream
        async for event in self.stream.subscribe(job_id):
            yield self._format_sse(event, is_replay=False)
            # Also buffer this event for future reconnections
            await self.buffer.append(job_id, event.type, event.data)

    def _format_sse(self, event, is_replay: bool) -> str:
        """Format as SSE with replay flag."""
        event_type = getattr(event, "type", None) or (
            event.get("event") if isinstance(event, dict) else event.get("type")
        ) if isinstance(event, dict) else None
        data = getattr(event, "data", None) if not isinstance(event, dict) else event.get("data")

        if event_type is None and isinstance(event, dict):
            event_type = event.get("event") or event.get("type")
        if data is None and isinstance(event, dict):
            data = event.get("data")

        if event_type is None:
            event_type = "message"

        payload = data if data is not None else {}
        return (
            f"event: {event_type}\n"
            f"data: {json.dumps(payload)}\n"
            f"replay: {'true' if is_replay else 'false'}\n\n"
        )


if __name__ == "__main__":
    class FakeStream:
        def __init__(self, events):
            self._events = events

        async def subscribe(self, job_id):
            for ev in self._events:
                yield ev

    @dataclass
    class FakeEvent:
        type: str
        data: dict

    async def demo():
        buffer = ReplayBuffer()
        await buffer.append("job1", "status", {"phase": "started"})
        await buffer.append("job1", "status", {"phase": "parsing"}, event_id="evt-1")
        await buffer.append("job1", "status", {"phase": "converting"}, event_id="evt-2")

        stream = FakeStream([
            FakeEvent("status", {"phase": "done"}),
        ])
        manager = SSEReplayManager(buffer, stream)

        print("=== Full replay ===")
        async for chunk in manager.replay_and_subscribe("job1"):
            print(repr(chunk))

        print("=== Partial replay since evt-1 ===")
        async for chunk in manager.replay_and_subscribe("job1", since_id="evt-1"):
            print(repr(chunk))

        print("cleanup_expired:", await buffer.cleanup_expired())
        await buffer.cleanup("job1")
        print("job1 after cleanup:", await buffer.get_all("job1"))

    asyncio.run(demo())
