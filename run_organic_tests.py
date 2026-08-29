#!/usr/bin/env python3
"""
Organic Test Runner — Hostile PDF Gauntlet

Processes 10 real-world hostile PDFs through the PDF-to-PPTX conversion
pipeline and generates an HTML diagnostic report.

Key differences from curriculum runner:
- These are REAL-WORLD PDFs, so failures and fallbacks are EXPECTED
- A "pass" means the pipeline didn't crash AND the output PPTX was written
- A "fail" is GOOD telemetry — it tells us what real-world PDFs break
- Tracks table fallbacks (Binary Antagonist working correctly)
- Tracks clustering anomalies

Usage: python run_organic_tests.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

from pdf_to_pptx import MCPSession, PT_TO_EMU, pdf_to_pptx_y
from run_curriculum import (
    run_single_test,
    generate_html_report,
    TestResult,
    WorkerPool,
    NUM_WORKERS,
    TIMEOUT_PER_PDF,
)


def generate_organic_report(results: list, output_path: Path, hostile_dir: Path):
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    total_fallbacks = sum(len(r.table_fallbacks) for r in results)
    avg_time = sum(r.total_time_ms for r in results) / max(1, total)

    failed_results = [r for r in results if not r.success]
    passed_results = [r for r in results if r.success]
    fallback_results = [r for r in results if r.table_fallbacks]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Organic Hostile PDF Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; padding: 24px; }}
h1 {{ color: #58a6ff; font-size: 28px; margin-bottom: 8px; }}
h2 {{ color: #8b949e; font-size: 18px; margin-bottom: 16px; font-weight: 400; }}
h3 {{ color: #58a6ff; font-size: 16px; margin: 24px 0 12px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 32px; }}
.stat {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }}
.stat-value {{ font-size: 32px; font-weight: 700; color: #58a6ff; }}
.stat-label {{ color: #8b949e; font-size: 13px; margin-top: 4px; }}
.stat-pass {{ color: #3fb950; }} .stat-fail {{ color: #f85149; }} .stat-warn {{ color: #d29922; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
th {{ background: #161b22; color: #8b949e; text-align: left; padding: 10px 12px; font-size: 12px; text-transform: uppercase; border-bottom: 2px solid #30363d; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; font-size: 13px; }}
tr:hover {{ background: #161b22; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
.badge-pass {{ background: #238636; color: #fff; }}
.badge-fail {{ background: #da3633; color: #fff; }}
.badge-warn {{ background: #9e6a03; color: #fff; }}
.badge-info {{ background: #1f6feb; color: #fff; }}
.detail {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
.fallback-list {{ margin-top: 8px; }}
.fallback-item {{ background: #9e6a0322; border-left: 3px solid #d29922; padding: 4px 8px; margin: 4px 0; border-radius: 0 4px 4px 0; font-size: 12px; }}
.error-item {{ background: #da363322; border-left: 3px solid #da3633; padding: 4px 8px; margin: 4px 0; border-radius: 0 4px 4px 0; font-size: 12px; color: #f85149; }}
.note {{ background: #0d419d22; border: 1px solid #1f6feb; border-radius: 8px; padding: 16px; margin-bottom: 24px; font-size: 13px; line-height: 1.6; }}
.note strong {{ color: #58a6ff; }}
.error-type {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 6px; }}
.error-type-runtime {{ background: #da363344; color: #f85149; }}
.error-type-timeout {{ background: #9e6a0344; color: #d29922; }}
.error-type-value {{ background: #3fb95044; color: #3fb950; }}
.error-type-os {{ background: #6e40c9aa; color: #d2a8ff; }}
.error-type-unknown {{ background: #8b949e44; color: #8b949e; }}
</style>
</head>
<body>
<h1>Organic Hostile PDF Report</h1>
<h2>Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {total} hostile PDFs | {NUM_WORKERS} worker(s)</h2>

<div class="note">
  <strong>Why organic failures are EXPECTED and HEALTHY telemetry:</strong><br>
  These are real-world PDFs — arXiv papers, IRS tax forms, patents, bank statements, USGS maps, and more.
  They contain encryption, complex layouts, embedded fonts, scanned images, XFA forms, and other
  adversarial structures. A pipeline that passes 100% of hostile PDFs on the first pass is either
  over-fitting to edge cases or not being honest about its limitations. Failures here tell us
  exactly where the MCP extraction layer or the rendering pipeline needs hardening. Fallbacks
  mean the Binary Antagonist correctly rejected hallucinated tables — that's the system working
  as designed.
</div>

<div class="summary">
  <div class="stat"><div class="stat-value">{total}</div><div class="stat-label">Total Organic PDFs</div></div>
  <div class="stat"><div class="stat-value stat-pass">{passed}</div><div class="stat-label">Passed (no crash)</div></div>
  <div class="stat"><div class="stat-value stat-fail">{failed}</div><div class="stat-label">Failed (expected)</div></div>
  <div class="stat"><div class="stat-value stat-warn">{total_fallbacks}</div><div class="stat-label">Table Fallbacks</div></div>
  <div class="stat"><div class="stat-value">{avg_time:.0f}ms</div><div class="stat-label">Avg Time / PDF</div></div>
</div>

<h3>Per-PDF Results</h3>
<table>
<tr><th>Status</th><th>PDF</th><th>Pages</th><th>Slides</th><th>Extract</th><th>Render</th><th>Total</th><th>Fallbacks</th></tr>
"""
    for r in results:
        badge = '<span class="badge badge-pass">PASS</span>' if r.success else '<span class="badge badge-fail">FAIL</span>'
        fb = len(r.table_fallbacks)
        fb_str = f'<span class="stat-warn">{fb}</span>' if fb else "0"
        html += (
            f'<tr><td>{badge}</td><td><strong>{r.pdf_name}</strong></td>'
            f'<td>{r.total_pages}</td><td>{r.total_slides}</td>'
            f'<td>{r.extract_time_ms:.0f}ms</td><td>{r.render_time_ms:.0f}ms</td>'
            f'<td>{r.total_time_ms:.0f}ms</td><td>{fb_str}</td></tr>\n'
        )
    html += "</table>\n"

    if failed_results:
        html += "<h3>Organic Failures</h3>\n"
        html += '<div class="note"><strong>These failures are GOOD telemetry.</strong> Each one tells us exactly what real-world structure broke the pipeline and why. '
        html += "Use this data to harden the extraction layer and improve fallback thresholds.</div>\n"
        for r in failed_results:
            error = r.errors[0] if r.errors else "Unknown"
            if "TimeoutError" in error or "TIMEOUT" in error:
                error_type = '<span class="error-type error-type-timeout">TIMEOUT</span>'
            elif "RuntimeError" in error:
                error_type = '<span class="error-type error-type-runtime">RUNTIME</span>'
            elif "ValueError" in error or "KeyError" in error or "TypeError" in error:
                error_type = '<span class="error-type error-type-value">VALUE</span>'
            elif "OSError" in error or "FileNotFoundError" in error or "PermissionError" in error:
                error_type = '<span class="error-type error-type-os">OS</span>'
            else:
                error_type = '<span class="error-type error-type-unknown">UNKNOWN</span>'
            html += f'<div class="detail"><strong>{r.pdf_name}</strong> {error_type}<br>'
            for err in r.errors:
                html += f'<div class="error-item">{err}</div>\n'
            html += "</div>\n"

    if fallback_results:
        html += "<h3>Fallback Analysis (Binary Antagonist)</h3>\n"
        html += '<div class="note"><strong>Table fallbacks mean the system correctly rejected hallucinated or unparseable tables.</strong> '
        html += "The Binary Antagonist flagged these as invalid — sparse data, grid hallucinations, or missing vector context. "
        html += "In a real-world pipeline, these regions would be rendered as screenshot-images instead of broken HTML tables.</div>\n"
        for r in fallback_results:
            html += f'<div class="detail"><strong>{r.pdf_name}</strong> <span class="badge badge-warn">{len(r.table_fallbacks)} fallback(s)</span><div class="fallback-list">\n'
            for fb in r.table_fallbacks:
                html += f'<div class="fallback-item">Page {fb.get("page", "?")} — {fb.get("reason", "unknown")}</div>\n'
            html += "</div></div>\n"

    all_stats = [r.clustering_stats for r in results if r.clustering_stats]
    if all_stats:
        total_raw = sum(s.get("raw_spans_estimated", 0) for s in all_stats)
        total_final = sum(s.get("after_vertical", 0) for s in all_stats)
        avg_reduction = sum(s.get("reduction_pct", 0) for s in all_stats) / len(all_stats)
        anomalous = [r for r in results if r.clustering_stats and r.clustering_stats.get("reduction_pct", 0) < 10 and r.clustering_stats.get("raw_spans_estimated", 0) > 50]
        html += f'<h3>Clustering Summary</h3><div class="summary">'
        html += f'<div class="stat"><div class="stat-value">{total_raw}</div><div class="stat-label">Raw spans</div></div>'
        html += f'<div class="stat"><div class="stat-value stat-pass">{total_final}</div><div class="stat-label">Final clusters</div></div>'
        html += f'<div class="stat"><div class="stat-value">{avg_reduction:.1f}%</div><div class="stat-label">Avg reduction</div></div>'
        html += f'<div class="stat"><div class="stat-value {"stat-warn" if anomalous else ""}">{len(anomalous)}</div><div class="stat-label">Anomalous PDFs</div></div></div>\n'
        if anomalous:
            html += '<div class="note"><strong>Clustering anomalies detected.</strong> These PDFs had many raw spans but very few clusters merged — likely complex multi-column layouts, tables-as-text, or unusual font hierarchies that defeated the horizontal/vertical clustering heuristics.</div>\n'
            for r in anomalous:
                cs = r.clustering_stats
                html += f'<div class="detail"><strong>{r.pdf_name}</strong> — {cs.get("raw_spans_estimated", 0)} raw spans -> {cs.get("after_vertical", 0)} clusters ({cs.get("reduction_pct", 0)}% reduction)</div>\n'

    times = sorted(r.total_time_ms for r in results if r.total_time_ms > 0)
    if times:
        p50 = times[len(times) // 2]
        p95 = times[int(len(times) * 0.95)] if len(times) > 1 else times[0]
        html += f'<h3>Performance</h3><div class="summary">'
        html += f'<div class="stat"><div class="stat-value">{p50:.0f}ms</div><div class="stat-label">P50</div></div>'
        html += f'<div class="stat"><div class="stat-value">{p95:.0f}ms</div><div class="stat-label">P95</div></div>'
        html += f'<div class="stat"><div class="stat-value">{times[-1]:.0f}ms</div><div class="stat-label">Max</div></div></div>\n'

    html += "</body></html>"
    output_path.write_text(html, encoding="utf-8")


async def main():
    hostile_dir = Path("hostile").resolve()
    output_dir = Path("test_results").resolve()
    report_path = output_dir / "organic_report.html"

    output_dir.mkdir(exist_ok=True)

    if not hostile_dir.exists():
        print("Error: hostile/ directory not found.")
        sys.exit(1)

    pdfs = sorted(hostile_dir.glob("*.pdf"))

    if not pdfs:
        print("Error: No PDFs found in hostile/.")
        sys.exit(1)

    print(f"Organic Test Runner: {len(pdfs)} hostile PDFs, {NUM_WORKERS} workers, {TIMEOUT_PER_PDF}s timeout")
    print(f"Output: {output_dir}\n")

    pool = WorkerPool(NUM_WORKERS)
    await pool.start()
    pool.set_total(len(pdfs))

    results = []
    for pdf in pdfs:
        skip = pdf.stat().st_size < 50000
        r = await pool.process(pdf, output_dir, skip_vectors=skip)
        results.append(r)

    await pool.stop()

    generate_organic_report(results, report_path, hostile_dir)

    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    total_time = sum(r.total_time_ms for r in results)
    wall_time = max(r.total_time_ms for r in results) if results else 0
    total_fb = sum(len(r.table_fallbacks) for r in results)

    print(f"\n{'=' * 60}")
    print(f"ORGANIC RESULTS: {passed} passed, {failed} failed / {len(results)} total")
    print(f"Table fallbacks: {total_fb} | Total CPU: {total_time:.0f}ms | Wall: {wall_time:.0f}ms")
    print(f"Report: {report_path}")

    if failed > 0:
        print(f"\nFailed PDFs (expected telemetry):")
        for r in results:
            if not r.success:
                print(f"  - {r.pdf_name}: {r.errors[0] if r.errors else '?'}")

    json_path = output_dir / "organic_results.json"
    json_path.write_text(json.dumps([asdict(r) for r in results], indent=2, default=str), encoding="utf-8")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
