"""
Tests for Redis Streams and SSE components.
"""

import time
import json
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swarm.redis_streams import (
    SwarmStreamWriter,
    SwarmStreamReader,
    StreamOrchestrator,
    StreamEvent,
    StreamEventType,
    DEFAULT_MAXLEN,
)


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self._streams: dict[str, list[tuple[str, dict]]] = {}
        self._ttls: dict[str, int] = {}
        self._expiries: dict[str, float] = {}

    async def xadd(self, stream_name: str, fields: dict, maxlen: int = None) -> str:
        if stream_name not in self._streams:
            self._streams[stream_name] = []

        seq = len(self._streams[stream_name]) + 1
        event_id = f"{int(time.time())}-{seq}"

        self._streams[stream_name].append((event_id, fields))

        if maxlen and len(self._streams[stream_name]) > maxlen:
            self._streams[stream_name] = self._streams[stream_name][-maxlen:]

        return event_id

    async def xread(self, count: int = None, block: int = None, streams: dict = None) -> list:
        if not streams:
            return []

        stream_name = list(streams.keys())[0]
        last_id = list(streams.values())[0]

        if stream_name not in self._streams:
            return []

        messages = []
        for event_id, fields in self._streams[stream_name]:
            if event_id > last_id:
                messages.append((event_id.encode(), {k.encode(): v.encode() if isinstance(v, str) else v for k, v in fields.items()}))

        if messages:
            return [(stream_name.encode(), messages[:count or len(messages)])]
        return []

    async def expire(self, key: str, ttl: int) -> None:
        self._expiries[key] = time.time() + ttl

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._streams:
                del self._streams[key]
                count += 1
        return count


def test_stream_event_creation():
    event = StreamEvent(
        event_type=StreamEventType.PHASE_CHANGE,
        data={"phase": "VAULT_ONLY"},
        timestamp=time.time(),
        sequence=1,
    )
    assert event.event_type == StreamEventType.PHASE_CHANGE
    assert event.data["phase"] == "VAULT_ONLY"
    print("PASS: test_stream_event_creation")


def test_stream_event_redis_fields():
    event = StreamEvent(
        event_type=StreamEventType.COMPLETE,
        data={"verdict": "HIGH_AUTHORITY"},
        timestamp=time.time(),
        sequence=5,
    )
    fields = event.to_redis_fields()
    assert fields["event_type"] == "complete"
    assert json.loads(fields["data"])["verdict"] == "HIGH_AUTHORITY"
    print("PASS: test_stream_event_redis_fields")


def test_stream_event_from_redis_fields():
    fields = {
        "event_type": "phase",
        "data": json.dumps({"phase": "SPECULATIVE"}),
        "timestamp": str(time.time()),
        "sequence": "3",
    }
    event = StreamEvent.from_redis_fields(fields)
    assert event.event_type == StreamEventType.PHASE_CHANGE
    assert event.sequence == 3
    print("PASS: test_stream_event_from_redis_fields")


def test_writer_publish():
    redis = MockRedis()
    writer = SwarmStreamWriter(redis, max_len=100)

    loop = asyncio.get_event_loop()
    event_id = loop.run_until_complete(
        writer.publish("test_query", StreamEventType.PHASE_CHANGE, {"phase": "VAULT_ONLY"})
    )

    assert event_id is not None
    assert len(redis._streams) == 1
    print("PASS: test_writer_publish")


def test_writer_maxlen_bound():
    redis = MockRedis()
    writer = SwarmStreamWriter(redis, max_len=5)

    loop = asyncio.get_event_loop()
    for i in range(10):
        loop.run_until_complete(
            writer.publish("test_query", StreamEventType.HEARTBEAT, {"i": i})
        )

    stream_key = "run_events:test_query"
    assert len(redis._streams[stream_key]) <= 5
    print("PASS: test_writer_maxlen_bound")


def test_reader_subscribe():
    redis = MockRedis()
    writer = SwarmStreamWriter(redis, max_len=100)
    reader = SwarmStreamReader(redis)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(writer.publish("test_query", StreamEventType.COMPLETE, {"done": True}))

    async def read_events():
        events = []
        async for event in reader.subscribe("test_query"):
            events.append(event)
            if event.event_type == StreamEventType.COMPLETE:
                break
        return events

    events = loop.run_until_complete(read_events())
    assert len(events) == 1
    assert events[0].event_type == StreamEventType.COMPLETE
    print("PASS: test_reader_subscribe")


def test_reader_cursor_replay():
    redis = MockRedis()
    writer = SwarmStreamWriter(redis, max_len=100)
    reader = SwarmStreamReader(redis)

    loop = asyncio.get_event_loop()

    for i in range(5):
        loop.run_until_complete(
            writer.publish("test_query", StreamEventType.HEARTBEAT, {"i": i})
        )

    state = writer.get_state("test_query")
    cursor = state.last_event_id

    loop.run_until_complete(
        writer.publish("test_query", StreamEventType.COMPLETE, {"done": True})
    )

    events = loop.run_until_complete(reader.replay_from("test_query", cursor))
    assert len(events) == 1
    assert events[0].event_type == StreamEventType.COMPLETE
    print("PASS: test_reader_cursor_replay")


def test_tombstone_expiry():
    redis = MockRedis()
    writer = SwarmStreamWriter(redis, max_len=100, tombstone_ttl=60)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        writer.publish("test_query", StreamEventType.COMPLETE, {"done": True})
    )

    stream_key = "run_events:test_query"
    assert stream_key in redis._expiries
    print("PASS: test_tombstone_expiry")


def test_stream_orchestrator():
    redis = MockRedis()
    orchestrator = StreamOrchestrator(redis, max_len=100)

    loop = asyncio.get_event_loop()

    state = loop.run_until_complete(orchestrator.initialize_run("test_query"))
    assert state.query_hash == "test_query"

    event_id = loop.run_until_complete(
        orchestrator.publish_event("test_query", StreamEventType.PHASE_CHANGE, {"phase": "VAULT_ONLY"})
    )
    assert event_id is not None

    complete_id = loop.run_until_complete(
        orchestrator.complete_run("test_query", {"verdict": "HIGH_AUTHORITY"})
    )
    assert complete_id is not None

    print("PASS: test_stream_orchestrator")


if __name__ == "__main__":
    test_stream_event_creation()
    test_stream_event_redis_fields()
    test_stream_event_from_redis_fields()
    test_writer_publish()
    test_writer_maxlen_bound()
    test_reader_subscribe()
    test_reader_cursor_replay()
    test_tombstone_expiry()
    test_stream_orchestrator()
    print("\n=== ALL STREAM TESTS PASSED ===")
