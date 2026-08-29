#!/usr/bin/env python3
"""
Concurrency Stress Test for PDF-to-PPTX Conversion Pipeline

Fires simultaneous conversion requests with fresh MCPSessions,
monitors memory, detects deadlocks, and generates an HTML report.
"""

import asyncio
import json
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from pdf_to_pptx import MCPSession
from run_curriculum import run_single_test

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

TOTAL_REQUESTS = 20
DEFAULT_CONCURRENCY = 5
REQUEST_TIMEOUT = 60

TARGET_PDFS = [
    "26_large_10pages.pdf",
    "27_large_25pages.pdf",
    "28_large_50pages.pdf",
    "29_large_table_heavy.pdf",
    "30_large_chapter_book.pdf",
    "messy_test.pdf",
    "08_two_columns_multipage.pdf",
]


@dataclass
class RequestResult:
    request_id: int
    pdf_name: str
    status: str  # "success", "fail", "timeout"
    wall_time: float = 0.0
    peak_memory_mb: float = 0.0
    start_offset: float = 0.0
    end_offset: float = 0.0
    error: str = ""
    slides: int = 0
    pages: int = 0


class MemoryMonitor:
    def __init__(self):
        self._tracking = PSUTIL_AVAILABLE
        self._peak = 0.0
        self._samples: List[float] = []
        self._process = psutil.Process() if PSUTIL_AVAILABLE else None

    def sample(self) -> float:
        if not self._tracking:
            return 0.0
        mb = self._process.memory_info().rss / (1024 * 1024)
        self._samples.append(mb)
        if mb > self._peak:
            self._peak = mb
        return mb

    @property
    def peak_mb(self) -> float:
        return self._peak

    @property
    def samples(self) -> List[float]:
        return self._samples


async def run_request(
    request_id: int,
    pdf_path: Path,
    output_dir: Path,
    semaphore: asyncio.Semaphore,
    global_start: float,
    memory_monitor: MemoryMonitor,
) -> RequestResult:
    async with semaphore:
        req_start = time.time()
        result = RequestResult(
            request_id=request_id,
            pdf_name=pdf_path.stem,
            status="fail",
            start_offset=req_start - global_start,
        )

        session = None
        try:
            memory_monitor.sample()
            from orchestrator_v2 import convert_pdf
            memory_monitor.sample()

            orch_result = await asyncio.wait_for(
                convert_pdf(str(pdf_path), output_dir, mcp_augment=True),
                timeout=REQUEST_TIMEOUT,
            )

            memory_monitor.sample()

            if orch_result.success:
                result.status = "success"
                result.slides = orch_result.total_slides
                result.pages = orch_result.total_pages
            else:
                result.status = "fail"
                result.error = "; ".join(orch_result.errors[:3])

        except asyncio.TimeoutError:
            result.status = "timeout"
            result.error = f"Exceeded {REQUEST_TIMEOUT}s deadline"
        except Exception as e:
            result.status = "fail"
            result.error = f"{type(e).__name__}: {str(e)[:150]}"

        result.wall_time = time.time() - req_start
        result.end_offset = time.time() - global_start
        result.peak_memory_mb = memory_monitor.peak_mb
        return result


def build_target_list(curriculum_dir: Path) -> List[Path]:
    targets = []
    for name in TARGET_PDFS:
        path = curriculum_dir / name
        if name == "messy_test.pdf":
            path = Path("messy_test.pdf").resolve()
        if path.exists():
            targets.append(path)
        else:
            print(f"  Warning: {path} not found, skipping")
    return targets


