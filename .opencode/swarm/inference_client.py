#!/usr/bin/env python3
"""
Swarm Cascade — Live Inference Client
Pluggable 8B model clients with GBNF logit masking for Blind Matrix.

Supports:
  - Ollama (http://localhost:11434) — grammar via JSON format fallback + prompt-enforced schema
  - llama.cpp server (http://localhost:8080) — native GBNF grammar field
  - MockModelClient — deterministic stub for tests / pipeline validation

Env:
  SWARM_MODEL_CLIENT=ollama|llamacpp|mock  (default: mock)
  SWARM_MODEL_URL=http://localhost:11434   (ollama) or http://localhost:8080 (llamacpp)
  SWARM_MODEL_NAME=mistral:7b-instruct     (ollama) or /path/to/model.gguf (llamacpp: no-op)
  SWARM_MODEL_TEMPERATURE=0.1
"""

import json
import os
import re
import urllib.request
import urllib.error
from typing import Optional

from .blind_matrix import GBNF_GRAMMAR


def _gbnf_to_ollama_format() -> dict:
    """Convert GBNF to Ollama JSON format hint (Ollama grammar is modelfile-level; we enforce via prompt + regex validation)."""
    return {
        "type": "object",
        "properties": {
            "category": {"type": "integer", "minimum": 1, "maximum": 4},
            "boundary": {"type": "string", "maxLength": 250},
        },
        "required": ["category", "boundary"],
    }


def validate_gbnf_output(raw: str, max_len: int = 250) -> bool:
    """Check raw matches GBNF: <1-4> <boundary up to 250>."""
    if not raw or not raw.strip():
        return False
    m = re.match(r"^([1-4]) (.{1,250})\s*$", raw.strip(), flags=re.DOTALL)
    if not m:
        return False
    return 1 <= int(m.group(1)) <= 4 and 1 <= len(m.group(2).strip()) <= max_len


class MockModelClient:
    """Deterministic stub — returns static Population_Mismatch for pipeline tests."""

    def __init__(self, canned: str = "1 Population_Mismatch: Atropine and orthokeratology target different age groups"):
        self.canned = canned

    def generate(self, prompt: str, grammar: str = GBNF_GRAMMAR, max_tokens: int = 256, temperature: float = 0.1) -> str:
        return self.canned


class OllamaClient:
    """
    Ollama client — POST /api/generate with prompt + format enforcement.
    GBNF is enforced via prompt instruction + post-validation (Ollama grammar requires custom modelfile; format does JSON, so we parse JSON→GBNF).
    If Ollama returns JSON, we convert to GBNF string; if raw text, we validate directly.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        timeout: int = 120,
    ):
        self.base_url = (base_url or os.environ.get("SWARM_MODEL_URL") or "http://localhost:11434").rstrip("/")
        self.model = model or os.environ.get("SWARM_MODEL_NAME") or "mistral:7b-instruct"
        self.temperature = float(os.environ.get("SWARM_MODEL_TEMPERATURE", str(temperature)))
        self.timeout = timeout

    def generate(self, prompt: str, grammar: str = GBNF_GRAMMAR, max_tokens: int = 512, temperature: float = 0.1) -> str:
        temp = float(temperature) if temperature is not None else self.temperature
        # Enforce GBNF via prompt — do NOT use format=json (GBNF is plain "1 boundary", not JSON)
        gbnf_instruction = (
            "\n\nSTRICT OUTPUT: Reply with exactly one line in GBNF format: '<category 1-4> <boundary 1-250 chars>'"
            " Example: '1 Population_Mismatch: optical zone 6mm'"
            " Do not wrap in JSON."
        )
        full_prompt = prompt + gbnf_instruction
        body = json.dumps({
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": temp, "num_predict": max_tokens},
        }).encode()
        req = urllib.request.Request(f"{self.base_url}/api/generate", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                raw = data.get("response", "")
                # If Ollama honored format=json, raw will be JSON like {"category":1,"boundary":"..."} — convert to GBNF
                raw_stripped = raw.strip()
                if raw_stripped.startswith("{"):
                    try:
                        j = json.loads(raw_stripped)
                        cat = int(j.get("category", 4))
                        bnd = str(j.get("boundary", "None")).strip()
                        candidate = f"{cat} {bnd}"
                        if validate_gbnf_output(candidate):
                            return candidate
                    except Exception:
                        pass
                if validate_gbnf_output(raw_stripped):
                    return raw_stripped
                # Fallback: extract first GBNF-like line
                for line in raw.splitlines():
                    if validate_gbnf_output(line):
                        return line.strip()
                return raw_stripped[:300] if raw_stripped else "4 None"
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama unavailable at {self.base_url} (model={self.model}): {e}. Start with: ollama serve && ollama pull {self.model}") from e


class LlamaCppClient:
    """
    llama.cpp server client — POST /completion with native grammar field.
    Server must be started with: ./llama-server -m model.gguf --port 8080 --grammar-file gbnf ...
    Actually we pass grammar per-request via JSON field 'grammar'.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        timeout: int = 120,
    ):
        self.base_url = (base_url or os.environ.get("SWARM_MODEL_URL") or "http://localhost:8080").rstrip("/")
        self.temperature = float(os.environ.get("SWARM_MODEL_TEMPERATURE", str(temperature)))
        self.timeout = timeout

    def generate(self, prompt: str, grammar: str = GBNF_GRAMMAR, max_tokens: int = 256, temperature: float = 0.1) -> str:
        temp = float(temperature) if temperature is not None else self.temperature
        body = json.dumps({
            "prompt": prompt,
            "grammar": grammar,
            "temperature": temp,
            "n_predict": max_tokens,
            "stream": False,
        }).encode()
        req = urllib.request.Request(f"{self.base_url}/completion", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                # llama.cpp returns {"content": "...", ...}
                raw = data.get("content") or data.get("response") or ""
                raw = raw.strip()
                if validate_gbnf_output(raw):
                    return raw
                for line in raw.splitlines():
                    if validate_gbnf_output(line):
                        return line.strip()
                return raw[:300] if raw else "4 None"
        except urllib.error.URLError as e:
            raise RuntimeError(f"llama.cpp server unavailable at {self.base_url}/completion: {e}. Start with: llama-server -m <model.gguf> --port 8080") from e


def get_model_client():
    """
    Factory — reads SWARM_MODEL_CLIENT env.
    Returns (client, label) for logging.
    """
    kind = (os.environ.get("SWARM_MODEL_CLIENT") or "mock").lower()
    if kind == "ollama":
        return OllamaClient(), f"ollama:{os.environ.get('SWARM_MODEL_NAME','mistral:7b-instruct')}@{os.environ.get('SWARM_MODEL_URL','http://localhost:11434')}"
    if kind in ("llamacpp", "llama.cpp", "llama_cpp"):
        return LlamaCppClient(), f"llamacpp@{os.environ.get('SWARM_MODEL_URL','http://localhost:8080')}"
    return MockModelClient(), "mock"
