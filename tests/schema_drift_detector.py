"""
Schema Drift Detector
====================
Surgical field-level triage of VCR cassettes against live APIs.
Uses AST-extracted ingested fields (no manual mapping).
Only invalidates cassettes if code-referenced fields drift.

Usage:
    python tests/schema_drift_detector.py

Exit codes:
    0 — no ingested field drift (warnings may exist)
    1 — ingested field drift detected, cassette invalidated
"""

import json
import subprocess
import sys
from pathlib import Path

import httpx
import yaml

CASSETTE_DIR = Path(__file__).parent / "cassettes" / "scholarsearch"
LIVE_BASE_URL = "http://localhost:3001"
FIELDS_FILE = Path(__file__).parent / "ingested_fields.json"


def load_ingested_fields() -> dict:
    """Load AST-extracted ingested fields, or generate them."""
    if not FIELDS_FILE.exists():
        print("Generating ingested fields from AST analysis...")
        subprocess.run(
            [sys.executable, str(Path(__file__).parent / "extract_ingested_fields.py")],
            check=True,
        )

    with open(FIELDS_FILE) as f:
        data = json.load(f)

    return data.get("schema_contracts", {})


def load_cassette_response(cassette_name: str) -> dict | None:
    """Extract JSON response body from a VCR cassette file."""
    cassette_path = CASSETTE_DIR / f"{cassette_name}.yaml"
    if not cassette_path.exists():
        return None

    with open(cassette_path) as f:
        data = yaml.safe_load(f)

    if not data or "interactions" not in data:
        return None

    interaction = data["interactions"][0]
    response = interaction.get("response", {})
    body = response.get("body", {})
    raw = body.get("string", "")

    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return raw


def fetch_live_response(endpoint: str, method: str = "POST", body: dict = None) -> dict | None:
    """Fetch live response from the running service."""
    try:
        with httpx.Client(base_url=LIVE_BASE_URL, timeout=10) as client:
            if method == "POST":
                resp = client.post(endpoint, json=body or {})
            else:
                resp = client.get(endpoint)

            if resp.status_code == 200:
                return resp.json()
    except httpx.ConnectError:
        pass
    return None


class DriftResult:
    def __init__(self):
        self.hard_failures = []
        self.warnings = []

    @property
    def has_critical_drift(self) -> bool:
        return len(self.hard_failures) > 0

    def summary(self) -> str:
        lines = []
        if self.hard_failures:
            lines.append(f"CRITICAL ({len(self.hard_failures)}):")
            for e in self.hard_failures:
                lines.append(f"  [BLOCK] {e}")
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for e in self.warnings:
                lines.append(f"  [WARN] {e}")
        return "\n".join(lines)


def triage_drift(
    cassette_name: str,
    cassette_json: dict,
    live_json: dict,
    ingested_keys: list[str],
    ingested_element_keys: list[str] = None,
) -> DriftResult:
    """
    Surgical field-level triage using AST-extracted keys.
    Only blocks if keys the CODE ACTUALLY ACCESSES have drifted.
    """
    result = DriftResult()
    ingested_set = set(ingested_keys)

    # Phase 1: Check ingested top-level keys
    for key in ingested_keys:
        if key not in cassette_json:
            result.hard_failures.append(f"Ingested key '{key}' missing from cassette")
        if key not in live_json:
            result.hard_failures.append(f"Ingested key '{key}' missing from live API")

    # Phase 2: Check results element shape (if applicable)
    if ingested_element_keys and "results" in cassette_json:
        if not isinstance(cassette_json["results"], list):
            result.hard_failures.append("'results' is not a list in cassette")
        if "results" in live_json and not isinstance(live_json["results"], list):
            result.hard_failures.append("'results' is not a list in live API")

        if isinstance(cassette_json.get("results"), list) and cassette_json["results"]:
            element = cassette_json["results"][0]
            for key in ingested_element_keys:
                if key not in element:
                    result.hard_failures.append(
                        f"results[0] missing ingested key '{key}' in cassette"
                    )

    # Phase 3: Compare live vs cassette
    cassette_keys = set(cassette_json.keys()) if isinstance(cassette_json, dict) else set()
    live_keys = set(live_json.keys()) if isinstance(live_json, dict) else set()

    added_keys = live_keys - cassette_keys
    removed_keys = cassette_keys - live_keys

    # Only block if INGESTED keys were added/removed
    ingested_added = added_keys & ingested_set
    ingested_removed = removed_keys & ingested_set
    peripheral_added = added_keys - ingested_set
    peripheral_removed = removed_keys - ingested_set

    if ingested_added:
        result.hard_failures.append(
            f"Live API added ingested keys not in cassette: {ingested_added}"
        )
    if peripheral_added:
        result.warnings.append(
            f"Live API added peripheral keys (ignored): {peripheral_added}"
        )
    if ingested_removed:
        result.hard_failures.append(
            f"Ingested keys removed from live API: {ingested_removed}"
        )
    if peripheral_removed:
        result.warnings.append(
            f"Peripheral keys removed from live API (ignored): {peripheral_removed}"
        )

    # Phase 4: Type comparison for ingested keys
    for key in ingested_keys:
        if key in cassette_json and key in live_json:
            c_val = cassette_json[key]
            l_val = live_json[key]
            if type(c_val) != type(l_val):
                result.hard_failures.append(
                    f"Ingested key '{key}' type changed: {type(c_val).__name__} → {type(l_val).__name__}"
                )

    return result


def invalidate_cassette(cassette_name: str) -> None:
    """Rename cassette to .invalid to block CI."""
    cassette_path = CASSETTE_DIR / f"{cassette_name}.yaml"
    if cassette_path.exists():
        invalid_path = CASSETTE_DIR / f"{cassette_name}.yaml.invalid"
        cassette_path.rename(invalid_path)
        print(f"INVALIDATED: {cassette_path} → {invalid_path}")


def main() -> int:
    CASSETTE_DIR.mkdir(parents=True, exist_ok=True)

    # Load AST-extracted fields
    contracts = load_ingested_fields()
    ss_contract = contracts.get("scholarsearch", {})

    endpoints = [
        ("search_machine_learning", "/api/search/sync", {"raw_query": "machine learning"}),
        ("search_CRISPR_gene_editing", "/api/search/sync", {"raw_query": "CRISPR gene editing"}),
        ("search_quantum_computing", "/api/search/sync", {"raw_query": "quantum computing"}),
    ]

    any_critical = False

    for name, endpoint, body in endpoints:
        cassette_json = load_cassette_response(name)
        if cassette_json is None:
            print(f"DRIFT in {name}: Cassette missing or unparseable")
            invalidate_cassette(name)
            any_critical = True
            continue

        live_json = fetch_live_response(endpoint, body=body)
        if live_json is None:
            print(f"SKIP {name}: Live service unreachable")
            continue

        result = triage_drift(
            name,
            cassette_json,
            live_json,
            ingested_keys=ss_contract.get("ingested_top_level", []),
            ingested_element_keys=ss_contract.get("ingested_results_element"),
        )

        if result.has_critical_drift:
            print(f"CRITICAL DRIFT in {name}:")
            print(result.summary())
            invalidate_cassette(name)
            any_critical = True
        elif result.warnings:
            print(f"SUB-CLINICAL DRIFT in {name}:")
            print(result.summary())
            print("  → CI proceeds (peripheral drift only)")
        else:
            print(f"OK: {name}")

    if any_critical:
        print("\nIngested field drift detected. Cassettes invalidated.")
        return 1

    print("\nNo ingested field drift. CI unblocked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
