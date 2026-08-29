"""
PDF-to-PPTX Conversion API
===========================

A production-ready FastAPI microservice that wraps the PDF-to-PPTX orchestrator.

Endpoints
---------
POST /v1/convert          Submit a PDF for conversion (returns 202)
GET  /v1/jobs/{job_id}    Poll job status
GET  /v1/jobs/{job_id}/download   Download the converted PPTX
DELETE /v1/jobs/{job_id}  Cancel a job and clean up
GET  /v1/health           Liveness / readiness probe

Quickstart
----------
    python api_server.py                         # auto-reload dev server
    uvicorn api_server:app --reload --port 8000  # equivalent

Requirements
------------
    fastapi, uvicorn, python-multipart

Optional:
    redis (pip install redis) for persistent job queue

The conversion pipeline lives in orchestrator_v2.convert_pdf().
Job persistence uses job_queue.py (Redis backend if available, memory fallback).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from job_queue import create_queue, JobQueue
from dead_letter_queue import create_dlq, DeadLetterQueue

try:
    from rate_limiter import RateLimiter, RateLimitMiddleware, CostGuardrails, APIKeyManager
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False

try:
    from feedback_loop import FeedbackCollector, CITestSuitUpdater, FeedbackDashboard
    FEEDBACK_AVAILABLE = True
except ImportError:
    FEEDBACK_AVAILABLE = False

try:
    from streaming import stream_manager, format_sse, StreamEvent
    STREAMING_AVAILABLE = True
except ImportError:
    STREAMING_AVAILABLE = False

try:
    from replay_buffer import ReplayBuffer, SSEReplayManager
    REPLAY_AVAILABLE = True
except ImportError:
    REPLAY_AVAILABLE = False

try:
    from auth_proxy import AuthProxy, ScopedToken
    AUTH_PROXY_AVAILABLE = True
except ImportError:
    AUTH_PROXY_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_QUEUE_SIZE = 100
MAX_CONCURRENT = 5
PDF_MAGIC = b"%PDF"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job:
    __slots__ = (
        "job_id",
        "status",
        "progress",
        "created_at",
        "started_at",
        "completed_at",
        "result",
        "error",
        "webhook_url",
        "temp_dir",
        "pdf_path",
        "output_path",
        "mcp_augment",
        "task",
        "cancelled",
    )

    def __init__(
        self,
        job_id: str,
        webhook_url: Optional[str] = None,
        mcp_augment: bool = True,
    ) -> None:
        now = _now_iso()
        self.job_id = job_id
        self.status = JobStatus.QUEUED
        self.progress: float = 0.0
        self.created_at = now
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.webhook_url = webhook_url
        self.mcp_augment = mcp_augment
        self.temp_dir: Optional[str] = None
        self.pdf_path: Optional[str] = None
        self.output_path: Optional[str] = None
        self.task: Optional[asyncio.Task] = None
        self.cancelled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Worker (Redis-backed with in-memory fallback)
# ---------------------------------------------------------------------------


class ConversionWorker:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._queue: Optional[JobQueue] = None
        self._dlq: Optional[DeadLetterQueue] = None
        self._phases_completed: Dict[str, List[str]] = {}

    async def _ensure_queue(self) -> JobQueue:
        if self._queue is None:
            self._queue = create_queue(REDIS_URL)
        return self._queue

    async def _ensure_dlq(self) -> DeadLetterQueue:
        if self._dlq is None:
            self._dlq = create_dlq(REDIS_URL)
        return self._dlq

    # -- public helpers -----------------------------------------------------

    @property
    def active_count(self) -> int:
        return sum(
            1 for j in self._jobs.values() if j.status == JobStatus.PROCESSING
        )

    @property
    def queue_size(self) -> int:
        return sum(
            1 for j in self._jobs.values() if j.status == JobStatus.QUEUED
        )

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        self._http_client = httpx.AsyncClient(timeout=10)

    async def shutdown(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
        for job in self._jobs.values():
            if job.task and not job.task.done():
                job.cancelled = True
                job.task.cancel()

    # -- submit -------------------------------------------------------------

    async def submit(
        self,
        temp_dir: str,
        pdf_path: str,
        webhook_url: Optional[str] = None,
        mcp_augment: bool = True,
    ) -> Job:
        queue = await self._ensure_queue()
        q_size = await queue.queue_size()
        if q_size >= MAX_QUEUE_SIZE:
            raise RuntimeError("queue_full")

        job_id = str(uuid.uuid4())
        job = Job(job_id, webhook_url=webhook_url, mcp_augment=mcp_augment)
        job.temp_dir = temp_dir
        job.pdf_path = pdf_path
        job.output_path = str(Path(temp_dir) / "output.pptx")
        self._jobs[job_id] = job

        loop = asyncio.get_event_loop()
        job.task = loop.create_task(self._run(job))
        return job

    # -- background execution -----------------------------------------------

    async def _run(self, job: Job) -> None:
        queue = await self._ensure_queue()
        dlq = await self._ensure_dlq()
        
        async with self._semaphore:
            if job.cancelled:
                job.status = JobStatus.CANCELLED
                self._cleanup(job)
                return

            job.status = JobStatus.PROCESSING
            job.started_at = _now_iso()
            job.progress = 0.1
            await queue.set_status(job.job_id, "processing")
            self._phases_completed[job.job_id] = []

            try:
                from orchestrator_v2 import convert_pdf

                output_dir = Path(job.temp_dir) / "out"
                output_dir.mkdir(exist_ok=True)

                job.progress = 0.2
                conversion_result = await convert_pdf(
                    job.pdf_path, output_dir, mcp_augment=job.mcp_augment,
                    trace_id=job.job_id
                )

                if job.cancelled:
                    job.status = JobStatus.CANCELLED
                    self._cleanup(job)
                    return

                job.progress = 0.9

                if conversion_result.success:
                    resolved_out = Path(conversion_result.output_path)
                    if resolved_out.exists():
                        dest = Path(job.output_path)
                        shutil.copy2(str(resolved_out), str(dest))

                    job.result = {
                        "output_path": job.output_path,
                        "total_pages": conversion_result.total_pages,
                        "total_slides": conversion_result.total_slides,
                        "mcp_augmented_pages": conversion_result.mcp_augmented_pages,
                        "total_time_ms": round(conversion_result.total_time_ms, 1),
                    }
                    job.status = JobStatus.COMPLETED
                    await queue.complete_job(job.job_id, job.result)
                else:
                    err = "; ".join(conversion_result.errors) if conversion_result.errors else "unknown"
                    job.error = err
                    job.status = JobStatus.FAILED
                    await queue.fail_job(job.job_id, err)
                    
                    # DLQ: record failure and check if we should retry
                    dlq_entry = await dlq.record_failure(
                        job_id=job.job_id,
                        error=err,
                        phases_completed=self._phases_completed.get(job.job_id, []),
                        metadata={"pdf_name": Path(job.pdf_path).name,
                                  "file_size": Path(job.pdf_path).stat().st_size}
                    )
                    if dlq_entry:
                        job.error = f"Poison pill: routed to DLQ after {dlq_entry.retry_count} attempts"

            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
            except Exception as exc:
                job.error = f"{type(exc).__name__}: {str(exc)[:300]}"
                job.status = JobStatus.FAILED
                
                # DLQ: record exception failure
                dlq_entry = await dlq.record_failure(
                    job_id=job.job_id,
                    error=job.error,
                    phases_completed=self._phases_completed.get(job.job_id, []),
                    metadata={"pdf_name": Path(job.pdf_path).name if job.pdf_path else "unknown",
                              "file_size": Path(job.pdf_path).stat().st_size if job.pdf_path and Path(job.pdf_path).exists() else 0}
                )
                if dlq_entry:
                    job.error = f"Poison pill: routed to DLQ after {dlq_entry.retry_count} attempts"

            job.progress = 1.0
            job.completed_at = _now_iso()
            self._phases_completed.pop(job.job_id, None)

        if job.webhook_url:
            await self._send_webhook(job)

    def _cleanup(self, job: Job) -> None:
        if job.temp_dir:
            shutil.rmtree(job.temp_dir, ignore_errors=True)
            job.temp_dir = None

    async def _send_webhook(self, job: Job) -> None:
        if not self._http_client:
            return
        payload = job.to_dict()
        try:
            await self._http_client.post(job.webhook_url, json=payload)  # type: ignore[union-attr]
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pdf_magic_check(header: bytes) -> bool:
    return header[:4] == PDF_MAGIC


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

worker = ConversionWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await worker.start()
    yield
    await worker.shutdown()


app = FastAPI(
    title="PDF-to-PPTX Conversion API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# POST /v1/convert
# ---------------------------------------------------------------------------

@app.post("/v1/convert", status_code=202)
async def convert(
    file: UploadFile = File(...),
    webhook_url: Optional[str] = Form(None),
    mcp_augment: bool = Form(True),
):
    # Validate queue capacity
    if worker.queue_size + worker.active_count >= MAX_QUEUE_SIZE:
        raise HTTPException(503, detail="Queue is full. Try again later.")

    # Read & validate file size / magic bytes
    header = await file.read(4)
    if not _pdf_magic_check(header):
        raise HTTPException(422, detail="Uploaded file is not a valid PDF.")

    rest = await file.read()
    content = header + rest

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            413,
            detail=f"File exceeds the {MAX_FILE_SIZE_MB} MB limit.",
        )

    # Persist to a temp directory
    tmp = tempfile.mkdtemp(prefix="pptxjob_")
    pdf_path = str(Path(tmp) / "input.pdf")
    Path(pdf_path).write_bytes(content)

    job = await worker.submit(
        temp_dir=tmp,
        pdf_path=pdf_path,
        webhook_url=webhook_url,
        mcp_augment=mcp_augment,
    )

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job.job_id,
            "status": job.status.value,
            "created_at": job.created_at,
            "estimated_time_ms": 5000,
        },
    )


# ---------------------------------------------------------------------------
# GET /v1/jobs/{job_id}
# ---------------------------------------------------------------------------

@app.get("/v1/jobs/{job_id}")
async def get_job(job_id: str):
    job = worker.get_job(job_id)
    if not job:
        raise HTTPException(404, detail="Job not found.")
    return job.to_dict()


# ---------------------------------------------------------------------------
# GET /v1/jobs/{job_id}/download
# ---------------------------------------------------------------------------

@app.get("/v1/jobs/{job_id}/download")
async def download(job_id: str):
    job = worker.get_job(job_id)
    if not job:
        raise HTTPException(404, detail="Job not found.")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(404, detail="Job has not completed yet.")
    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(404, detail="Output file not found.")

    return FileResponse(
        job.output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": 'attachment; filename="converted.pptx"'},
    )


# ---------------------------------------------------------------------------
# DELETE /v1/jobs/{job_id}
# ---------------------------------------------------------------------------

@app.delete("/v1/jobs/{job_id}", status_code=204)
async def cancel(job_id: str):
    job = worker.get_job(job_id)
    if not job:
        raise HTTPException(404, detail="Job not found.")

    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        worker._cleanup(job)
        return

    job.cancelled = True
    if job.task and not job.task.done():
        job.task.cancel()
    worker._cleanup(job)

    return None


# ---------------------------------------------------------------------------
# GET /v1/health
# ---------------------------------------------------------------------------

@app.get("/v1/health")
async def health():
    dlq = await worker._ensure_dlq()
    return {
        "status": "healthy",
        "active_jobs": worker.active_count,
        "queue_size": worker.queue_size,
        "dlq_size": await dlq.dlq_size(),
    }


# ---------------------------------------------------------------------------
# GET /v1/dlq
# ---------------------------------------------------------------------------

@app.get("/v1/dlq")
async def list_dlq(limit: int = 100):
    dlq = await worker._ensure_dlq()
    entries = await dlq.get_dlq_entries(limit=limit)
    return {"entries": [e.__dict__ for e in entries], "total": await dlq.dlq_size()}


# ---------------------------------------------------------------------------
# POST /v1/dlq/{job_id}/retry
# ---------------------------------------------------------------------------

@app.post("/v1/dlq/{job_id}/retry", status_code=202)
async def retry_from_dlq(job_id: str):
    dlq = await worker._ensure_dlq()
    success = await dlq.retry_from_dlq(job_id)
    if not success:
        raise HTTPException(404, detail="Job not found in DLQ.")
    return {"status": "queued", "job_id": job_id}


# ---------------------------------------------------------------------------
# POST /v1/feedback
# ---------------------------------------------------------------------------

if FEEDBACK_AVAILABLE:
    _feedback_collector = FeedbackCollector()
    _feedback_updater = CITestSuitUpdater()
    _feedback_dashboard = FeedbackDashboard()

    @app.post("/v1/feedback", status_code=201)
    async def submit_feedback(
        job_id: str = Form(...),
        rating: str = Form(...),
        category: str = Form("other"),
        description: str = Form(""),
        page_numbers: str = Form(""),
    ):
        pages = [int(p.strip()) for p in page_numbers.split(",") if p.strip().isdigit()] if page_numbers else []
        entry = await _feedback_collector.submit_feedback(
            job_id=job_id, rating=rating, category=category,
            description=description, page_numbers=pages
        )
        return {"feedback_id": entry.feedback_id, "status": entry.status}

    @app.get("/v1/feedback")
    async def list_feedback(status: str = None, limit: int = 100):
        entries = await _feedback_collector.list_feedback(status=status, limit=limit)
        return {"entries": [e.__dict__ for e in entries], "total": len(entries)}

    @app.get("/v1/feedback/stats")
    async def feedback_stats():
        return await _feedback_collector.get_feedback_stats()

    @app.post("/v1/feedback/{feedback_id}/promote")
    async def promote_to_ci(feedback_id: str):
        entry = await _feedback_collector.get_feedback(feedback_id)
        if not entry:
            raise HTTPException(404, detail="Feedback not found.")
        success = await _feedback_updater.promote_to_ci(entry)
        if not success:
            raise HTTPException(500, detail="Failed to promote to CI suite.")
        return {"status": "promoted", "feedback_id": feedback_id}

    @app.get("/v1/feedback/dashboard")
    async def feedback_dashboard_html():
        from fastapi.responses import HTMLResponse
        stats = await _feedback_collector.get_feedback_stats()
        entries = await _feedback_collector.list_feedback(limit=100)
        html = _feedback_dashboard.generate_html(stats, entries)
        return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# GET /v1/jobs/{job_id}/stream  (Server-Sent Events)
# ---------------------------------------------------------------------------

if STREAMING_AVAILABLE:
    _replay_buffer = ReplayBuffer(REDIS_URL)
    _replay_manager = SSEReplayManager(_replay_buffer, stream_manager)

    @app.get("/v1/jobs/{job_id}/stream")
    async def stream_job(job_id: str, request: Request):
        from fastapi.responses import StreamingResponse

        async def event_generator():
            async for chunk in _replay_manager.replay_and_subscribe(job_id):
                yield chunk

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )


# ---------------------------------------------------------------------------
# BFF Auth Proxy endpoints
# ---------------------------------------------------------------------------

if AUTH_PROXY_AVAILABLE:
    _auth_proxy = AuthProxy()

    @app.post("/v1/auth/token")
    async def issue_scoped_token(api_key: str = Form(...)):
        token = _auth_proxy.issue_token(api_key)
        return {
            "token_id": token.token_id,
            "tier": token.tier,
            "expires_at": token.expires_at,
            "scopes": token.scopes,
        }

    @app.post("/v1/auth/{token_id}/consume")
    async def consume_token(token_id: str):
        ok = _auth_proxy.consume_upload(token_id)
        if not ok:
            raise HTTPException(401, detail="Token invalid or expired.")
        return {"status": "consumed", "token_id": token_id}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
