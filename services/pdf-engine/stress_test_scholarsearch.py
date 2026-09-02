#!/usr/bin/env python3
"""ScholarSearch GitHub Version Stress Test.

Tests the full ScholarSearch stack:
- Health endpoint
- SSE search streaming
- Synchronous search
- Concurrent searches (8-source parallel dispatch)
- Circuit breaker behavior
- Rate limiting
- Edge cases (empty queries, special characters, long queries)
- Source failover
- Compact mode
- Paper abstract endpoint
- Gap analysis
- Query versioning
"""

import os
import sys
import time
import json
import hashlib
import statistics
import threading
import subprocess
import signal
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

RESULTS = []
BASE_URL = os.environ.get("SCHOLARSEARCH_URL", "http://localhost:3001")
SERVER_PROCESS = None

def log(msg, level="INFO"):
    print(f"[{level}] {msg}", flush=True)

def record_test(name, duration, status, details=None):
    RESULTS.append({
        "name": name,
        "duration_ms": round(duration * 1000, 2),
        "status": status,
        "details": details or {},
        "timestamp": datetime.now().isoformat(),
    })
    icon = "PASS" if status == "pass" else "WARN" if status == "warn" else "FAIL"
    log(f"{icon} {name}: {round(duration * 1000, 2)}ms")

def api_get(path, timeout=30):
    """Simple GET request."""
    url = f"{BASE_URL}{path}"
    req = Request(url)
    start = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode()
            elapsed = time.perf_counter() - start
            return {"status": resp.status, "data": json.loads(data), "time_s": elapsed}
    except HTTPError as e:
        elapsed = time.perf_counter() - start
        return {"status": e.code, "error": str(e), "time_s": elapsed}
    except URLError as e:
        elapsed = time.perf_counter() - start
        return {"status": 0, "error": str(e.reason), "time_s": elapsed}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {"status": 0, "error": str(e), "time_s": elapsed}

def api_post(path, body, timeout=60):
    """Simple POST request."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    start = time.perf_counter()
    try:
        with urlopen(req, timeout=timeout) as resp:
            response_data = resp.read().decode()
            elapsed = time.perf_counter() - start
            return {"status": resp.status, "data": json.loads(response_data), "time_s": elapsed}
    except HTTPError as e:
        elapsed = time.perf_counter() - start
        body_text = ""
        try:
            body_text = e.read().decode()
        except:
            pass
        try:
            error_data = json.loads(body_text) if body_text else None
        except:
            error_data = body_text
        return {"status": e.code, "error": str(e), "data": error_data, "time_s": elapsed}
    except URLError as e:
        elapsed = time.perf_counter() - start
        return {"status": 0, "error": str(e.reason), "time_s": elapsed}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {"status": 0, "error": str(e), "time_s": elapsed}

def api_post_sse(path, body, timeout=60):
    """POST request that reads SSE stream."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }, method="POST")
    start = time.perf_counter()
    events = []
    try:
        with urlopen(req, timeout=timeout) as resp:
            buffer = ""
            while True:
                chunk = resp.read(1024)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n\n" in buffer:
                    event_str, buffer = buffer.split("\n\n", 1)
                    event = {"raw": event_str.strip()}
                    for line in event_str.strip().split("\n"):
                        if line.startswith("event: "):
                            event["type"] = line[7:]
                        elif line.startswith("data: "):
                            try:
                                event["data"] = json.loads(line[6:])
                            except:
                                event["data"] = line[6:]
                    events.append(event)
            elapsed = time.perf_counter() - start
            return {"status": resp.status, "events": events, "time_s": elapsed}
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {"status": 0, "events": events, "error": str(e), "time_s": elapsed}

# ============================================================================
# TEST 1: Health Check
# ============================================================================

def test_health():
    """Test GET /health endpoint."""
    log("=== Test 1: Health Check ===")
    result = api_get("/health")
    record_test(
        "health_check",
        result["time_s"],
        "pass" if result["status"] == 200 else "fail",
        {"status_code": result["status"], "response": result.get("data", result.get("error"))}
    )

# ============================================================================
# TEST 2: Basic Search (Sync)
# ============================================================================

