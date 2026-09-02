#!/usr/bin/env python3
"""
OpenCode Model Proxy — Network Layer Rewrite

Intercepts OpenCode requests, rewrites display names to canonical slugs,
and implements cascading fallback on 401/403 errors.

Architecture:
  OpenCode → localhost:20129 (this proxy) → localhost:20128 (OmniRoute)
  
This isolates OpenCode from OmniRoute's internal mapping fragility.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import time

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import StreamingResponse
    import uvicorn
    import httpx
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("ERROR: pip install fastapi uvicorn httpx")
    sys.exit(1)


# ============================================================================
# MODEL ALIAS MAP — Load from config or use hardcoded defaults
# ============================================================================

ALIAS_MAP_PATH = Path(__file__).parent / ".opencode" / "model-aliases.json"

def load_alias_map() -> Dict[str, Dict]:
    """Load model alias mapping from config file."""
    defaults = {
        "north-mini-code-free": {
            "canonical": "cohere/north-mini-code:free",
            "fallbacks": ["google/gemini-flash-1.5:free", "meta-llama/llama-3.1-8b-instruct:free"],
        },
        "big-pickle": {
            "canonical": "openchat/openchat-3.5-0106:free",
            "fallbacks": ["meta-llama/llama-3.1-8b-instruct:free"],
        },
        "muse-spark-1.2": {
            "canonical": "nousresearch/hermes-3-llama-3.1-405b:free",
            "fallbacks": ["meta-llama/llama-3.1-70b-instruct:free"],
        },
        "deepseek-v4-flash-free": {
            "canonical": "deepseek/deepseek-chat:free",
            "fallbacks": ["google/gemini-flash-1.5:free"],
        },
        "mimo-v2.5-free": {
            "canonical": "xiaomi/mimo-v2.5-free",
            "fallbacks": ["google/gemini-flash-1.5:free"],
        },
    }
    
    if ALIAS_MAP_PATH.exists():
        try:
            data = json.loads(ALIAS_MAP_PATH.read_text())
            return data.get("aliases", defaults)
        except Exception:
            pass
    return defaults


# Strip provider prefixes that OpenCode injects
def normalize_model_id(model_id: str) -> str:
    """Strip opencode/, oc/, openrouter/ prefixes."""
    for prefix in ["opencode/", "oc/", "openrouter/"]:
        if model_id.startswith(prefix):
            model_id = model_id[len(prefix):]
    return model_id.strip()


def resolve_model(display_name: str) -> Tuple[str, List[str]]:
    """Resolve display name to (canonical_slug, fallback_slugs)."""
    normalized = normalize_model_id(display_name).lower()
    alias_map = load_alias_map()
    
    # Direct lookup
    if normalized in alias_map:
        entry = alias_map[normalized]
        return entry["canonical"], entry.get("fallbacks", [])
    
    # Fuzzy match (strip spaces, hyphens)
    clean = normalized.replace(" ", "-").replace("_", "-")
    for key, entry in alias_map.items():
        if key.replace(" ", "-").replace("_", "-") == clean:
            return entry["canonical"], entry.get("fallbacks", [])
    
    # Unknown model — return as-is, let OmniRoute handle it
    return display_name, []


# ============================================================================
# REQUEST REWRITER
# ============================================================================

def rewrite_request(body: dict) -> dict:
    """Rewrite model IDs in the request body."""
    if "model" in body:
        original = body["model"]
        canonical, _ = resolve_model(original)
        if canonical != original:
            body["model"] = canonical
            print(f"[REWRITE] {original} -> {canonical}")
    return body


# ============================================================================
# FASTAPI APP — Reverse Proxy with Rewrite
# ============================================================================

app = FastAPI(title="OpenCode Model Proxy")

OMNIRoute_BASE = os.getenv("OMNIRoute_BASE_URL", "http://127.0.0.1:20128")
PROXY_PORT = int(os.getenv("PROXY_PORT", "20129"))
MAX_FALLBACK_ATTEMPTS = 3

# Track fallback state per request
request_fallback_state: Dict[str, Dict] = {}


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    """Proxy chat completion requests with model rewrite + fallback."""
    body = await request.json()
    original_model = body.get("model", "unknown")
    
    # Rewrite the model ID
    body = rewrite_request(body)
    rewritten_model = body.get("model", original_model)
    
    # Get fallback chain
    _, fallbacks = resolve_model(original_model)
    all_models = [rewritten_model] + fallbacks
    
    # Try primary, then fallbacks
    last_error = None
    async with httpx.AsyncClient(timeout=120.0) as client:
        for attempt, model in enumerate(all_models[:MAX_FALLBACK_ATTEMPTS]):
            body["model"] = model
            
            # Forward headers (strip OpenCode auth, let OmniRoute handle it)
            headers = {}
            for key, value in request.headers.items():
                if key.lower() not in ("host", "content-length", "transfer-encoding"):
                    headers[key] = value
            
            try:
                response = await client.post(
                    f"{OMNIRoute_BASE}/v1/chat/completions",
                    json=body,
                    headers=headers,
                )
                
                if response.status_code in (401, 403, 404):
                    print(f"[FALLBACK] {model} returned {response.status_code}, trying next...")
                    last_error = response.status_code
                    continue
                
                # Success — return response
                if attempt > 0:
                    print(f"[FALLBACK] Success on attempt {attempt + 1}: {model}")
                
                # Stream or buffer response
                if body.get("stream"):
                    return StreamingResponse(
                        response.aiter_bytes(),
                        status_code=response.status_code,
                        media_type="text/event-stream",
                    )
                else:
                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        media_type="application/json",
                    )
                    
            except httpx.RequestError as e:
                print(f"[FALLBACK] Connection error for {model}: {e}")
                last_error = str(e)
                continue
    
    # All attempts failed
    return Response(
        content=json.dumps({
            "error": {
                "message": f"All models failed after {len(all_models[:MAX_FALLBACK_ATTEMPTS])} attempts",
                "type": "model_routing_error",
                "last_error": str(last_error),
                "attempted_models": all_models[:MAX_FALLBACK_ATTEMPTS],
            }
        }),
        status_code=502,
        media_type="application/json",
    )


@app.post("/v1/{path:path}")
async def proxy_generic(path: str, request: Request):
    """Generic proxy for other OpenAI-compatible endpoints."""
    body = await request.body()
    
    # Try to parse and rewrite JSON bodies
    try:
        body_dict = json.loads(body)
        if "model" in body_dict:
            body_dict = rewrite_request(body_dict)
            body = json.dumps(body_dict).encode()
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ("host", "content-length", "transfer-encoding"):
            headers[key] = value
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.request(
            method=request.method,
            url=f"{OMNIRoute_BASE}/v1/{path}",
            content=body,
            headers=headers,
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json"),
        )


@app.get("/v1/models")
async def proxy_models():
    """Proxy model listing, rewriting display names to slugs."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{OMNIRoute_BASE}/v1/models")
        data = response.json()
        
        # Rewrite model IDs in the response
        if "data" in data:
            for model in data["data"]:
                if "id" in model:
                    canonical, _ = resolve_model(model["id"])
                    model["id"] = canonical
        
        return Response(
            content=json.dumps(data),
            media_type="application/json",
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "proxy_port": PROXY_PORT, "upstream": OMNIRoute_BASE}


@app.get("/")
async def root():
    """Root endpoint with proxy info."""
    return {
        "service": "OpenCode Model Proxy",
        "proxy_port": PROXY_PORT,
        "upstream": OMNIRoute_BASE,
        "alias_map_loaded": len(load_alias_map()),
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print(f"OpenCode Model Proxy starting on port {PROXY_PORT}")
    print(f"Upstream: {OMNIRoute_BASE}")
    print(f"Alias map: {len(load_alias_map())} models loaded")
    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT)
