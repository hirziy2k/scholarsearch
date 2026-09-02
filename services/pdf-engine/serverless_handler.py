#!/usr/bin/env python3
"""
serverless_handler.py — Serverless Event-Driven Architecture handler for PDF-to-PPTX.

Flow:
  1. FastAPI ingress receives PDF -> uploads to S3 -> drops event into SQS -> returns 202
  2. Lambda worker picks up SQS message -> downloads PDF from S3 -> runs orchestrator_v2
     -> uploads PPTX to S3 -> writes status -> terminates
  3. User polls status endpoint or receives webhook

Imports only stdlib + optional boto3. No FastAPI dependency.
Runnable standalone: python serverless_handler.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger("serverless_handler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_h)

# ---------------------------------------------------------------------------
# Optional boto3 import (graceful degradation)
# ---------------------------------------------------------------------------
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    HAS_BOTO3 = True
except ImportError:
    boto3 = None  # type: ignore[assignment]
    BOTO_CORE_ERROR: type = Exception  # type: ignore[assignment]
    ClientError: type = Exception  # type: ignore[assignment]

    class BotoCoreError(Exception):  # type: ignore[no-redef]
        pass

    HAS_BOTO3 = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SQS_BATCH_RESPONSE = "batchItemFailures"
SQS_BATCH_FAILURE = {"itemIdentifier": str}

DEFAULT_BUCKET = os.environ.get("PDF2PPTX_BUCKET", "pdf2pptx-storage")
DEFAULT_TABLE = os.environ.get("PDF2PPTX_TABLE", "pdf2pptx-jobs")
DEFAULT_QUEUE = os.environ.get("PDF2PPTX_QUEUE", "pdf2pptx-conversion-queue")
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))


# =========================================================================
# Data model
# =========================================================================
@dataclass
class ConversionEvent:
    """Event dropped into SQS for asynchronous processing."""

    job_id: str
    pdf_s3_key: str
    output_s3_key: str
    status_s3_key: str
    webhook_url: Optional[str] = None
    mcp_augment: bool = True
    created_at: str = ""
    trace_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> "ConversionEvent":
        d = json.loads(raw)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# =========================================================================
# S3 Manager
# =========================================================================
class S3Manager:
    """Handles all S3 operations with SSE-S3 encryption.

    Bucket layout:
      uploads/{job_id}/{filename}
      outputs/{job_id}/{filename}
      status/{job_id}.json
      traces/{job_id}_trace.html
    """

    def __init__(self, bucket: str = DEFAULT_BUCKET, region: str = AWS_REGION):
        self.bucket = bucket
        self._client = None
        if HAS_BOTO3:
            try:
                self._client = boto3.client("s3", region_name=region)
            except Exception:
                logger.warning("boto3 S3 client init failed; S3 operations will be unavailable")

    # -- internal helpers ---------------------------------------------------
    def _ensure_client(self):
        if self._client is None:
            raise RuntimeError("S3 client not available – check boto3 installation and AWS credentials")

    def _sse_headers(self) -> Dict[str, str]:
        return {"ServerSideEncryption": "aws:kms"} if False else {"ServerSideEncryption": "AES256"}

    # -- upload / download --------------------------------------------------
    def upload_pdf(self, job_id: str, filename: str, data: bytes) -> str:
        """Upload input PDF. Returns the S3 key."""
        self._ensure_client()
        key = f"uploads/{job_id}/{filename}"
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType="application/pdf",
            **self._sse_headers(),
        )
        logger.info("Uploaded PDF s3://%s/%s (%d bytes)", self.bucket, key, len(data))
        return key

    def download_pdf(self, s3_key: str, local_path: Path) -> Path:
        """Download PDF to local path."""
        self._ensure_client()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(self.bucket, s3_key, str(local_path))
        logger.info("Downloaded s3://%s/%s -> %s", self.bucket, s3_key, local_path)
        return local_path

    def upload_pptx(self, job_id: str, filename: str, data: bytes) -> str:
        """Upload output PPTX. Returns the S3 key."""
        self._ensure_client()
        key = f"outputs/{job_id}/{filename}"
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            **self._sse_headers(),
        )
        logger.info("Uploaded PPTX s3://%s/%s (%d bytes)", self.bucket, key, len(data))
        return key

    # -- status JSON --------------------------------------------------------
    def write_status(self, job_id: str, status: Dict[str, Any]) -> str:
        """Write status JSON. Returns the S3 key."""
        self._ensure_client()
        key = f"status/{job_id}.json"
        body = json.dumps(status, default=str, indent=2).encode()
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
            **self._sse_headers(),
        )
        return key

    def read_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_client()
        key = f"status/{job_id}.json"
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=key)
            return json.loads(resp["Body"].read())
        except (ClientError, KeyError):
            return None

    # -- presigned URLs -----------------------------------------------------
    def presigned_url(self, s3_key: str, expires: int = 3600) -> str:
        self._ensure_client()
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=expires,
        )

    # -- trace HTML ---------------------------------------------------------
    def upload_trace(self, job_id: str, html: str) -> str:
        self._ensure_client()
        key = f"traces/{job_id}_trace.html"
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=html.encode(),
            ContentType="text/html",
            **self._sse_headers(),
        )
        return key


# =========================================================================
# DynamoDB Status Tracker
# =========================================================================
class DynamoDBStatusTracker:
    """Tracks conversion jobs in DynamoDB.

    Table: pdf2pptx-jobs
    Partition key: job_id (S)
    """

    TABLE_NAME = DEFAULT_TABLE
    STATUS_VALUES = ("queued", "downloading", "converting", "uploading", "completed", "failed")

    def __init__(self, table_name: str = TABLE_NAME, region: str = AWS_REGION):
        self.table_name = table_name
        self._resource = None
        self._table = None
        if HAS_BOTO3:
            try:
                self._resource = boto3.resource("dynamodb", region_name=region)
                self._table = self._resource.Table(self.table_name)
            except Exception:
                logger.warning("DynamoDB resource init failed; status tracking unavailable")

    def _ensure_table(self):
        if self._table is None:
            raise RuntimeError("DynamoDB table not available – check boto3 and AWS credentials")

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_job(
        self,
        job_id: str,
        pdf_name: str,
        output_s3_key: str = "",
        trace_id: str = "",
    ) -> Dict[str, Any]:
        self._ensure_table()
        item: Dict[str, Any] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "created_at": self._now_iso(),
            "pdf_name": pdf_name,
            "output_s3_key": output_s3_key,
            "trace_id": trace_id,
        }
        self._table.put_item(Item=item)
        return item

    def update_status(self, job_id: str, status: str, progress: int = 0, **extra: Any) -> None:
        self._ensure_table()
        expr_vals: Dict[str, Any] = {":s": status, ":p": progress}
        expr_names: Dict[str, str] = {}
        updates: Dict[str, str] = {"#st": ":s", "#pr": ":p"}
        expr_names["#st"] = "status"
        expr_names["#pr"] = "progress"

        if status == "converting":
            expr_vals[":started"] = self._now_iso()
            updates["#sa"] = ":started"
            expr_names["#sa"] = "started_at"

        for k, v in extra.items():
            safe = f"#{k}"
            val_key = f":v_{k}"
            expr_names[safe] = k
            expr_vals[val_key] = v
            updates[safe] = val_key

        expr = "SET " + ", ".join(f"{k} = {v}" for k, v in updates.items())
        self._table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_vals,
        )

    def complete_job(
        self,
        job_id: str,
        output_s3_key: str,
        total_pages: int,
        total_slides: int,
        total_time_ms: float,
    ) -> None:
        self.update_status(
            job_id,
            "completed",
            progress=100,
            completed_at=self._now_iso(),
            output_s3_key=output_s3_key,
            total_pages=total_pages,
            total_slides=total_slides,
            total_time_ms=total_time_ms,
        )

    def fail_job(self, job_id: str, error: str) -> None:
        self.update_status(job_id, "failed", error=error)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_table()
        resp = self._table.get_item(Key={"job_id": job_id})
        return resp.get("Item")


# =========================================================================
# SQS Event Handler (Lambda entry-point)
# =========================================================================
class SQSEventHandler:
    """Parse SQS messages, run orchestrator, upload results, send webhooks."""

    @staticmethod
    def handle(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """AWS Lambda handler for SQS trigger.

        Returns a batch response with ``batchItemFailures`` listing any
        message IDs that should be retried.
        """
        s3_mgr = S3Manager()
        tracker = DynamoDBStatusTracker()
        failed: List[Dict[str, str]] = []

        records = event.get("Records", [])
        for record in records:
            msg_id = record.get("messageId", "unknown")
            try:
                body = record.get("body", "{}")
                evt = ConversionEvent.from_json(body)
                SQSEventHandler._process_event(evt, s3_mgr, tracker)
            except Exception as exc:
                logger.exception("Failed to process message %s: %s", msg_id, exc)
                failed.append({"itemIdentifier": msg_id})

        return {SQS_BATCH_RESPONSE: failed}

    @staticmethod
    def _process_event(
        evt: ConversionEvent,
        s3_mgr: S3Manager,
        tracker: DynamoDBStatusTracker,
    ) -> None:
        t0 = time.time()

        # Download PDF
        tracker.update_status(evt.job_id, "downloading")
        local_dir = Path("/tmp") / evt.job_id
        local_dir.mkdir(parents=True, exist_ok=True)
        local_pdf = s3_mgr.download_pdf(evt.pdf_s3_key, local_dir / "input.pdf")

        # Convert
        tracker.update_status(evt.job_id, "converting")
        result = asyncio.run(
            _run_orchestrator(str(local_pdf), local_dir, evt.mcp_augment, evt.trace_id)
        )

        if not result.get("success"):
            error_msg = "; ".join(result.get("errors", ["unknown error"]))
            tracker.fail_job(evt.job_id, error_msg)
            _send_webhook(evt.webhook_url, evt.job_id, "failed", error=error_msg)
            return

        # Upload PPTX
        tracker.update_status(evt.job_id, "uploading")
        output_path = Path(result["output_path"])
        pptx_data = output_path.read_bytes()
        output_key = s3_mgr.upload_pptx(evt.job_id, output_path.name, pptx_data)

        # Upload trace if present
        trace_path = local_dir / "trace.html"
        if trace_path.exists():
            s3_mgr.upload_trace(evt.job_id, trace_path.read_text())

        elapsed_ms = (time.time() - t0) * 1000
        tracker.complete_job(
            evt.job_id,
            output_key,
            result.get("total_pages", 0),
            result.get("total_slides", 0),
            elapsed_ms,
        )

        # Write S3 status JSON
        s3_mgr.write_status(
            evt.job_id,
            {
                "job_id": evt.job_id,
                "status": "completed",
                "output_s3_key": output_key,
                "elapsed_ms": elapsed_ms,
            },
        )

        _send_webhook(evt.webhook_url, evt.job_id, "completed", output_key=output_key)
        logger.info("Job %s completed in %.0fms", evt.job_id, elapsed_ms)


# =========================================================================
# Serverless Ingress (called from FastAPI or any HTTP framework)
# =========================================================================
class ServerlessIngress:
    """HTTP-layer helper that stages work into S3 / SQS / DynamoDB."""

    def __init__(
        self,
        bucket: str = DEFAULT_BUCKET,
        queue_url: str = "",
        table_name: str = DEFAULT_TABLE,
        region: str = AWS_REGION,
    ):
        self.s3 = S3Manager(bucket, region)
        self.tracker = DynamoDBStatusTracker(table_name, region)
        self.queue_url = queue_url or os.environ.get("SQS_QUEUE_URL", "")
        self._sqs = None
        if HAS_BOTO3 and self.queue_url:
            try:
                self._sqs = boto3.client("sqs", region_name=region)
            except Exception:
                logger.warning("SQS client init failed")

    def submit(
        self,
        pdf_bytes: bytes,
        pdf_name: str,
        mcp_augment: bool = True,
        webhook_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upload PDF, create DB record, enqueue SQS message. Returns job info."""
        job_id = uuid.uuid4().hex[:16]
        trace_id = f"trace-{job_id}"

        # Upload PDF to S3
        pdf_key = self.s3.upload_pdf(job_id, pdf_name, pdf_bytes)

        # DynamoDB record
        output_key = f"outputs/{job_id}/{Path(pdf_name).stem}.pptx"
        self.tracker.create_job(job_id, pdf_name, output_key, trace_id)

        # Build event
        evt = ConversionEvent(
            job_id=job_id,
            pdf_s3_key=pdf_key,
            output_s3_key=output_key,
            status_s3_key=f"status/{job_id}.json",
            webhook_url=webhook_url,
            mcp_augment=mcp_augment,
            created_at=datetime.now(timezone.utc).isoformat(),
            trace_id=trace_id,
            metadata=metadata or {},
        )

        # Send to SQS
        if self._sqs and self.queue_url:
            self._sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=evt.to_json(),
                MessageGroupId=job_id,
            )
        else:
            logger.warning("SQS unavailable; event not enqueued for job %s", job_id)

        return {"job_id": job_id, "status": "queued", "trace_id": trace_id}

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.tracker.get_job(job_id)

    def get_output_url(self, job_id: str, expires: int = 3600) -> Optional[str]:
        job = self.tracker.get_job(job_id)
        if not job or job.get("status") != "completed":
            return None
        key = job.get("output_s3_key", "")
        if not key:
            return None
        return self.s3.presigned_url(key, expires)