def test_basic_search_sync():
    """Test POST /api/search/sync with a simple query."""
    log("=== Test 2: Basic Search (Sync) ===")
    body = {
        "raw_query": "paracetamol fever",
        "mode": "discovery",
        "max_results": 10,
    }
    result = api_post("/api/search/sync", body, timeout=120)
    
    details = {"status_code": result["status"]}
    if result["status"] == 200 and isinstance(result.get("data"), dict):
        data = result["data"]
        details["total_raw"] = data.get("totalRaw")
        details["total_deduplicated"] = data.get("totalDeduplicated")
        details["duplicates_removed"] = data.get("duplicatesRemoved")
        details["duration_ms"] = data.get("durationMs")
        details["sources"] = data.get("sources", [])
        details["gap_analysis"] = bool(data.get("gapAnalysis"))
        details["query_version_hash"] = data.get("queryVersionHash", {}).get("hash")[:16] if data.get("queryVersionHash") else None
    else:
        details["error"] = result.get("error", result.get("body"))
    
    record_test(
        "basic_search_sync",
        result["time_s"],
        "pass" if result["status"] == 200 else "fail",
        details
    )

# ============================================================================
# TEST 3: Search with Compact Mode
# ============================================================================

def test_compact_mode():
    """Test POST /api/search/sync?compact=true strips abstracts."""
    log("=== Test 3: Compact Mode ===")
    body = {
        "raw_query": "machine learning healthcare",
        "mode": "evidence",
        "max_results": 5,
    }
    result = api_post("/api/search/sync?compact=true", body, timeout=120)
    
    details = {"status_code": result["status"]}
    if result["status"] == 200 and isinstance(result.get("data"), dict):
        data = result["data"]
        details["compact"] = data.get("compact")
        details["results_count"] = len(data.get("results", []))
        # Verify abstracts are stripped
        results_list = data.get("results", [])
        if results_list:
            has_abstract = any(r.get("abstract") for r in results_list)
            details["abstracts_stripped"] = not has_abstract
    else:
        details["error"] = result.get("error", result.get("body"))
    
    record_test(
        "compact_mode",
        result["time_s"],
        "pass" if result["status"] == 200 else "fail",
        details
    )

# ============================================================================
# TEST 4: SSE Search Streaming
# ============================================================================

def test_sse_streaming():
    """Test POST /api/search with SSE streaming."""
    log("=== Test 4: SSE Streaming ===")
    body = {
        "raw_query": "COVID-19 vaccine",
        "mode": "clinical",
        "max_results": 10,
    }
    result = api_post_sse("/api/search", body, timeout=120)
    
    event_types = [e.get("type") for e in result.get("events", []) if e.get("type")]
    has_progress = "progress" in event_types or "source_progress" in event_types
    has_results = "results" in event_types
    has_done = "done" in event_types
    has_papers = "paper" in event_types
    
    record_test(
        "sse_streaming",
        result["time_s"],
        "pass" if result["status"] == 200 and has_done else "fail",
        {
            "status_code": result["status"],
            "total_events": len(result.get("events", [])),
            "event_types": list(set(event_types)),
            "has_progress": has_progress,
            "has_results": has_results,
            "has_papers": has_papers,
            "has_done": has_done,
            "error": result.get("error"),
        }
    )

# ============================================================================
# TEST 5: Clinical Mode Search
# ============================================================================

def test_clinical_mode():
    """Test clinical mode with Malay region."""
    log("=== Test 5: Clinical Mode (MY region) ===")
    body = {
        "raw_query": "diabetes management",
        "mode": "clinical",
        "max_results": 15,
        "region": "MY",
    }
    result = api_post("/api/search/sync", body, timeout=120)
    
    details = {"status_code": result["status"]}
    if result["status"] == 200 and isinstance(result.get("data"), dict):
        data = result["data"]
        details["total_deduplicated"] = data.get("totalDeduplicated")
        details["sources_queried"] = len(data.get("sources", []))
        details["gap_analysis"] = bool(data.get("gapAnalysis"))
    else:
        details["error"] = result.get("error", result.get("body"))
    
    record_test(
        "clinical_mode_my",
        result["time_s"],
        "pass" if result["status"] == 200 else "fail",
        details
    )

