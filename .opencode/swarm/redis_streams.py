"""
Redis Streams Ephemeral State Layer
Provides bounded, rewindable state streaming for Swarm workers.
Connects headless execution to client SSE with frame-perfect replay.
"""

import time
import json
import asyncio
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator, Any
from enum import Enum


# Stream configuration
DEFAULT_MAXLEN = 1000
DEFAULT_BLOCK_MS = 0
DEFAULT_TOMBSTONE_TTL = 3600
STREAM_KEY_PREFIX = "run_events"
HEARTBEAT_INTERVAL = 5.0


class StreamEventType(Enum):
    PHASE_CHANGE = "phase"
    TRIAGE_RESULT = "triage"
    SWARM_PROGRESS = "progress"
    MATRIX_RESULT = "matrix"
    BOUNDARY_UPDATE = "boundary"
    HEARTBEAT = "heartbeat"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass(frozen=True)
class StreamEvent:
    event_type: StreamEventType
    data: dict
    timestamp: float
    sequence: int

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
        }

    def to_redis_fields(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "data": json.dumps(self.data),
            "timestamp": str(self.timestamp),
            "sequence": str(self.sequence),
        }

    @classmethod
    def from_redis_fields(cls, fields: dict) -> "StreamEvent":
        return cls(
            event_type=StreamEventType(fields["event_type"]),
            data=json.loads(fields["data"]),
            timestamp=float(fields["timestamp"]),
            sequence=int(fields["sequence"]),
        )


@dataclass
class StreamState:
    query_hash: str
    stream_key: str
    last_event_id: str
    sequence_counter: int
    started_at: float
    last_heartbeat: float

    def to_dict(self) -> dict:
        return {
            "query_hash": self.query_hash,
            "stream_key": self.stream_key,
            "last_event_id": self.last_event_id,
            "sequence_counter": self.sequence_counter,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
        }


class SwarmStreamWriter:
    """
    Writes bounded events to Redis Streams for Swarm state broadcasting.
    """

    def __init__(
        self,
        redis_client,
        max_len: int = DEFAULT_MAXLEN,
        tombstone_ttl: int = DEFAULT_TOMBSTONE_TTL,
    ):
        self._redis = redis_client
        self._max_len = max_len
        self._tombstone_ttl = tombstone_ttl
        self._states: dict[str, StreamState] = {}

    def _make_stream_key(self, query_hash: str) -> str:
        return f"{STREAM_KEY_PREFIX}:{query_hash}"

    async def initialize(self, query_hash: str) -> StreamState:
        """Initialize a new stream for a query."""
        stream_key = self._make_stream_key(query_hash)
        now = time.time()

        state = StreamState(
            query_hash=query_hash,
            stream_key=stream_key,
            last_event_id="0-0",
            sequence_counter=0,
            started_at=now,
            last_heartbeat=now,
        )
        self._states[query_hash] = state

        await self._redis.expire(stream_key, self._tombstone_ttl)

        return state

    async def publish(
        self,
        query_hash: str,
        event_type: StreamEventType,
        data: dict,
    ) -> str:
        """
        Publish an event to the stream.

        Returns the event ID for cursor tracking.
        """
        state = self._states.get(query_hash)
        if not state:
            state = await self.initialize(query_hash)

        state.sequence_counter += 1

        event = StreamEvent(
            event_type=event_type,
            data=data,
            timestamp=time.time(),
            sequence=state.sequence_counter,
        )

        event_id = await self._redis.xadd(
            state.stream_key,
            event.to_redis_fields(),
            maxlen=self._max_len,
        )

        state.last_event_id = event_id.decode() if isinstance(event_id, bytes) else event_id

        return state.last_event_id

    async def publish_heartbeat(self, query_hash: str) -> str:
        """Send a keepalive heartbeat to the stream."""
        state = self._states.get(query_hash)
        if state:
            state.last_heartbeat = time.time()

        return await self.publish(
            query_hash,
            StreamEventType.HEARTBEAT,
            {"status": "alive"},
        )

    async def publish_complete(
        self,
        query_hash: str,
        final_data: dict,
    ) -> str:
        """Publish final completion event."""
        event_id = await self.publish(
            query_hash,
            StreamEventType.COMPLETE,
            final_data,
        )

        state = self._states.get(query_hash)
        if state:
            await self._schedule_tombstone(state.stream_key)

        return event_id

    async def _schedule_tombstone(self, stream_key: str) -> None:
        """Schedule stream expiration after tombstone TTL."""
        await self._redis.expire(stream_key, self._tombstone_ttl)

    def get_state(self, query_hash: str) -> Optional[StreamState]:
        return self._states.get(query_hash)