# =========================================================================
# Helper utilities
# =========================================================================
async def _run_orchestrator(
    pdf_path: str, output_dir: Path, mcp_augment: bool, trace_id: str
) -> Dict[str, Any]:
    """Run orchestrator_v2.convert_pdf and return a serialisable dict."""
    try:
        from orchestrator_v2 import convert_pdf

        result = await convert_pdf(pdf_path, output_dir, mcp_augment=mcp_augment, trace_id=trace_id)
        return {
            "success": result.success,
            "output_path": result.output_path,
            "total_pages": result.total_pages,
            "total_slides": result.total_slides,
            "total_time_ms": result.total_time_ms,
            "errors": result.errors,
            "warnings": result.warnings,
        }
    except Exception as exc:
        return {
            "success": False,
            "errors": [str(exc)],
            "output_path": None,
            "total_pages": 0,
            "total_slides": 0,
            "total_time_ms": 0,
        }


def _send_webhook(
    url: Optional[str], job_id: str, status: str, **extra: Any
) -> None:
    """POST a JSON payload to *url* (best-effort)."""
    if not url:
        return
    payload = json.dumps({"job_id": job_id, "status": status, **extra}).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10) as resp:
            logger.info("Webhook %s -> %s", url, resp.status)
    except (URLError, OSError) as exc:
        logger.warning("Webhook %s failed: %s", url, exc)


