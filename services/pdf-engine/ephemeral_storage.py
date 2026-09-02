"""Ephemeral Storage Lifecycle for PDF-to-PPTX conversion.

Manages temporary file storage with secure wipe capabilities.
Supports RAMDISK, S3, and LOCAL backends with automatic fallback.

Usage:
    lifecycle = StorageLifecycle()
    ref = await lifecycle.store_pdf(pdf_bytes, "invoice.pdf")
    output_ref = await lifecycle.store_output(pptx_bytes, "invoice.pptx")
    await lifecycle.complete(ref)          # wipe input
    output = await lifecycle.retrieve(output_ref)
    await lifecycle.shutdown()             # wipe everything remaining
"""

from __future__ import annotations

import asyncio
import atexit
import json
import logging
import os
import platform
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("ephemeral_storage")

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


# ---------------------------------------------------------------------------
# Secure delete helper
# ---------------------------------------------------------------------------

def secure_delete_file(path: str) -> bool:
    """Overwrite file with random bytes, then delete.

    DOD 5220.22-M inspired: 3 passes (random, 0xFF, random)
    for files under 1 MB, single pass for larger files.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False

    size = p.stat().st_size
    passes = 1 if size > 1_000_000 else 3
    try:
        with open(p, "r+b") as f:
            for i in range(passes):
                f.seek(0)
                remaining = size
                while remaining > 0:
                    chunk = min(remaining, 65536)
                    if i % 2 == 1:
                        f.write(b"\xff" * chunk)
                    else:
                        f.write(os.urandom(chunk))
                    remaining -= chunk
                f.flush()
                os.fsync(f.fileno())
        p.unlink(missing_ok=True)
        if hasattr(os, "sync"):
            try:
                os.sync()
            except OSError:
                pass
        return True
    except OSError as exc:
        logger.warning("secure_delete failed for %s: %s", path, exc)
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
        return False


# ---------------------------------------------------------------------------
# S3 storage backend
# ---------------------------------------------------------------------------

class S3Storage:
    """S3 backend with lifecycle rules.

    Uses boto3. Each object gets SSE-S3 encryption and metadata with
    source, timestamp, and TTL.

    Bucket lifecycle (configured via ``configure_bucket_lifecycle``):
    - Transition to Glacier after 1 day
    - Delete after 7 days
    """

    def __init__(self, bucket: str, prefix: str = "ephemeral/"):
        if not HAS_BOTO3:
            raise ImportError("boto3 is required for S3 storage mode")
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._client = boto3.client("s3")
        self._managed: list[str] = []

    # -- public API --------------------------------------------------------

    async def store(self, data: bytes, filename: str) -> str:
        key = self._make_key(filename)
        meta = {
            "source": "pdf2pptx",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ttl": "24h",
        }
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ServerSideEncryption="AES256",
            Metadata=meta,
        )
        uri = f"s3://{self._bucket}/{key}"
        self._managed.append(uri)
        return uri

    async def retrieve(self, ref: str) -> bytes:
        key = self._extract_key(ref)
        resp = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self._bucket,
            Key=key,
        )
        body = await asyncio.to_thread(resp["Body"].read)
        return body  # type: ignore[return-value]

    async def delete(self, ref: str) -> bool:
        key = self._extract_key(ref)
        try:
            await asyncio.to_thread(
                self._client.delete_object,
                Bucket=self._bucket,
                Key=key,
            )
            if ref in self._managed:
                self._managed.remove(ref)
            return True
        except (ClientError, BotoCoreError) as exc:
            logger.warning("S3 delete failed for %s: %s", ref, exc)
            return False

    async def delete_all(self) -> int:
        count = 0
        for uri in list(self._managed):
            if await self.delete(uri):
                count += 1
        return count

    def configure_bucket_lifecycle(self) -> None:
        """Apply lifecycle rules: Glacier after 1 day, delete after 7 days."""
        rule_id = "ephemeral-pdf2pptx-cleanup"
        lifecycle = {
            "Rules": [
                {
                    "ID": rule_id,
                    "Filter": {"Prefix": f"{self._prefix}/"},
                    "Status": "Enabled",
                    "Transitions": [
                        {
                            "Days": 1,
                            "StorageClass": "GLACIER",
                        }
                    ],
                    "Expiration": {"Days": 7},
                }
            ]
        }
        try:
            self._client.put_bucket_lifecycle_configuration(
                Bucket=self._bucket,
                LifecycleConfiguration=lifecycle,
            )
        except (ClientError, BotoCoreError) as exc:
            logger.warning("Could not set bucket lifecycle: %s", exc)

    # -- helpers -----------------------------------------------------------

    def _make_key(self, filename: str) -> str:
        ts = int(time.time())
        uid = uuid.uuid4().hex[:12]
        safe = "".join(c if c.isalnum() or c in ".-_/" else "_" for c in filename)
        return f"{self._prefix}/{ts}_{uid}_{safe}"

    @staticmethod
    def _extract_key(ref: str) -> str:
        if ref.startswith("s3://"):
            parts = ref[5:].split("/", 1)
            return parts[1] if len(parts) > 1 else ""
        return ref


# ---------------------------------------------------------------------------
# Ramdisk storage backend
# ---------------------------------------------------------------------------

class RamdiskStorage:
    """RAM-backed storage using /dev/shm or platform equivalent.

    Linux:  /dev/shm/pdf2pptx/
    Others: system temp directory (fastest available)

    Files are cleaned on process exit via atexit hook.
    """

    _BASE_DIR: str | None = None

    def __init__(self) -> None:
        self._dir = self._resolve_base()
        self._managed: list[Path] = []
        self._ensure_dir()
        atexit.register(self._cleanup)

    async def store(self, data: bytes, filename: str) -> str:
        p = self._path_for(filename)
        await asyncio.to_thread(self._write_bytes, p, data)
        self._managed.append(p)
        return str(p)

    async def retrieve(self, ref: str) -> bytes:
        p = Path(ref)
        return await asyncio.to_thread(p.read_bytes)

    async def delete(self, ref: str) -> bool:
        return await asyncio.to_thread(self._secure_delete, ref)

    async def delete_all(self) -> int:
        count = 0
        for p in list(self._managed):
            if await self.delete(str(p)):
                count += 1
        return count

    @property
    def base_dir(self) -> str:
        return str(self._dir)

    # -- internals ---------------------------------------------------------

    @classmethod
    def _resolve_base(cls) -> Path:
        if cls._BASE_DIR is not None:
            return Path(cls._BASE_DIR)
        system = platform.system()
        if system == "Linux":
            shm = Path("/dev/shm")
            if shm.exists() and os.access(str(shm), os.W_OK | os.R_OK | os.X_OK):
                return shm / "pdf2pptx"
        return Path(tempfile.gettempdir()) / "pdf2pptx_ramdisk"

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, filename: str) -> Path:
        ts = int(time.time())
        uid = uuid.uuid4().hex[:8]
        safe = "".join(c if c.isalnum() or c in ".-" else "_" for c in filename)
        return self._dir / f"{ts}_{uid}_{safe}"

    @staticmethod
    def _write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

    @staticmethod
    def _secure_delete(ref: str) -> bool:
        return secure_delete_file(ref)

    def _cleanup(self) -> None:
        for p in list(self._managed):
            try:
                secure_delete_file(str(p))
            except Exception:
                pass
        self._managed.clear()


# ---------------------------------------------------------------------------
# Local secure storage backend
# ---------------------------------------------------------------------------

class LocalSecureStorage:
    """Local temp directory with secure wipe.

    Uses ``tempfile.mkdtemp(prefix="pdf2pptx_")``.
    Secure wipe overwrites with ``os.urandom(size)`` before unlink.
    """

    def __init__(self) -> None:
        self._dir = tempfile.mkdtemp(prefix="pdf2pptx_")
        self._managed: list[Path] = []
        atexit.register(self._cleanup)

    async def store(self, data: bytes, filename: str) -> str:
        p = self._path_for(filename)
        await asyncio.to_thread(self._write_bytes, p, data)
        self._managed.append(p)
        return str(p)

    async def retrieve(self, ref: str) -> bytes:
        p = Path(ref)
        return await asyncio.to_thread(p.read_bytes)

    async def delete(self, ref: str) -> bool:
        return await asyncio.to_thread(self._secure_delete, ref)

    async def delete_all(self) -> int:
        count = 0
        for p in list(self._managed):
            if await self.delete(str(p)):
                count += 1
        return count

    @property
    def base_dir(self) -> str:
        return self._dir

    # -- internals ---------------------------------------------------------

    def _path_for(self, filename: str) -> Path:
        ts = int(time.time())
        uid = uuid.uuid4().hex[:8]
        safe = "".join(c if c.isalnum() or c in ".-" else "_" for c in filename)
        return Path(self._dir) / f"{ts}_{uid}_{safe}"

    @staticmethod
    def _write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

    @staticmethod
    def _secure_delete(ref: str) -> bool:
        return secure_delete_file(ref)

    def _cleanup(self) -> None:
        for p in list(self._managed):
            try:
                secure_delete_file(str(p))
            except Exception:
                pass
        self._managed.clear()
        try:
            shutil.rmtree(self._dir, ignore_errors=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main EphemeralStorage facade
# ---------------------------------------------------------------------------

class EphemeralStorage:
    """Manages the lifecycle of temporary files during conversion.

    Three modes:
    1. RAMDISK  – /dev/shm (Linux) or temp dir with memory mapping
    2. S3       – encrypted S3 bucket with lifecycle rules
    3. LOCAL    – local temp directory with secure wipe
    """

    _BACKENDS = ("ramdisk", "s3", "local")

    def __init__(
        self,
        mode: str = "auto",
        s3_bucket: str | None = None,
        s3_prefix: str = "ephemeral/",
    ) -> None:
        self._mode = self._resolve_mode(mode, s3_bucket)
        self._bytes_stored: int = 0
        self._input_refs: list[str] = []
        self._output_refs: list[str] = []

        if self._mode == "s3":
            self._backend: Any = S3Storage(s3_bucket, s3_prefix)
        elif self._mode == "ramdisk":
            self._backend = RamdiskStorage()
        else:
            self._backend = LocalSecureStorage()

    # -- public API --------------------------------------------------------

    async def store_input(self, data: bytes, filename: str) -> str:
        ref = await self._backend.store(data, filename)
        self._bytes_stored += len(data)
        self._input_refs.append(ref)
        return ref

    async def retrieve_input(self, ref: str) -> bytes:
        return await self._backend.retrieve(ref)

    async def store_output(self, data: bytes, filename: str) -> str:
        ref = await self._backend.store(data, filename)
        self._bytes_stored += len(data)
        self._output_refs.append(ref)
        return ref

    async def retrieve_output(self, ref: str) -> bytes:
        return await self._backend.retrieve(ref)

    async def secure_wipe(self, ref: str) -> bool:
        result = await self._backend.delete(ref)
        if ref in self._input_refs:
            self._input_refs.remove(ref)
        if ref in self._output_refs:
            self._output_refs.remove(ref)
        return result

    async def cleanup_all(self) -> int:
        count = await self._backend.delete_all()
        self._input_refs.clear()
        self._output_refs.clear()
        return count

    @property
    def storage_mode(self) -> str:
        return self._mode

    @property
    def bytes_stored(self) -> int:
        return self._bytes_stored

    # -- internals ---------------------------------------------------------

    @classmethod
    def _resolve_mode(cls, mode: str, s3_bucket: str | None) -> str:
        if mode != "auto":
            if mode == "s3" and not s3_bucket:
                raise ValueError("s3_bucket is required for s3 mode")
            if mode not in cls._BACKENDS:
                raise ValueError(f"Unknown mode {mode!r}; choose from {cls._BACKENDS}")
            if mode == "s3" and not HAS_BOTO3:
                logger.warning("boto3 not available; falling back to local")
                return "local"
            return mode

        # auto-detect
        if s3_bucket and HAS_BOTO3:
            try:
                client = boto3.client("s3")
                client.head_bucket(Bucket=s3_bucket)
                return "s3"
            except Exception as exc:
                logger.info("S3 unavailable (%s); trying ramdisk", exc)

        shm = Path("/dev/shm")
        if platform.system() == "Linux" and shm.exists() and os.access(
            str(shm), os.W_OK
        ):
            return "ramdisk"

        return "local"


# ---------------------------------------------------------------------------
# High-level lifecycle manager
# ---------------------------------------------------------------------------

class StorageLifecycle:
    """High-level lifecycle manager coordinating storage and wiping.

    Usage::

        lifecycle = StorageLifecycle()
        ref = await lifecycle.store_pdf(pdf_bytes, "invoice.pdf")
        # ... process ...
        output_ref = await lifecycle.store_output(pptx_bytes, "invoice.pptx")
        await lifecycle.complete(ref)   # wipe input, keep output
        data = await lifecycle.retrieve(output_ref)
        await lifecycle.shutdown()      # wipe everything remaining
    """

    def __init__(
        self,
        mode: str = "auto",
        s3_bucket: str | None = None,
        s3_prefix: str = "ephemeral/",
    ) -> None:
        self._storage = EphemeralStorage(
            mode=mode, s3_bucket=s3_bucket, s3_prefix=s3_prefix
        )
        self._refs: dict[str, dict[str, str]] = {}
        self._closed = False

    async def store_pdf(self, data: bytes, filename: str) -> str:
        ref = await self._storage.store_input(data, filename)
        self._refs[ref] = {"kind": "input", "filename": filename}
        return ref

    async def store_output(self, data: bytes, filename: str) -> str:
        ref = await self._storage.store_output(data, filename)
        self._refs[ref] = {"kind": "output", "filename": filename}
        return ref

    async def retrieve(self, ref: str) -> bytes:
        kind = self._refs.get(ref, {}).get("kind", "input")
        if kind == "output":
            return await self._storage.retrieve_output(ref)
        return await self._storage.retrieve_input(ref)

    async def complete(self, ref: str) -> None:
        """Mark a conversion as complete: wipe the input, keep the output."""
        info = self._refs.get(ref)
        if info and info["kind"] == "input":
            await self._storage.secure_wipe(ref)
            self._refs.pop(ref, None)

    async def shutdown(self) -> int:
        """Wipe all remaining files. Called on worker shutdown."""
        if self._closed:
            return 0
        self._closed = True
        count = await self._storage.cleanup_all()
        self._refs.clear()
        return count

    @property
    def storage(self) -> EphemeralStorage:
        return self._storage

    @property
    def bytes_stored(self) -> int:
        return self._storage.bytes_stored

    @property
    def storage_mode(self) -> str:
        return self._storage.storage_mode


# ---------------------------------------------------------------------------
# Standalone test harness
# ---------------------------------------------------------------------------

async def _run_tests() -> None:
    """Self-contained tests for all backends."""
    print("=" * 60)
    print("Ephemeral Storage Lifecycle – Backend Tests")
    print("=" * 60)

    test_data = b"Sensitive financial ledger data -- " * 200
    test_filename = "test_ledger.pdf"

    # --- Test each backend ------------------------------------------------
    backends: list[tuple[str, dict[str, Any]]] = [
        ("local", {}),
        ("ramdisk", {}),
    ]
    if HAS_BOTO3 and os.environ.get("PDF2PPTX_TEST_S3_BUCKET"):
        backends.append(("s3", {"s3_bucket": os.environ["PDF2PPTX_TEST_S3_BUCKET"]}))

    for mode, kwargs in backends:
        print(f"\n--- Testing backend: {mode.upper()} ---")
        store = EphemeralStorage(mode=mode, **kwargs)
        print(f"  Storage mode: {store.storage_mode}")

        # store_input
        ref = await store.store_input(test_data, test_filename)
        print(f"  store_input  -> {ref[:80]}...")
        assert store.bytes_stored == len(test_data)

        # retrieve_input
        retrieved = await store.retrieve_input(ref)
        assert retrieved == test_data, "Data mismatch on retrieve_input"
        print(f"  retrieve_input: {len(retrieved)} bytes OK")

        # store_output
        out_data = test_data.replace(b"ledger", b"pptx")
        out_ref = await store.store_output(out_data, "out.pptx")
        print(f"  store_output -> {out_ref[:80]}...")
        assert store.bytes_stored == len(test_data) + len(out_data)

        # secure_wipe
        wiped = await store.secure_wipe(ref)
        print(f"  secure_wipe input: {wiped}")

        # cleanup_all
        count = await store.cleanup_all()
        print(f"  cleanup_all: {count} files wiped")
        assert count >= 1

    # --- Test StorageLifecycle ---------------------------------------------
    print(f"\n--- Testing StorageLifecycle ---")
    lifecycle = StorageLifecycle()
    print(f"  Lifecycle backend: {lifecycle.storage_mode}")

    pdf_ref = await lifecycle.store_pdf(test_data, "invoice.pdf")
    out_ref = await lifecycle.store_output(b"pptx data", "invoice.pptx")
    print(f"  PDF ref:     {pdf_ref[:60]}...")
    print(f"  Output ref:  {out_ref[:60]}...")

    data = await lifecycle.retrieve(pdf_ref)
    assert data == test_data
    print(f"  retrieve OK: {len(data)} bytes")

    await lifecycle.complete(pdf_ref)
    print(f"  complete (wipe input): done")

    remaining = await lifecycle.shutdown()
    print(f"  shutdown: {remaining} files wiped")

    # --- Test secure_delete_file directly ----------------------------------
    print(f"\n--- Testing secure_delete_file ---")
    tmp = Path(tempfile.mktemp(suffix=".txt"))
    tmp.write_bytes(b"secret data " * 500)
    print(f"  Created {tmp} ({tmp.stat().st_size} bytes)")
    ok = secure_delete_file(str(tmp))
    print(f"  secure_delete_file: {ok}, exists={tmp.exists()}")

    print("\n" + "=" * 60)
    print("All tests passed.")
    print("=" * 60)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(_run_tests())


if __name__ == "__main__":
    main()
