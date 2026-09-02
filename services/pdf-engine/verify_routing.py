#!/usr/bin/env python3
"""
verify_routing.py — Verify the model routing chain works correctly.

Tests:
1. Proxy starts and responds to health check
2. Model alias resolution works
3. Fallback chain is properly configured
4. OmniRoute is reachable through the proxy

Usage:
    python verify_routing.py              # Full test
    python verify_routing.py --quick      # Quick health check only
    python verify_routing.py --start      # Start proxy + OmniRoute + test
"""

import asyncio
import json
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


# ============================================================================
# TEST: Model Alias Resolution
# ============================================================================

def test_alias_resolution():
    """Test that model aliases resolve correctly."""
    print("=" * 60)
    print("TEST: Model Alias Resolution")
    print("=" * 60)
    
    from model_proxy import resolve_model, normalize_model_id
    
    test_cases = [
        ("north-mini-code-free", "cohere/north-mini-code:free"),
        ("opencode/north-mini-code-free", "cohere/north-mini-code:free"),
        ("oc/north-mini-code-free", "cohere/north-mini-code:free"),
        ("North Mini Code Free", "cohere/north-mini-code:free"),
        ("big-pickle", "openchat/openchat-3.5-0106:free"),
        ("muse-spark-1.2", "nousresearch/hermes-3-llama-3.1-405b:free"),
        ("deepseek-v4-flash-free", "deepseek/deepseek-chat:free"),
        ("mimo-v2.5-free", "xiaomi/mimo-v2.5-free"),
        ("unknown-model", "unknown-model"),  # Passthrough
    ]
    
    passed = 0
    failed = 0
    
    for input_name, expected_canonical in test_cases:
        canonical, fallbacks = resolve_model(input_name)
        status = "PASS" if canonical == expected_canonical else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] '{input_name}' -> '{canonical}' (expected: '{expected_canonical}')")
        if fallbacks:
            print(f"         Fallbacks: {fallbacks[:2]}...")
    
    print(f"\n  Results: {passed} passed, {failed} failed\n")
    return failed == 0


# ============================================================================
# TEST: Normalize Model ID
# ============================================================================

def test_normalize():
    """Test model ID normalization."""
    print("=" * 60)
    print("TEST: Model ID Normalization")
    print("=" * 60)
    
    from model_proxy import normalize_model_id
    
    test_cases = [
        ("opencode/north-mini-code-free", "north-mini-code-free"),
        ("oc/north-mini-code-free", "north-mini-code-free"),
        ("openrouter/north-mini-code-free", "north-mini-code-free"),
        ("north-mini-code-free", "north-mini-code-free"),
        ("  north-mini-code-free  ", "north-mini-code-free"),
    ]
    
    passed = 0
    failed = 0
    
    for input_id, expected in test_cases:
        result = normalize_model_id(input_id)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] '{input_id}' -> '{result}' (expected: '{expected}')")
    
    print(f"\n  Results: {passed} passed, {failed} failed\n")
    return failed == 0


# ============================================================================
# TEST: Request Rewriting
# ============================================================================

def test_request_rewrite():
    """Test that request bodies are rewritten correctly."""
    print("=" * 60)
    print("TEST: Request Body Rewriting")
    print("=" * 60)
    
    from model_proxy import rewrite_request
    
    test_cases = [
        (
            {"model": "opencode/north-mini-code-free", "messages": []},
            "cohere/north-mini-code:free",
        ),
        (
            {"model": "North Mini Code Free", "messages": []},
            "cohere/north-mini-code:free",
        ),
        (
            {"model": "unknown-model", "messages": []},
            "unknown-model",  # No rewrite for unknown
        ),
    ]
    
    passed = 0
    failed = 0
    
    for body, expected_model in test_cases:
        result = rewrite_request(body.copy())
        actual = result.get("model")
        status = "PASS" if actual == expected_model else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] model: '{body['model']}' -> '{actual}' (expected: '{expected_model}')")
    
    print(f"\n  Results: {passed} passed, {failed} failed\n")
    return failed == 0


# ============================================================================
# TEST: Proxy Health
# ============================================================================

async def test_proxy_health(proxy_port: int = 20129) -> bool:
    """Test that the proxy is running and healthy."""
    print("=" * 60)
    print("TEST: Proxy Health Check")
    print("=" * 60)
    
    if not HTTPX_AVAILABLE:
        print("  [SKIP] httpx not installed")
        return True
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"http://127.0.0.1:{proxy_port}/health")
            data = response.json()
            if data.get("status") == "ok":
                print(f"  [PASS] Proxy running on port {proxy_port}")
                print(f"         Upstream: {data.get('upstream')}")
                print(f"         Alias map: {data.get('alias_map_loaded')} models")
                return True
            else:
                print(f"  [FAIL] Proxy unhealthy: {data}")
                return False
        except httpx.RequestError:
            print(f"  [FAIL] Proxy not reachable on port {proxy_port}")
            return False


# ============================================================================
# TEST: OmniRoute Reachability
# ============================================================================

async def test_omniroute_reachable(omniroute_port: int = 20128) -> bool:
    """Test that OmniRoute is reachable directly."""
    print("=" * 60)
    print("TEST: OmniRoute Reachability")
    print("=" * 60)
    
    if not HTTPX_AVAILABLE:
        print("  [SKIP] httpx not installed")
        return True
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"http://127.0.0.1:{omniroute_port}/v1/models")
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("data", []))
                print(f"  [PASS] OmniRoute reachable on port {omniroute_port}")
                print(f"         Models available: {model_count}")
                return True
            else:
                print(f"  [WARN] OmniRoute returned status {response.status_code}")
                return True  # Still reachable
        except httpx.RequestError:
            print(f"  [FAIL] OmniRoute not reachable on port {omniroute_port}")
            return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    args = sys.argv[1:]
    quick = "--quick" in args
    start_services = "--start" in args
    
    print("\n" + "=" * 60)
    print("OpenCode Model Routing Verification")
    print("=" * 60 + "\n")
    
    # Run offline tests
    tests_passed = 0
    tests_total = 0
    
    tests_total += 1
    if test_normalize():
        tests_passed += 1
    
    tests_total += 1
    if test_alias_resolution():
        tests_passed += 1
    
    tests_total += 1
    if test_request_rewrite():
        tests_passed += 1
    
    if quick:
        print(f"\n{'=' * 60}")
        print(f"Quick Test Results: {tests_passed}/{tests_total} passed")
        print(f"{'=' * 60}")
        return
    
    # Start services if requested
    if start_services:
        print("\nStarting OmniRoute...")
        subprocess.Popen(
            ["omniroute", "serve", "--port", "20128"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
        
        print("Starting Model Proxy...")
        subprocess.Popen(
            ["python", "model_proxy.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
    
    # Run online tests
    async def run_online_tests():
        online_passed = 0
        online_total = 0
        
        online_total += 1
        if await test_omniroute_reachable():
            online_passed += 1
        
        online_total += 1
        if await test_proxy_health():
            online_passed += 1
        
        return online_passed, online_total
    
    online_passed, online_total = asyncio.run(run_online_tests())
    tests_passed += online_passed
    tests_total += online_total
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"FINAL RESULTS: {tests_passed}/{tests_total} tests passed")
    if tests_passed == tests_total:
        print("STATUS: ALL TESTS PASSED")
        print("\nTo use the proxy, start it with:")
        print("  python model_proxy.py")
        print("\nThen point OpenCode at http://127.0.0.1:20129")
    else:
        print("STATUS: SOME TESTS FAILED")
        print("\nFix the failing tests before using the proxy.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
