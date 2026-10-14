#!/usr/bin/env python3
"""Audit provenance manifest — fail-closed, stdlib only.

Problem: Audit runs without provenance cannot meet Protocol v7.6 auditability.
Evidence: swarm/inference_client.py has temp 0.1, no seed/hash/backend log.
Benefit: known inputs -> known context -> constrained output -> validated result.
Cost: caller must supply all mandatory fields; missing field = hard fail.
Failure modes: F3 provenance failure -> FAIL CLOSED, no downgrade.
Rollback: delete audit/ outputs; committed trio untouched.
"""
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field

MANDATORY = [
    "run_id", "git_commit", "protocol_version", "model_id", "model_sha256",
    "prompt_hash", "input_hash", "schema_hash", "grammar_hash", "seed",
    "sampling_parameters", "backend", "compiler_type",
]

@dataclass(frozen=True)
class AuditManifest:
    run_id: str
    timestamp: str
    git_commit: str
    protocol_version: str = "v7.6"
    model_id: str = ""
    model_sha256: str = ""
    runtime_version: str = ""
    llama_cpp_version: str = ""
    prompt_hash: str = ""
    input_hash: str = ""
    schema_hash: str = ""
    grammar_hash: str = ""
    retrieval_manifest_hash: str = ""
    retrieval_span_hashes: tuple = ()
    seed: int = 42
    sampling_parameters: dict = field(default_factory=dict)
    backend: str = ""
    compiler_type: str = ""  # Framework 2: "human_manual" when hand-written parser acts as compiler
    hardware_summary: str = ""
    context_token_count: int = 0
    output_token_count: int = 0
    status: str = "pending"
    failure_class: str = ""

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def validate_fail_closed(m: AuditManifest) -> None:
    """F3: any missing mandatory provenance -> raise, never downgrade."""
    d = asdict(m)
    missing = [k for k in MANDATORY if not d.get(k)]
    if missing:
        raise ValueError(f"F3 provenance failure, missing: {missing}")
    if "secret" in json.dumps(d).lower() or "api_key" in json.dumps(d).lower():
        raise ValueError("F3: manifest must not contain secrets")

def write_manifest(m: AuditManifest, out_path: str) -> str:
    validate_fail_closed(m)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(asdict(m), f, indent=2, sort_keys=True)
    return sha256_file(out_path)

if __name__ == "__main__":
    raise SystemExit("import only; no direct execution against corpus")