class SwarmStreamReader:
    """
    Reads from Redis Streams with cursor-based rewind support.
    Handles client disconnects by replaying missed frames.
    """

    def __init__(
        self,
        redis_client,
        block_ms: int = DEFAULT_BLOCK_MS,
        heartbeat_timeout: float = HEARTBEAT_INTERVAL * 3,
    ):
        self._redis = redis_client
        self._block_ms = block_ms
        self._heartbeat_timeout = heartbeat_timeout
        self._active_subscriptions: dict[str, bool] = {}

    def _make_stream_key(self, query_hash: str) -> str:
        return f"{STREAM_KEY_PREFIX}:{query_hash}"

    async def subscribe(
        self,
        query_hash: str,
        cursor: Optional[str] = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Subscribe to a stream with optional cursor for replay.

        Args:
            query_hash: Query to subscribe to.
            cursor: Last received event ID (None = start from beginning).

        Yields:
            StreamEvent objects as they arrive.
        """
        stream_key = self._make_stream_key(query_hash)
        self._active_subscriptions[query_hash] = True

        last_id = cursor if cursor else "0"
        missed_count = 0

        try:
            while self._active_subscriptions.get(query_hash, False):
                try:
                    result = await self._redis.xread(
                        count=10,
                        block=self._block_ms,
                        streams={stream_key: last_id},
                    )

                    if not result:
                        continue

                    for stream_name, messages in result:
                        for message_id, fields in messages:
                            event_id = (
                                message_id.decode()
                                if isinstance(message_id, bytes)
                                else message_id
                            )

                            if event_id == last_id:
                                continue

                            last_id = event_id
                            missed_count = 0

                            event = StreamEvent.from_redis_fields(
                                {k.decode() if isinstance(k, bytes) else k:
                                 v.decode() if isinstance(v, bytes) else v
                                 for k, v in fields.items()}
                            )

                            yield event

                            if event.event_type == StreamEventType.COMPLETE:
                                return

                except asyncio.TimeoutError:
                    missed_count += 1
                    if missed_count * (self._block_ms / 1000) > self._heartbeat_timeout:
                        await self._handle_heartbeat_timeout(query_hash)
                        break

        finally:
            self._active_subscriptions[query_hash] = False

    async def _handle_heartbeat_timeout(self, query_hash: str) -> None:
        """Handle missed heartbeats by emitting timeout event."""
        pass

    async def unsubscribe(self, query_hash: str) -> None:
        """Stop subscribing to a stream."""
        self._active_subscriptions[query_hash] = False

    async def replay_from(
        self,
        query_hash: str,
        cursor: str,
    ) -> list[StreamEvent]:
        """
        Replay all events from a cursor position.
        Used for client reconnection.
        """
        stream_key = self._make_stream_key(query_hash)
        events = []

        try:
            result = await self._redis.xread(
                count=100,
                block=0,
                streams={stream_key: cursor},
            )

            if not result:
                return events

            for stream_name, messages in result:
                for message_id, fields in messages:
                    event_id = (
                        message_id.decode()
                        if isinstance(message_id, bytes)
                        else message_id
                    )

                    if event_id == cursor:
                        continue

                    event = StreamEvent.from_redis_fields(
                        {k.decode() if isinstance(k, bytes) else k:
                         v.decode() if isinstance(v, bytes) else v
                         for k, v in fields.items()}
                    )
                    events.append(event)

        except Exception:
            pass

        return events


class StreamOrchestrator:
    """
    Coordinates writers and readers for the ephemeral state layer.
    """

    def __init__(
        self,
        redis_client,
        max_len: int = DEFAULT_MAXLEN,
        tombstone_ttl: int = DEFAULT_TOMBSTONE_TTL,
        block_ms: int = DEFAULT_BLOCK_MS,
    ):
        self._redis = redis_client
        self._writer = SwarmStreamWriter(redis_client, max_len, tombstone_ttl)
        self._reader = SwarmStreamReader(redis_client, block_ms)

    async def initialize_run(self, query_hash: str) -> StreamState:
        """Initialize a new stream for a research run."""
        return await self._writer.initialize(query_hash)

    async def publish_event(
        self,
        query_hash: str,
        event_type: StreamEventType,
        data: dict,
    ) -> str:
        """Publish an event to the stream."""
        return await self._writer.publish(query_hash, event_type, data)

    async def subscribe(
        self,
        query_hash: str,
        cursor: Optional[str] = None,
    ) -> AsyncIterator[StreamEvent]:
        """Subscribe to a stream with optional cursor."""
        async for event in self._reader.subscribe(query_hash, cursor):
            yield event

    async def replay(
        self,
        query_hash: str,
        cursor: str,
    ) -> list[StreamEvent]:
        """Replay events from a cursor position."""
        return await self._reader.replay_from(query_hash, cursor)

    async def complete_run(
        self,
        query_hash: str,
        final_data: dict,
    ) -> str:
        """Mark a run as complete and schedule tombstone."""
        return await self._writer.publish_complete(query_hash, final_data)

    def get_stream_state(self, query_hash: str) -> Optional[StreamState]:
        """Get current stream state for a query."""
        return self._writer.get_state(query_hash)
