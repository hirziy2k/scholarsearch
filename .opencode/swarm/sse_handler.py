"""
SSE Endpoint for Swarm State Streaming
Connects Redis Streams to client UI with cursor-based frame replay.
"""

import json
import asyncio
from dataclasses import dataclass
from typing import Optional, AsyncIterator
from enum import Enum

from .redis_streams import (
    SwarmStreamReader,
    StreamOrchestrator,
    StreamEvent,
    StreamEventType,
)


class SSEMessageType(Enum):
    EVENT = "event"
    HEARTBEAT = "heartbeat"
    RECONNECT = "reconnect"
    ERROR = "error"


@dataclass(frozen=True)
class SSEMessage:
    message_type: SSEMessageType
    event: Optional[StreamEvent]
    cursor: Optional[str]
    replay_count: int

    def to_sse(self) -> str:
        if self.event:
            data = json.dumps(self.event.to_dict())
            return f"event: {self.event.event_type.value}\ndata: {data}\nid: {self.event.sequence}\n\n"
        elif self.message_type == SSEMessageType.HEARTBEAT:
            return ": heartbeat\n\n"
        elif self.message_type == SSEMessageType.RECONNECT:
            return f"event: reconnect\ndata: {json.dumps({'cursor': self.cursor, 'replayed': self.replay_count})}\n\n"
        elif self.message_type == SSEMessageType.ERROR:
            return f"event: error\ndata: {json.dumps({'error': 'stream_lost'})}\n\n"
        return ""


class SSEHandler:
    """
    Handles SSE connections with cursor-based frame replay.
    """

    def __init__(
        self,
        stream_orchestrator: StreamOrchestrator,
        heartbeat_interval: float = 5.0,
    ):
        self._orchestrator = stream_orchestrator
        self._heartbeat_interval = heartbeat_interval

    async def stream_to_client(
        self,
        query_hash: str,
        cursor: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream events to client as SSE.

        Args:
            query_hash: Query to stream.
            cursor: Last received event ID for reconnection.

        Yields:
            SSE-formatted strings.
        """
        if cursor:
            replay_events = await self._orchestrator.replay(query_hash, cursor)
            if replay_events:
                for event in replay_events:
                    msg = SSEMessage(
                        message_type=SSEMessageType.EVENT,
                        event=event,
                        cursor=None,
                        replay_count=0,
                    )
                    yield msg.to_sse()

                yield SSEMessage(
                    message_type=SSEMessageType.RECONNECT,
                    event=None,
                    cursor=cursor,
                    replay_count=len(replay_events),
                ).to_sse()

        last_cursor = cursor
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(query_hash)
        )

        try:
            async for event in self._orchestrator.subscribe(query_hash, last_cursor):
                last_cursor = str(event.sequence)

                msg = SSEMessage(
                    message_type=SSEMessageType.EVENT,
                    event=event,
                    cursor=None,
                    replay_count=0,
                )
                yield msg.to_sse()

                if event.event_type == StreamEventType.COMPLETE:
                    return

        except asyncio.CancelledError:
            pass
        except Exception:
            yield SSEMessage(
                message_type=SSEMessageType.ERROR,
                event=None,
                cursor=None,
                replay_count=0,
            ).to_sse()
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _heartbeat_loop(self, query_hash: str) -> None:
        """Send periodic heartbeats to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                yield SSEMessage(
                    message_type=SSEMessageType.HEARTBEAT,
                    event=None,
                    cursor=None,
                    replay_count=0,
                ).to_sse()
        except asyncio.CancelledError:
            pass


class SSEConnectionManager:
    """
    Manages multiple SSE connections for concurrent clients.
    """

    def __init__(self, stream_orchestrator: StreamOrchestrator):
        self._orchestrator = stream_orchestrator
        self._handlers: dict[str, SSEHandler] = {}
        self._connections: dict[str, set[str]] = {}

    def get_handler(self, query_hash: str) -> SSEHandler:
        if query_hash not in self._handlers:
            self._handlers[query_hash] = SSEHandler(self._orchestrator)
        return self._handlers[query_hash]

    def register_connection(self, query_hash: str, client_id: str) -> None:
        if query_hash not in self._connections:
            self._connections[query_hash] = set()
        self._connections[query_hash].add(client_id)

    def unregister_connection(self, query_hash: str, client_id: str) -> None:
        if query_hash in self._connections:
            self._connections[query_hash].discard(client_id)
            if not self._connections[query_hash]:
                del self._connections[query_hash]
                if query_hash in self._handlers:
                    del self._handlers[query_hash]

    def get_active_connections(self, query_hash: str) -> int:
        return len(self._connections.get(query_hash, set()))