# =========================================================================
# Module-level Lambda handler
# =========================================================================
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry-point for SQS-triggered conversion worker."""
    return SQSEventHandler.handle(event, context)


def status_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry-point for GET /status/{job_id} via API Gateway."""
    job_id = (event.get("pathParameters") or {}).get("job_id", "")
    if not job_id:
        return {"statusCode": 400, "body": json.dumps({"error": "missing job_id"})}

    tracker = DynamoDBStatusTracker()
    try:
        job = tracker.get_job(job_id)
    except Exception:
        logger.warning("DynamoDB unavailable; returning 503")
        return {"statusCode": 503, "body": json.dumps({"error": "service unavailable"})}

    if job is None:
        return {"statusCode": 404, "body": json.dumps({"error": "job not found"})}

    return {"statusCode": 200, "body": json.dumps(job, default=str)}


# =========================================================================
# Standalone runner (no AWS required)
# =========================================================================
def _standalone_run() -> None:
    """Simulate a local conversion when invoked directly."""
    print("=" * 60)
    print("serverless_handler.py — standalone local simulation")
    print("=" * 60)

    if not HAS_BOTO3:
        print("[INFO] boto3 not installed; AWS features disabled.\n")

    # Locate a test PDF in the workspace
    candidates = list(Path(".").glob("*.pdf"))
    if not candidates:
        print("[WARN] No PDF files found in current directory.")
        print("       Creating a dummy event to demonstrate the data flow.\n")
        evt = ConversionEvent(
            job_id="local-demo-" + uuid.uuid4().hex[:8],
            pdf_s3_key="uploads/demo/test.pdf",
            output_s3_key="outputs/demo/test.pptx",
            status_s3_key="status/demo.json",
            created_at=datetime.now(timezone.utc).isoformat(),
            trace_id=f"trace-local-{uuid.uuid4().hex[:8]}",
        )
        print("Sample ConversionEvent:")
        print(json.dumps(json.loads(evt.to_json()), indent=2))
        print("\nIn a real deployment this would:")
        print("  1. Upload the PDF to S3 via S3Manager.upload_pdf()")
        print("  2. Enqueue the event into SQS")
        print("  3. Lambda picks it up and runs SQSEventHandler.handle()")
        print("  4. orchestrator_v2.convert_pdf() produces the PPTX")
        print("  5. Results uploaded to S3, status written to DynamoDB")
        return

    pdf_path = candidates[0]
    print(f"Found PDF: {pdf_path.name}")
    print("Running orchestrator_v2.convert_pdf() locally...\n")

    output_dir = Path("output_serverless")
    output_dir.mkdir(exist_ok=True)

    t0 = time.time()
    result = asyncio.run(
        _run_orchestrator(str(pdf_path), output_dir, mcp_augment=True, trace_id="local-run")
    )
    elapsed = (time.time() - t0) * 1000

    if result["success"]:
        print(f"Conversion completed in {elapsed:.0f}ms")
        print(f"  Output:    {result['output_path']}")
        print(f"  Pages:     {result['total_pages']}")
        print(f"  Slides:    {result['total_slides']}")
        if result["warnings"]:
            print(f"  Warnings:  {result['warnings']}")
    else:
        print(f"Conversion FAILED after {elapsed:.0f}ms")
        for err in result["errors"]:
            print(f"  Error: {err}")

    # Show DynamoDB status structure (dry-run)
    job_id = "local-demo-" + uuid.uuid4().hex[:8]
    print(f"\n--- DynamoDB record structure for job {job_id} ---")
    sample_record = {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "pdf_name": pdf_path.name,
        "output_s3_key": f"outputs/{job_id}/{pdf_path.stem}.pptx",
        "total_pages": result.get("total_pages", 0),
        "total_slides": result.get("total_slides", 0),
        "total_time_ms": elapsed,
        "trace_id": f"trace-{job_id}",
    }
    print(json.dumps(sample_record, indent=2))
    print("\nDone.")


if __name__ == "__main__":
    _standalone_run()