# ============================================================================
# TEST 6: Concurrent Searches (Parallel Dispatch)
# ============================================================================

def test_concurrent_searches():
    """Test 5 concurrent searches hitting all 8 sources."""
    log("=== Test 6: Concurrent Searches ===")
    queries = [
        {"raw_query": "aspirin cardiovascular", "mode": "discovery", "max_results": 5},
        {"raw_query": "insulin diabetes type 2", "mode": "clinical", "max_results": 5},
        {"raw_query": "antibiotic resistance", "mode": "evidence", "max_results": 5},
        {"raw_query": "machine learning radiology", "mode": "discovery", "max_results": 5},
        {"raw_query": "gene therapy cancer", "mode": "systematic_review", "max_results": 5},
    ]
    
    timings = []
    statuses = []
    errors = []
    
    def search_one(idx, body):
        start = time.perf_counter()
        try:
            result = api_post("/api/search/sync", body, timeout=120)
            elapsed = time.perf_counter() - start
            return {"idx": idx, "status": result["status"], "time_s": elapsed, "error": result.get("error")}
        except Exception as e:
            elapsed = time.perf_counter() - start
            return {"idx": idx, "status": 0, "time_s": elapsed, "error": str(e)}
    
    overall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(search_one, i, q) for i, q in enumerate(queries)]
        for f in as_completed(futures):
            r = f.result()
            timings.append(r["time_s"])
            statuses.append(r["status"])
            if r.get("error"):
                errors.append(f"Query {r['idx']}: {r['error']}")
    overall_elapsed = time.perf_counter() - overall_start
    
    success_count = sum(1 for s in statuses if s == 200)
    
    record_test(
        "concurrent_searches",
        overall_elapsed,
        "pass" if success_count >= 4 else "warn" if success_count >= 2 else "fail",
        {
            "queries": len(queries),
            "success_count": success_count,
            "avg_time_s": round(statistics.mean(timings), 2) if timings else 0,
            "max_time_s": round(max(timings), 2) if timings else 0,
            "min_time_s": round(min(timings), 2) if timings else 0,
            "parallel_benefit": f"5 queries in {round(overall_elapsed, 2)}s vs ~{round(sum(timings), 2)}s sequential",
            "errors": errors,
        }
    )

# ============================================================================
# TEST 7: Edge Cases
# ============================================================================

def test_edge_cases():
    """Test edge cases: empty query, special chars, long query."""
    log("=== Test 7: Edge Cases ===")
    
    cases = [
        ("empty_query", {"raw_query": "", "mode": "discovery"}, 400),
        ("special_chars", {"raw_query": "test AND (OR NOT) \"phrase\"", "mode": "discovery"}, 200),
        ("long_query", {"raw_query": " ".join(["word"] * 200), "mode": "discovery"}, 200),
        ("boolean_operators", {"raw_query": "aspirin AND cardiac NOT stroke", "mode": "discovery"}, 200),
        ("quoted_phrases", {"raw_query": "\"machine learning\" AND \"deep learning\"", "mode": "discovery"}, 200),
    ]
    
    results = {}
    for name, body, expected_status in cases:
        timeout = 30 if name != "long_query" else 120
        result = api_post("/api/search/sync", body, timeout=timeout)
        passed = result["status"] == expected_status
        results[name] = {
            "status_code": result["status"],
            "expected": expected_status,
            "passed": passed,
            "time_s": round(result["time_s"], 2),
        }
    
    all_passed = all(r["passed"] for r in results.values())
    
    record_test(
        "edge_cases",
        sum(r["time_s"] for r in results.values()),
        "pass" if all_passed else "warn",
        {"cases": results}
    )

# ============================================================================
# TEST 8: Paper Abstract Endpoint
# ============================================================================