def generate_html_report(
    results: List[RequestResult],
    output_path: Path,
    wall_clock: float,
    cpu_time: float,
    memory_monitor: MemoryMonitor,
    concurrency: int,
):
    total = len(results)
    passed = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "fail")
    timeouts = sum(1 for r in results if r.status == "timeout")
    throughput = passed / max(0.001, wall_clock)
    avg_time = sum(r.wall_time for r in results) / max(1, total)
    max_time = max((r.wall_time for r in results), default=0)
    min_time = min((r.wall_time for r in results), default=0)

    sorted_by_start = sorted(results, key=lambda r: r.start_offset)
    total_span = max((r.end_offset for r in results), default=1)
    if total_span == 0:
        total_span = 1

    gantt_rows = ""
    for r in sorted_by_start:
        left_pct = (r.start_offset / total_span) * 100
        width_pct = max(0.3, (r.wall_time / total_span) * 100)
        if r.status == "success":
            color = "#3fb950"
        elif r.status == "timeout":
            color = "#d29922"
        else:
            color = "#da3633"
        gantt_rows += f"""
        <div class="gantt-row">
          <div class="gantt-label">#{r.request_id} {r.pdf_name}</div>
          <div class="gantt-track">
            <div class="gantt-bar" style="left:{left_pct:.1f}%;width:{width_pct:.1f}%;background:{color}" title="{r.status}: {r.wall_time:.1f}s"></div>
          </div>
          <div class="gantt-time">{r.wall_time:.1f}s</div>
        </div>"""

    memory_chart = ""
    if memory_monitor._tracking and memory_monitor.samples:
        samples = memory_monitor.samples
        max_mem = max(samples) if samples else 1
        if max_mem == 0:
            max_mem = 1
        points = []
        step = max(1, len(samples) // 200)
        for i in range(0, len(samples), step):
            x = (i / max(1, len(samples) - 1)) * 100
            y = 100 - (samples[i] / max_mem) * 100
            points.append(f"{x:.1f},{y:.1f}")
        peak_val = memory_monitor.peak_mb
        memory_chart = f"""
        <div class="memory-chart">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#58a6ff" stop-opacity="0.4"/>
                <stop offset="100%" stop-color="#58a6ff" stop-opacity="0.05"/>
              </linearGradient>
            </defs>
            <polygon points="0,100 {' '.join(points)} 100,100" fill="url(#memGrad)"/>
            <polyline points="{' '.join(points)}" fill="none" stroke="#58a6ff" stroke-width="0.5"/>
            <line x1="0" y1="0" x2="100" y2="0" stroke="#30363d" stroke-width="0.1"/>
          </svg>
          <div class="memory-label">Peak: {peak_val:.1f} MB | Samples: {len(samples)}</div>
        </div>"""

    error_rows = ""
    for r in results:
        if r.status != "success":
            err_class = "timeout" if r.status == "timeout" else "error"
            error_rows += f"""
        <div class="error-item">
          <div class="error-req">#{r.request_id} {r.pdf_name}</div>
          <div class="error-badge {err_class}">{r.status.upper()}</div>
          <div class="error-msg">{r.error}</div>
        </div>"""

    error_section = ""
    if error_rows:
        error_section = f"""
    <h3>Error Analysis</h3>
    <div class="error-list">{error_rows}</div>"""

    memory_section = ""
    if memory_monitor._tracking:
        memory_section = f"""
    <h3>Memory Usage</h3>
    {memory_chart}"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stress Test Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; padding: 24px; }}
h1 {{ color: #58a6ff; font-size: 28px; margin-bottom: 8px; }}
h2 {{ color: #8b949e; font-size: 18px; margin-bottom: 16px; font-weight: 400; }}
h3 {{ color: #58a6ff; font-size: 16px; margin: 24px 0 12px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }}
.stat {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }}
.stat-value {{ font-size: 32px; font-weight: 700; color: #58a6ff; }}
.stat-label {{ color: #8b949e; font-size: 13px; margin-top: 4px; }}
.stat-pass {{ color: #3fb950; }}
.stat-fail {{ color: #f85149; }}
.stat-warn {{ color: #d29922; }}
.stat-info {{ color: #a371f7; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
th {{ background: #161b22; color: #8b949e; text-align: left; padding: 10px 12px; font-size: 12px; text-transform: uppercase; border-bottom: 2px solid #30363d; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; font-size: 13px; }}
tr:hover {{ background: #161b22; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
.badge-pass {{ background: #238636; color: #fff; }}
.badge-fail {{ background: #da3633; color: #fff; }}
.badge-timeout {{ background: #9e6a03; color: #fff; }}

.gantt-section {{ margin-bottom: 32px; }}
.gantt-row {{ display: flex; align-items: center; margin-bottom: 3px; height: 22px; }}
.gantt-label {{ width: 220px; min-width: 220px; font-size: 11px; color: #8b949e; text-align: right; padding-right: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.gantt-track {{ flex: 1; position: relative; height: 16px; background: #161b22; border-radius: 3px; }}
.gantt-bar {{ position: absolute; top: 1px; height: 14px; border-radius: 2px; min-width: 3px; transition: opacity 0.2s; }}
.gantt-bar:hover {{ opacity: 0.8; filter: brightness(1.3); }}
.gantt-time {{ width: 60px; min-width: 60px; font-size: 11px; color: #8b949e; text-align: right; padding-left: 8px; }}
.gantt-legend {{ display: flex; gap: 16px; margin-bottom: 16px; font-size: 12px; }}
.gantt-legend-item {{ display: flex; align-items: center; gap: 4px; }}
.gantt-legend-dot {{ width: 10px; height: 10px; border-radius: 2px; }}

.memory-chart {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
.memory-chart svg {{ width: 100%; height: 150px; }}
.memory-label {{ font-size: 12px; color: #8b949e; margin-top: 8px; }}

.error-list {{ display: flex; flex-direction: column; gap: 8px; }}
.error-item {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; display: flex; align-items: flex-start; gap: 12px; }}
.error-req {{ font-weight: 600; min-width: 180px; color: #c9d1d9; }}
.error-badge {{ padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; min-width: 60px; text-align: center; }}
.error-badge.error {{ background: #da3633; color: #fff; }}
.error-badge.timeout {{ background: #9e6a03; color: #fff; }}
.error-msg {{ font-size: 12px; color: #f85149; flex: 1; word-break: break-word; }}
</style>
</head>
<body>
<h1>Concurrency Stress Test Report</h1>
<h2>Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {total} requests | {DEFAULT_CONCURRENCY} max concurrent</h2>

<div class="summary">
  <div class="stat"><div class="stat-value">{total}</div><div class="stat-label">Total Requests</div></div>
  <div class="stat"><div class="stat-value stat-pass">{passed}</div><div class="stat-label">Passed</div></div>
  <div class="stat"><div class="stat-value stat-fail">{failed}</div><div class="stat-label">Failed</div></div>
  <div class="stat"><div class="stat-value stat-warn">{timeouts}</div><div class="stat-label">Timeouts</div></div>
  <div class="stat"><div class="stat-value stat-info">{throughput:.2f}</div><div class="stat-label">Throughput (conv/s)</div></div>
  <div class="stat"><div class="stat-value">{wall_clock:.1f}s</div><div class="stat-label">Wall Clock</div></div>
  <div class="stat"><div class="stat-value">{cpu_time:.1f}s</div><div class="stat-label">Total CPU Time</div></div>
  <div class="stat"><div class="stat-value">{avg_time:.1f}s</div><div class="stat-label">Avg Request Time</div></div>
</div>

<h3>Request Timeline</h3>
<div class="gantt-legend">
  <div class="gantt-legend-item"><div class="gantt-legend-dot" style="background:#3fb950"></div> Success</div>
  <div class="gantt-legend-item"><div class="gantt-legend-dot" style="background:#da3633"></div> Failed</div>
  <div class="gantt-legend-item"><div class="gantt-legend-dot" style="background:#d29922"></div> Timeout</div>
</div>
<div class="gantt-section">{gantt_rows}</div>

<h3>Per-Request Details</h3>
<table>
<tr><th>#</th><th>PDF</th><th>Status</th><th>Time</th><th>Pages</th><th>Slides</th><th>Error</th></tr>
"""
    for r in sorted(results, key=lambda x: x.request_id):
        badge_cls = f"badge-{r.status}" if r.status in ("success", "fail") else "badge-timeout"
        badge_label = r.status.upper() if r.status != "success" else "PASS"
        html += f"""<tr>
  <td>{r.request_id}</td>
  <td><strong>{r.pdf_name}</strong></td>
  <td><span class="badge {badge_cls}">{badge_label}</span></td>
  <td>{r.wall_time:.1f}s</td>
  <td>{r.pages if r.pages else '-'}</td>
  <td>{r.slides if r.slides else '-'}</td>
  <td style="color:#f85149;font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{r.error if r.error else ''}</td>
</tr>\n"""

    html += "</table>\n"

    html += error_section
    html += memory_section

    html += """
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


async def main():
    print("=" * 60)
    print("CONCURRENCY STRESS TEST")
    print("=" * 60)
    print(f"Requests: {TOTAL_REQUESTS} | Concurrency: {DEFAULT_CONCURRENCY} | Timeout: {REQUEST_TIMEOUT}s")
    print(f"psutil available: {PSUTIL_AVAILABLE}")
    print()

    curriculum_dir = Path("curriculum").resolve()
    output_dir = Path("test_results").resolve()
    output_dir.mkdir(exist_ok=True)

    targets = build_target_list(curriculum_dir)
    if not targets:
        print("Error: No target PDFs found.")
        sys.exit(1)

    print(f"Target PDFs ({len(targets)}):")
    for t in targets:
        print(f"  - {t.name}")
    print()

    request_assignments = []
    for i in range(TOTAL_REQUESTS):
        pdf = targets[i % len(targets)]
        request_assignments.append(pdf)

    semaphore = asyncio.Semaphore(DEFAULT_CONCURRENCY)
    memory_monitor = MemoryMonitor()

    print(f"Launching {TOTAL_REQUESTS} requests (max {DEFAULT_CONCURRENCY} concurrent)...")
    print()

    global_start = time.time()

    tasks = [
        run_request(i + 1, pdf, output_dir, semaphore, global_start, memory_monitor)
        for i, pdf in enumerate(request_assignments)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    wall_clock = time.time() - global_start
    cpu_time = sum(r.wall_time for r in results if isinstance(r, RequestResult))

    final_results: List[RequestResult] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            final_results.append(RequestResult(
                request_id=i + 1,
                pdf_name=request_assignments[i].stem,
                status="fail",
                error=f"Task exception: {str(r)[:150]}",
            ))
        else:
            final_results.append(r)

    passed = sum(1 for r in final_results if r.status == "success")
    failed = sum(1 for r in final_results if r.status == "fail")
    timeouts = sum(1 for r in final_results if r.status == "timeout")
    throughput = passed / max(0.001, wall_clock)

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Passed:    {passed}/{TOTAL_REQUESTS}")
    print(f"  Failed:    {failed}/{TOTAL_REQUESTS}")
    print(f"  Timeouts:  {timeouts}/{TOTAL_REQUESTS}")
    print(f"  Wall time: {wall_clock:.1f}s")
    print(f"  CPU time:  {cpu_time:.1f}s")
    print(f"  Throughput: {throughput:.2f} conv/s")
    if PSUTIL_AVAILABLE:
        print(f"  Peak memory: {memory_monitor.peak_mb:.1f} MB")
    print()

    if failed + timeouts > 0:
        print("Failed/Timed out requests:")
        for r in final_results:
            if r.status != "success":
                print(f"  #{r.request_id} {r.pdf_name}: [{r.status}] {r.error}")
        print()

    report_path = output_dir / "stress_report.html"
    generate_html_report(final_results, report_path, wall_clock, cpu_time, memory_monitor, DEFAULT_CONCURRENCY)
    print(f"HTML report: {report_path}")

    json_path = output_dir / "stress_results.json"
    json_path.write_text(
        json.dumps([asdict(r) for r in final_results], indent=2, default=str),
        encoding="utf-8",
    )
    print(f"JSON results: {json_path}")

    if failed + timeouts > 0:
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
