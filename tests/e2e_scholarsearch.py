"""
E2E Contract Tests — scholarsearch
====================================
Black-box validation of external API contracts.
Air-gapped: all external API responses are replayed from cassettes.

These tests gate dependency updates. If any test fails after a bump,
the merge is blocked until the contract is restored or intentionally changed.
"""

import os
from pathlib import Path

import httpx
import pytest
import vcr

BASE_URL = os.getenv("SCHOLARSEARCH_URL", "http://localhost:3001")
TIMEOUT = 30

CASSETTE_DIR = Path(__file__).parent / "cassettes" / "scholarsearch"
CASSETTE_DIR.mkdir(parents=True, exist_ok=True)


def _cassette_path(name: str) -> Path:
    return CASSETTE_DIR / f"{name}.yaml"


def _vcr():
    return vcr.VCR(
        record_mode="none",
        match_on=["method", "scheme", "host", "port", "path", "query"],
        decode_compressed_response=True,
    )


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as c:
        yield c


class TestHealthContract:
    """Contract: GET /health returns 200 with status 'ok'."""

    def test_health_returns_200(self, client: httpx.Client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_status_ok(self, client: httpx.Client):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_has_service_name(self, client: httpx.Client):
        resp = client.get("/health")
        data = resp.json()
        assert "service" in data
        assert data["service"] == "scholarsearch-backend"


class TestSearchSyncContract:
    """
    Contract: POST /api/search/sync returns structured search results.
    Uses VCR cassettes to replay deterministic responses.
    If cassette is missing, test fails with explicit message — no live calls.
    """

    def _search(self, client: httpx.Client, query: str) -> httpx.Response:
        cassette = _cassette_path(f"search_{query.replace(' ', '_')}")
        if not cassette.exists():
            pytest.fail(
                f"Missing cassette: {cassette}. "
                f"Record locally with: vcrpy.record — then commit the cassette."
            )
        with _vcr().use_cassette(str(cassette)):
            return client.post(
                "/api/search/sync",
                json={"raw_query": query},
            )

    def test_sync_search_returns_200(self, client: httpx.Client):
        resp = self._search(client, "machine_learning")
        assert resp.status_code == 200

    def test_sync_search_has_results_array(self, client: httpx.Client):
        resp = self._search(client, "CRISPR_gene_editing")
        data = resp.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_sync_search_has_metadata(self, client: httpx.Client):
        resp = self._search(client, "quantum_computing")
        data = resp.json()
        for key in ("totalDeduplicated", "searchId", "durationMs"):
            assert key in data, f"Missing metadata key: {key}"


class TestSearchValidationContract:
    """Contract: Missing raw_query returns 400."""

    def test_empty_body_returns_400(self, client: httpx.Client):
        resp = client.post("/api/search/sync", json={})
        assert resp.status_code == 400

    def test_error_message_includes_raw_query(self, client: httpx.Client):
        resp = client.post("/api/search/sync", json={})
        data = resp.json()
        assert "error" in data
        assert "raw_query" in data["error"]