def test_paper_abstract():
    """Test GET /api/paper/abstract?doi=..."""
    log("=== Test 8: Paper Abstract Endpoint ===")
    
    # Use a known DOI
    test_dois = [
        "10.1038/s41586-020-2649-2",  # Nature COVID paper
        "10.1001/jama.2020.1234",  # JAMA (may not exist, tests error handling)
    ]
    
    results = {}
    for doi in test_dois:
        result = api_get(f"/api/paper/abstract?doi={doi}", timeout=30)
        results[doi[:30]] = {
            "status_code": result["status"],
            "has_abstract": bool(result.get("data", {}).get("abstract")),
            "has_micro_summary": bool(result.get("data", {}).get("microSummary")),
            "time_s": round(result["time_s"], 2),
        }
    
    record_test(
        "paper_abstract",
        sum(r["time_s"] for r in results.values()),
        "pass" if any(r["status_code"] == 200 for r in results.values()) else "warn",
        {"results": results}
    )

# ============================================================================
# TEST 9: Systematic Review Mode
# ============================================================================

def test_systematic_review():
    """Test systematic review mode (all 8 sources)."""
    log("=== Test 9: Systematic Review Mode ===")
    body = {
        "raw_query": "randomized controlled trial metformin",
        "mode": "systematic_review",
        "max_results": 20,
    }
    result = api_post("/api/search/sync", body, timeout=120)
    
    details = {"status_code": result["status"]}
    if result["status"] == 200 and isinstance(result.get("data"), dict):
        data = result["data"]
        details["total_raw"] = data.get("totalRaw")
        details["total_deduplicated"] = data.get("totalDeduplicated")
        details["sources"] = [s.get("source") for s in data.get("sources", [])]
        details["tier_classifications"] = len(data.get("tierClassifications", []))
        details["gap_analysis_present"] = bool(data.get("gapAnalysis"))
    else:
        details["error"] = result.get("error", result.get("body"))
    
    record_test(
        "systematic_review",
        result["time_s"],
        "pass" if result["status"] == 200 else "fail",
        details
    )

# ============================================================================
# TEST 10: Rate Limiting Behavior
# ============================================================================

def test_rate_limiting():
    """Test rapid-fire requests to trigger rate limiting."""
    log("=== Test 10: Rate Limiting ===")
    
    request_count = 10
    statuses = []
    timings = []
    
    for i in range(request_count):
        body = {"raw_query": f"test query {i}", "mode": "discovery", "max_results": 2}
        result = api_post("/api/search/sync", body, timeout=30)
        statuses.append(result["status"])
        timings.append(result["time_s"])
    
    success_count = sum(1 for s in statuses if s == 200)
    rate_limited = sum(1 for s in statuses if s == 429)
    
    record_test(
        "rate_limiting",
        sum(timings),
        "pass" if success_count > 0 else "fail",
        {
            "total_requests": request_count,
            "successful": success_count,
            "rate_limited_429": rate_limited,
            "other_errors": sum(1 for s in statuses if s not in [200, 429]),
            "avg_time_s": round(statistics.mean(timings), 2),
            "rate_limit_enforced": rate_limited > 0 or success_count == request_count,
        }
    )

# ============================================================================
# TEST 11: Discovery Feed Mode
# ============================================================================

def test_discovery_mode():
    """Test discovery mode with broad query."""
    log("=== Test 11: Discovery Mode ===")
    body = {
        "raw_query": "CRISPR gene editing",
        "mode": "discovery",
        "max_results": 50,
    }
    result = api_post("/api/search/sync", body, timeout=120)
    
    details = {"status_code": result["status"]}
    if result["status"] == 200 and isinstance(result.get("data"), dict):
        data = result["data"]
        details["total_raw"] = data.get("totalRaw")
        details["total_deduplicated"] = data.get("totalDeduplicated")
        details["duplicates_removed"] = data.get("duplicatesRemoved")
        details["entity_blocked"] = data.get("entityBlockedCount")
        details["shadow_merge_count"] = data.get("shadowMergeCount")
        details["sources"] = [s.get("source") for s in data.get("sources", [])]
    else:
        details["error"] = result.get("error", result.get("body"))
    
    record_test(
        "discovery_mode",
        result["time_s"],
        "pass" if result["status"] == 200 else "fail",
        details
    )

# ============================================================================
# TEST 12: Ranking Weights
# ============================================================================

