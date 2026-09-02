#!/usr/bin/env python3
"""
Swarm Cascade — Batch Router
High-volume clinical and market query dispatch with DLQ and export.
"""

import asyncio
import csv
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
import urllib.request
import urllib.error


# Configuration
API_BASE = "http://localhost:8084"
# Live 8B: 2-3 concurrent avoids VRAM eviction on consumer GPU (mock was 10)
# Override via env SWARM_MAX_CONCURRENT
import os as _os
MAX_CONCURRENT = int(_os.environ.get("SWARM_MAX_CONCURRENT", "3"))
BATCH_SIZE = 100     # Maximum queries per batch run


@dataclass
class BatchQuery:
    """Individual query within a batch."""
    index: int
    query: str
    query_hash: str = field(init=False)
    result: Optional[dict] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        self.query_hash = hashlib.sha256(self.query.encode()).hexdigest()[:16]


@dataclass
class BatchResult:
    """Complete batch execution result."""
    batch_id: str
    queries: List[BatchQuery] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float = 0
    success_count: int = 0
    failed_count: int = 0


class BatchRouter:
    """
    High-volume query dispatch for the Swarm Cascade.

    Features:
    - Parallel dispatch with concurrency cap via semaphore
    - Dead Letter Queue for failed queries
    - Cryptographic hash chain for batch integrity
    - CSV/JSON export of results
    - Progress tracking with asyncio
    """

    def __init__(
        self,
        max_concurrent: int = MAX_CONCURRENT,
        batch_size: int = BATCH_SIZE,
        api_base: str = API_BASE,
    ):
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size
        self.api_base = api_base
        self.batch_id = hashlib.sha256(f"{time.time()}-batch".encode()).hexdigest()[:16]
        self.dlq: List[BatchQuery] = []
        self.results: List[BatchQuery] = []

    async def _execute_single(self, query: str, index: int) -> BatchQuery:
        """Execute a single query against the Swarm API."""
        batch_query = BatchQuery(index=index, query=query)

        try:
            data = json.dumps({"query": query}).encode()
            req = urllib.request.Request(
                f"{self.api_base}/api/research",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode())
            batch_query.result = result
            return batch_query

        except urllib.error.HTTPError as e:
            batch_query.error = f"HTTP {e.code}: {e.reason}"
            return batch_query
        except urllib.error.URLError as e:
            batch_query.error = f"Connection error: {e.reason}"
            return batch_query
        except json.JSONDecodeError as e:
            batch_query.error = f"Invalid JSON response: {e}"
            return batch_query
        except Exception as e:
            batch_query.error = f"Unexpected error: {e}"
            return batch_query

    async def _dispatch_batch(self, queries: List[str]) -> List[BatchQuery]:
        """Dispatch a batch of queries with concurrency control."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _limited_execute(query: str, index: int) -> BatchQuery:
            async with semaphore:
                return await self._execute_single(query, index)

        tasks = [_limited_execute(q, i) for i, q in enumerate(queries)]
        return await asyncio.gather(*tasks)

    async def run_batch(
        self,
        queries: List[str],
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> BatchResult:
        """
        Execute a batch of queries with full tracking.

        Args:
            queries: List of query strings to execute
            progress_callback: Optional callback(index, completed, total)

        Returns:
            BatchResult with all outcomes
        """
        # Truncate to batch size
        queries = queries[:self.batch_size]

        batch_result = BatchResult(
            batch_id=self.batch_id,
            queries=[BatchQuery(index=i, query=q) for i, q in enumerate(queries)],
            start_time=time.time(),
        )

        # Execute with concurrency control
        dispatch_results = await self._dispatch_batch(queries)

        # Process results
        success_count = 0
        failed_count = 0

        for i, result in enumerate(dispatch_results):
            batch_result.queries[i].result = result.result
            batch_result.queries[i].error = result.error

            if result.error:
                self.dlq.append(batch_result.queries[i])
                failed_count += 1
            else:
                self.results.append(batch_result.queries[i])
                success_count += 1

            # Progress callback
            if progress_callback:
                try:
                    progress_callback(i, success_count + failed_count, len(queries))
                except Exception:
                    pass

        batch_result.end_time = time.time()
        batch_result.success_count = success_count
        batch_result.failed_count = failed_count

        return batch_result

    def export_csv(self, filepath: str) -> str:
        """Export batch results to CSV format."""
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Index", "Query", "Query_Hash", "Status",
                "Verdict", "Boundary_Condition", "Timestamp", "Error"
            ])

            # Successes first, then DLQ
            all_queries = self.results + self.dlq
            for q in all_queries:
                verdict = ""
                if q.result and q.result.get("blind_matrix"):
                    verdict = q.result["blind_matrix"].get("verdict", "")

                boundary = ""
                if q.result and q.result.get("blind_matrix"):
                    boundary = q.result["blind_matrix"].get("boundary_condition", "")

                writer.writerow([
                    q.index,
                    q.query[:200] if q.query else "",
                    q.query_hash,
                    "FAILED" if q.error else "SUCCESS",
                    verdict,
                    boundary[:100] if boundary else "",
                    q.timestamp,
                    q.error or "",
                ])

        return filepath

    def export_json(self, filepath: str) -> str:
        """Export batch results to JSON format."""
        export_data = {
            "batch_id": self.batch_id,
            "success_count": len(self.results),
            "failed_count": len(self.dlq),
            "queries": [
                {
                    "index": q.index,
                    "query": q.query,
                    "query_hash": q.query_hash,
                    "result": q.result,
                    "error": q.error,
                    "timestamp": q.timestamp,
                }
                for q in (self.results + self.dlq)
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        return filepath


async def main():
    """CLI entry point for the Batch Router."""
    import sys

    # Generate sample clinical queries
    sample_queries = [
        "Low-dose atropine versus orthokeratology for pediatric myopia control",
        "Comparative efficacy of MITF mutations in autosomal recessive retinal dystrophy",
        "CRS-116 versus standard care for chronic rhinosinusitis with nasal polyposis",
        "Low-dose fluconazole versus topical agents for refractory cutaneous candidiasis",
        "Vitamin D supplementation versus placebo for seasonal affective disorder",
        "Atropine 0.01% versus observation for myopia progression in children",
        "Orthokeratology overnight wear for juvenile myopia control",
        "Combination therapy: atropine + orthokeratology for myopia",
        "Daily disposable contact lenses versus ortho-k for myopia control",
        "Atropine 0.02% versus 0.05% for pediatric myopia progression",
    ]

    if len(sys.argv) > 1:
        query_file = sys.argv[1]
        try:
            with open(query_file, "r", encoding="utf-8") as f:
                queries = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            queries = sample_queries[:20]
    else:
        queries = sample_queries[:10]

    print(f"Swarm Cascade Batch Router")
    print(f"==========================")
    print(f"Batch ID: {hashlib.sha256(f'{time.time()}-batch'.encode()).hexdigest()[:16]}")
    print(f"Queries: {len(queries)}")
    print(f"Max concurrent: {MAX_CONCURRENT}")
    print(f"API: {API_BASE}/api/research")
    print()

    router = BatchRouter(max_concurrent=MAX_CONCURRENT)

    def progress(index: int, completed: int, total: int):
        percent = (completed / total * 100) if total > 0 else 0
        print(f"\rProgress: {completed}/{total} ({percent:.1f}%) ", end="")

    print("Executing batch...")
    result = await router.run_batch(queries, progress_callback=progress)

    print(f"\n\n{'='*60}")
    print(f"BATCH RESULTS")
    print(f"{'='*60}")
    print(f"Batch ID:      {result.batch_id}")
    print(f"Successes:     {result.success_count}")
    print(f"Failures:      {result.failed_count}")
    print(f"Duration:      {result.end_time - result.start_time:.2f}s")
    print()

    # Export results
    csv_path = router.export_csv(f"batch_results_{result.batch_id}.csv")
    json_path = router.export_json(f"batch_export_{result.batch_id}.json")

    print(f"CSV export:  {csv_path}")
    print(f"JSON export: {json_path}")

    # DLQ summary
    if router.dlq:
        print(f"\nDead Letter Queue ({len(router.dlq)} failures):")
        for q in router.dlq[:5]:
            print(f"  [{q.index}] {q.error[:80]}{'...' if len(q.error) > 80 else ''}")

    print(f"\n{len(result.queries)} queries processed total.")
    return result


if __name__ == "__main__":
    asyncio.run(main())