"""
E2E Contract Tests — pdf-engine
================================
Black-box validation of external API contracts.
Air-gapped: tests run against local service only, no external dependencies.

These tests gate dependency updates. If any test fails after a bump,
the merge is blocked until the contract is restored or intentionally changed.
"""

import os
import tempfile
from pathlib import Path

import httpx
import pytest

BASE_URL = os.getenv("PDF_ENGINE_URL", "http://localhost:8000")
TIMEOUT = 30


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as c:
        yield c


@pytest.fixture
def sample_pdf():
    """Create a minimal valid PDF for testing."""
    pdf_bytes = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
206
%%EOF"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        return Path(f.name)


class TestHealthContract:
    """Contract: GET /v1/health returns 200 with status field."""

    def test_health_returns_200(self, client: httpx.Client):
        resp = client.get("/v1/health")
        assert resp.status_code == 200

    def test_health_contains_status(self, client: httpx.Client):
        resp = client.get("/v1/health")
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("ok", "healthy", "ready")


class TestConvertContract:
    """Contract: POST /v1/convert accepts PDF, returns 202 with job_id."""

    def test_convert_returns_202(self, client: httpx.Client, sample_pdf: Path):
        with open(sample_pdf, "rb") as f:
            resp = client.post(
                "/v1/convert",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        assert resp.status_code == 202

    def test_convert_returns_job_id(self, client: httpx.Client, sample_pdf: Path):
        with open(sample_pdf, "rb") as f:
            resp = client.post(
                "/v1/convert",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        data = resp.json()
        assert "job_id" in data or "id" in data

    def test_convert_rejects_non_pdf(self, client: httpx.Client):
        resp = client.post(
            "/v1/convert",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
        )
        assert resp.status_code in (400, 415, 422)


class TestJobLifecycleContract:
    """Contract: Job can be queried and cancelled via REST."""

    def _create_job(self, client: httpx.Client, sample_pdf: Path) -> str:
        with open(sample_pdf, "rb") as f:
            resp = client.post(
                "/v1/convert",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        data = resp.json()
        return data.get("job_id") or data.get("id")

    def test_job_status_returns_200(self, client: httpx.Client, sample_pdf: Path):
        job_id = self._create_job(client, sample_pdf)
        resp = client.get(f"/v1/jobs/{job_id}")
        assert resp.status_code == 200

    def test_job_status_has_state(self, client: httpx.Client, sample_pdf: Path):
        job_id = self._create_job(client, sample_pdf)
        resp = client.get(f"/v1/jobs/{job_id}")
        data = resp.json()
        assert "status" in data or "state" in data

    def test_cancel_returns_success(self, client: httpx.Client, sample_pdf: Path):
        job_id = self._create_job(client, sample_pdf)
        resp = client.delete(f"/v1/jobs/{job_id}")
        assert resp.status_code in (200, 204)