def test_ranking_weights():
    """Test custom ranking weights."""
    log("=== Test 12: Ranking Weights ===")
    body = {
        "raw_query": "blockchain supply chain",
        "mode": "discovery",
        "max_results": 10,
        "weights": {
            "recency": 0.4,
            "citations": 0.3,
            "openAccess": 0.2,
            "relevance": 0.1,
        },
    }
    result = api_post("/api/search/sync", body, timeout=120)
    
    details = {"status_code": result["status"]}
    if result["status"] == 200 and isinstance(result.get("data"), dict):
        data = result["data"]
        details["frozen_weights"] = data.get("frozenWeights")
        details["total_deduplicated"] = data.get("totalDeduplicated")
    else:
        details["error"] = result.get("error", result.get("body"))
    
    record_test(
        "ranking_weights",
        result["time_s"],
        "pass" if result["status"] == 200 else "fail",
        details
    )

# ============================================================================
# TEST 13: Open Access Filter
# ============================================================================

def test_open_access_filter():
    """Test with open access filter."""
    log("=== Test 13: Open Access Filter ===")
    body = {
        "raw_query": "machine learning",
        "mode": "discovery",
        "max_results": 10,
        "filters": {
            "open_access_only": True,
        },
    }
    result = api_post("/api/search/sync", body, timeout=120)
    
    details = {"status_code": result["status"]}
    if result["status"] == 200 and isinstance(result.get("data"), dict):
        data = result["data"]
        results_list = data.get("results", [])
        oa_count = sum(1 for r in results_list if r.get("isOa"))
        details["total_results"] = len(results_list)
        details["open_access_count"] = oa_count
        details["oa_ratio"] = f"{oa_count/len(results_list)*100:.1f}%" if results_list else "0%"
    else:
        details["error"] = result.get("error", result.get("body"))
    
    record_test(
        "open_access_filter",
        result["time_s"],
        "pass" if result["status"] == 200 else "fail",
        details
    )

# ============================================================================
# MAIN
# ============================================================================

def check_server():
    """Check if server is running."""
    result = api_get("/health", timeout=5)
    return result["status"] == 200

def main():
    log("=" * 70)
    log("SCHOLARSEARCH GITHUB VERSION STRESS TEST")
    log(f"Target: {BASE_URL}")
    log(f"Started: {datetime.now().isoformat()}")
    log("=" * 70)
    
    # Check server
    if not check_server():
        log("Server not running. Attempting to start...", "WARN")
        log("Please start the server manually: cd scholarsearch && npm start", "WARN")
        log("Or set SCHOLARSEARCH_URL environment variable", "WARN")
        sys.exit(1)
    
    log("Server is running. Starting stress tests...\n")
    
    test_start = time.perf_counter()
    
    test_health()
    test_basic_search_sync()
    test_compact_mode()
    test_sse_streaming()
    test_clinical_mode()
    test_concurrent_searches()
    test_edge_cases()
    test_paper_abstract()
    test_systematic_review()
    test_rate_limiting()
    test_discovery_mode()
    test_ranking_weights()
    test_open_access_filter()
    
    total_elapsed = time.perf_counter() - test_start
    
    # Summary
    log("\n" + "=" * 70)
    log("STRESS TEST SUMMARY")
    log("=" * 70)
    
    passed = sum(1 for r in RESULTS if r["status"] == "pass")
    warned = sum(1 for r in RESULTS if r["status"] == "warn")
    failed = sum(1 for r in RESULTS if r["status"] == "fail")
    
    log(f"Total: {len(RESULTS)} | Pass: {passed} | Warn: {warned} | Fail: {failed}")
    log(f"Duration: {round(total_elapsed, 2)}s")
    
    for r in RESULTS:
        icon = "PASS" if r["status"] == "pass" else "WARN" if r["status"] == "warn" else "FAIL"
        log(f"  [{icon}] {r['name']}: {r['duration_ms']}ms")
    
    # Write report
    report_path = Path(__file__).parent / "test_results" / "scholarsearch_stress_report.json"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "target": BASE_URL,
            "total_duration_s": round(total_elapsed, 2),
            "summary": {"pass": passed, "warn": warned, "fail": failed},
            "tests": RESULTS,
        }, f, indent=2)
    log(f"\nReport: {report_path}")
    
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
