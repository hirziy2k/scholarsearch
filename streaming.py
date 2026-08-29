import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class StreamEvent:
    """A single SSE event."""

    event: str
    data: Dict[str, Any]
    id: str
    retry: int = 3000


class JobStreamManager:
    """Manage SSE streams for conversion jobs.

    Each job can have multiple connected clients watching the same stream.
    Events are broadcast to all connected clients.
    """

    def __init__(self):
        self._streams: Dict[str, asyncio.Queue] = {}
        self._clients: Dict[str, set] = {}

    async def subscribe(self, job_id: str) -> AsyncGenerator[StreamEvent, None]:
        queue = asyncio.Queue()
        stream_id = id(queue)

        if job_id not in self._streams:
            self._streams[job_id] = queue
        self._clients.setdefault(job_id, set()).add(stream_id)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield event
                    if event.event in ("complete", "error"):
                        break
                except asyncio.TimeoutError:
                    yield StreamEvent(
                        event="keepalive",
                        data={},
                        id=str(int(time.time())),
                    )
        finally:
            self._clients.get(job_id, set()).discard(stream_id)
            if not self._clients.get(job_id):
                self._streams.pop(job_id, None)
                self._clients.pop(job_id, None)

    async def publish(self, job_id: str, event: StreamEvent):
        queue = self._streams.get(job_id)
        if queue:
            await queue.put(event)

    async def phase_start(self, job_id: str, phase: str, page: int = None):
        data: Dict[str, Any] = {"phase": phase}
        if page is not None:
            data["page"] = page
        else:
            data["page"] = None
        await self.publish(
            job_id,
            StreamEvent(
                event="phase_start",
                data=data,
                id=str(int(time.time() * 1000)),
            ),
        )

    async def phase_end(self, job_id: str, phase: str, duration_ms: float):
        await self.publish(
            job_id,
            StreamEvent(
                event="phase_end",
                data={"phase": phase, "duration_ms": duration_ms},
                id=str(int(time.time() * 1000)),
            ),
        )

    async def progress(self, job_id: str, percentage: float, message: str = ""):
        await self.publish(
            job_id,
            StreamEvent(
                event="progress",
                data={"percentage": percentage, "message": message},
                id=str(int(time.time() * 1000)),
            ),
        )

    async def complete(self, job_id: str, download_url: str):
        await self.publish(
            job_id,
            StreamEvent(
                event="complete",
                data={"download_url": download_url},
                id=str(int(time.time() * 1000)),
            ),
        )

    async def error(self, job_id: str, error: str):
        await self.publish(
            job_id,
            StreamEvent(
                event="error",
                data={"message": error},
                id=str(int(time.time() * 1000)),
            ),
        )


stream_manager = JobStreamManager()


def format_sse(event: StreamEvent) -> str:
    """Format a StreamEvent as an SSE text frame.

    Format:
        id: <event_id>
        event: <event_type>
        data: <json_payload>
        retry: <reconnect_ms>
        \\n
    """
    lines = [f"id: {event.id}"]
    lines.append(f"event: {event.event}")
    lines.append(f"data: {json.dumps(event.data)}")
    if event.retry:
        lines.append(f"retry: {event.retry}")
    lines.append("\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Standalone simulation: python streaming.py
# ---------------------------------------------------------------------------

async def _simulate_conversion():
    """Simulate a PDF-to-PPTX conversion streaming progress events."""
    job_id = "sim-000"
    phases = [
        ("extract", "Extracting text and images..."),
        ("analyze", "Analyzing layout..."),
        ("design", "Generating slides..."),
        ("render", "Rendering PPTX..."),
    ]

    print(f"--- Starting simulated conversion for job {job_id} ---\n")

    async for event in stream_manager.subscribe(job_id):
        print(format_sse(event))

    print("\n--- Stream ended ---")


async def _run_simulation():
    job_id = "sim-000"
    manager = JobStreamManager()

    async def producer():
        phases = [
            ("extract", "Extracting text and images...", 0.0),
            ("analyze", "Analyzing layout...", 0.0),
            ("design", "Generating slides...", 0.0),
            ("render", "Rendering PPTX...", 0.0),
        ]

        for phase, desc, _ in phases:
            await manager.phase_start(job_id, phase)
            steps = 5
            for i in range(1, steps + 1):
                pct = round((i / steps) * 100, 1)
                await manager.progress(job_id, pct, f"{desc} ({i}/{steps})")
                await asyncio.sleep(0.3)
            await manager.phase_end(job_id, phase, duration_ms=steps * 300)

        await manager.complete(job_id, f"/v1/jobs/{job_id}/download")

    async def consumer():
        async for event in manager.subscribe(job_id):
            formatted = format_sse(event)
            print(formatted, end="")

    await asyncio.gather(producer(), consumer())


if __name__ == "__main__":
    asyncio.run(_run_simulation())
