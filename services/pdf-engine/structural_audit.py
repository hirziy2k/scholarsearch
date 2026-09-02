#!/usr/bin/env python3
"""
Structural Audit Script for PDF-to-PPTX Converter Output.

Opens each generated PPTX as a ZIP, parses slide XML, and runs spatial,
clustering, and content checks. Produces a dark-themed HTML report.

Usage: python structural_audit.py
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# PPTX XML namespaces
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

# Default slide dimensions in EMU (Letter: 8.5" x 11")
DEFAULT_SLIDE_W = 7772400   # 8.5 inches
DEFAULT_SLIDE_H = 10058400  # 11 inches

# Shape-count threshold per slide
MAX_SHAPES_PER_SLIDE = 20

# Helpers for resolving XML tag names with namespace prefix
def _ns(tag: str, prefix: str = "p") -> str:
    """Resolve ``prefix:tag`` using the NS map."""
    return f"{{{NS[prefix]}}}{tag}"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ShapeInfo:
    name: str
    left: int    # EMU
    top: int     # EMU
    width: int   # EMU
    height: int  # EMU
    text: str
    kind: str    # "textbox" | "shape" | "table" | "unknown"

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def area(self) -> int:
        return self.width * self.height

    def overlap_area(self, other: "ShapeInfo") -> int:
        """Return the area of overlap between two shapes (0 if none)."""
        x_overlap = max(0, min(self.right, other.right) - max(self.left, other.left))
        y_overlap = max(0, min(self.bottom, other.bottom) - max(self.top, other.top))
        return x_overlap * y_overlap

    def bbox_str(self) -> str:
        return f"({self.left},{self.top}) {self.width}x{self.height}"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    severity: str = "error"  # "error" | "warning"


@dataclass
class SlideAudit:
    slide_number: int
    shape_count: int
    shapes: List[ShapeInfo] = field(default_factory=list)
    checks: List[CheckResult] = field(default_factory=list)


@dataclass
class FileAudit:
    file_path: str
    file_name: str
    slide_count: int = 0
    slides: List[SlideAudit] = field(default_factory=list)
    checks: List[CheckResult] = field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0
    score: float = 0.0
    error: str = ""

    def compute_score(self):
        self.total_checks = len(self.checks)
        self.passed_checks = sum(1 for c in self.checks if c.passed)
        self.score = (self.passed_checks / self.total_checks * 100) if self.total_checks else 0.0


# ---------------------------------------------------------------------------
# PPTX XML parsing helpers
# ---------------------------------------------------------------------------

def _find_text(node: ET.Element) -> str:
    """Recursively extract all text content from a DrawingML text body."""
    parts: List[str] = []
    for t_elem in node.iter(_ns("t", "a")):
        if t_elem.text:
            parts.append(t_elem.text)
    return "".join(parts).strip()


def _parse_xfrm(sp: ET.Element) -> Optional[Tuple[int, int, int, int]]:
    """Extract (left, top, width, height) in EMU from a shape's ``<a:xfrm>``."""
    xfrm = sp.find(_ns("spPr", "p"))
    if xfrm is None:
        xfrm = sp.find(_ns("spPr", "a"))
    if xfrm is None:
        return None

    xfrm_inner = xfrm.find(_ns("xfrm", "a"))
    if xfrm_inner is None:
        xfrm_inner = xfrm  # sometimes xfrm is directly under spPr

    off = xfrm_inner.find(_ns("off", "a"))
    ext = xfrm_inner.find(_ns("ext", "a"))
    if off is None or ext is None:
        return None

    try:
        left = int(off.get("x", "0"))
        top = int(off.get("y", "0"))
        width = int(ext.get("cx", "0"))
        height = int(ext.get("cy", "0"))
    except (ValueError, TypeError):
        return None

    return left, top, width, height


def _shape_name(sp: ET.Element, idx: int) -> str:
    """Best-effort human-readable name for a shape."""
    nvSpPr = sp.find(_ns("nvSpPr", "p"))
    if nvSpPr is not None:
        cNvPr = nvSpPr.find(_ns("cNvPr", "p"))
        if cNvPr is not None and cNvPr.get("name"):
            return cNvPr.get("name")
    return f"Shape_{idx}"


def _classify_shape(sp: ET.Element) -> str:
    if sp.find(_ns("txBody", "p")) is not None or sp.find(_ns("txBody", "a")) is not None:
        return "textbox"
    if sp.find(_ns("graphic", "a")) is not None:
        return "table"
    if sp.find(_ns("spPr", "p")) is not None:
        return "shape"
    return "unknown"


def _slide_dims(prs_tree: ET.Element) -> Tuple[int, int]:
    """Return (width, height) in EMU from [Content_Types].xml or presentation.xml.

    Fallback to default Letter size.
    """
    sldSz = prs_tree.find(_ns("sldSz", "p"))
    if sldSz is not None:
        try:
            return int(sldSz.get("cx", DEFAULT_SLIDE_W)), int(sldSz.get("cy", DEFAULT_SLIDE_H))
        except (ValueError, TypeError):
            pass
    return DEFAULT_SLIDE_W, DEFAULT_SLIDE_H


def parse_slide_xml(xml_bytes: bytes, slide_num: int, slide_w: int, slide_h: int) -> SlideAudit:
    """Parse a single slide XML and return a SlideAudit."""
    root = ET.fromstring(xml_bytes)
    shapes: List[ShapeInfo] = []
    idx = 0

    # All shape types live under <p:cSld><p:spTree>
    cSld = root.find(_ns("cSld", "p"))
    if cSld is None:
        return SlideAudit(slide_number=slide_num, shape_count=0)

    spTree = cSld.find(_ns("spTree", "p"))
    if spTree is None:
        return SlideAudit(slide_number=slide_num, shape_count=0)

    for sp in spTree:
        # Skip non-shape elements (e.g. <p:nvGrpSpPr>, <p:grpSpPr>, <p:cNvGrpSpPr>)
        if not sp.tag.endswith("}sp") and not sp.tag.endswith("}pic"):
            continue

        # Skip group shapes (we don't recurse into them for now)
        if sp.tag == _ns("grpSp", "p"):
            continue

        idx += 1
        bbox = _parse_xfrm(sp)
        if bbox is None:
            continue

        left, top, width, height = bbox
        name = _shape_name(sp, idx)
        kind = _classify_shape(sp)

        # Extract text
        tx_body = sp.find(_ns("txBody", "p"))
        if tx_body is None:
            tx_body = sp.find(_ns("txBody", "a"))
        text = _find_text(tx_body) if tx_body is not None else ""

        shapes.append(ShapeInfo(name=name, left=left, top=top,
                                width=width, height=height, text=text, kind=kind))

    audit = SlideAudit(slide_number=slide_num, shape_count=len(shapes), shapes=shapes)

    # ── Run checks on this slide ──────────────────────────────────────────

    # 1. Clustering: too many shapes
    audit.checks.append(CheckResult(
        name="shape_count",
        passed=not (len(shapes) > MAX_SHAPES_PER_SLIDE),
        detail=f"{len(shapes)} shapes" + (f" (>{MAX_SHAPES_PER_SLIDE})" if len(shapes) > MAX_SHAPES_PER_SLIDE else ""),
        severity="warning",
    ))

    for s in shapes:
        # 2. Zero-dimension shapes
        audit.checks.append(CheckResult(
            name="zero_dimension",
            passed=s.width > 0 and s.height > 0,
            detail=f"{s.name}: {s.width}x{s.height} EMU",
        ))

        # 3. Margin / boundary check (negative coords or exceeding slide)
        out_of_bounds = s.left < 0 or s.top < 0 or s.right > slide_w or s.bottom > slide_h
        audit.checks.append(CheckResult(
            name="margin",
            passed=not out_of_bounds,
            detail=f"{s.name} at {s.bbox_str()} (slide {slide_w}x{slide_h})" if out_of_bounds else "",
        ))

        # 4. Coordinate sanity: positive values and within 2x slide dims
        sane = (0 <= s.left <= slide_w * 2 and 0 <= s.top <= slide_h * 2
                and 0 < s.width <= slide_w * 2 and 0 < s.height <= slide_h * 2)
        audit.checks.append(CheckResult(
            name="coordinate_sanity",
            passed=sane,
            detail=f"{s.name}: {s.bbox_str()}" if not sane else "",
        ))

        # 5. Text content check (only for textboxes)
        if s.kind == "textbox":
            audit.checks.append(CheckResult(
                name="text_content",
                passed=len(s.text) > 0,
                detail=f"{s.name}: empty" if not s.text else "",
                severity="warning",
            ))

    # 6. Overlap detection (pairwise among shapes)
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            area = shapes[i].overlap_area(shapes[j])
            if area > 0:
                audit.checks.append(CheckResult(
                    name="overlap",
                    passed=False,
                    detail=f"{shapes[i].name} <-> {shapes[j].name} overlap area={area:,} EMU^2",
                    severity="warning",
                ))

    return audit


# ---------------------------------------------------------------------------
# Top-level audit for a single PPTX file
# ---------------------------------------------------------------------------

def audit_pptx(pptx_path: str) -> FileAudit:
    """Open a PPTX and audit all its slides."""
    file_name = os.path.basename(pptx_path)
    fa = FileAudit(file_path=pptx_path, file_name=file_name)

    if not os.path.isfile(pptx_path):
        fa.error = f"File not found: {pptx_path}"
        fa.checks.append(CheckResult(name="file_exists", passed=False, detail=fa.error))
        fa.compute_score()
        return fa

    try:
        with zipfile.ZipFile(pptx_path, "r") as zf:
            names = zf.namelist()

            # ── Presentation-level dimensions ──────────────────────────────
            prs_xml = None
            prs_path = "ppt/presentation.xml"
            if prs_path in names:
                prs_xml = zf.read(prs_path)
            else:
                # Try to find any .xml at root level
                for n in names:
                    if n.endswith("presentation.xml") and n.count("/") <= 2:
                        prs_xml = zf.read(n)
                        break

            if prs_xml is not None:
                prs_tree = ET.fromstring(prs_xml)
                slide_w, slide_h = _slide_dims(prs_tree)
            else:
                slide_w, slide_h = DEFAULT_SLIDE_W, DEFAULT_SLIDE_H

            # ── Slide XMLs ─────────────────────────────────────────────────
            slide_files = sorted(
                [n for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
                key=lambda x: int(x.split("slide")[-1].replace(".xml", "")),
            )

            fa.slide_count = len(slide_files)

            for i, slide_path in enumerate(slide_files, start=1):
                slide_bytes = zf.read(slide_path)
                sa = parse_slide_xml(slide_bytes, i, slide_w, slide_h)
                fa.slides.append(sa)

            # ── File-level aggregate checks ────────────────────────────────
            total_shapes = sum(s.shape_count for s in fa.slides)
            total_overlaps = sum(1 for s in fa.slides for c in s.checks if c.name == "overlap")
            total_zero_dim = sum(1 for s in fa.slides for c in s.checks if c.name == "zero_dimension" and not c.passed)
            total_oob = sum(1 for s in fa.slides for c in s.checks if c.name == "margin" and not c.passed)
            total_empty = sum(1 for s in fa.slides for c in s.checks if c.name == "text_content" and not c.passed)
            total_sane = sum(1 for s in fa.slides for c in s.checks if c.name == "coordinate_sanity" and not c.passed)
            clustering_fails = sum(1 for s in fa.slides for c in s.checks if c.name == "shape_count" and not c.passed)

            fa.checks.append(CheckResult(
                name="file_parseable", passed=True,
                detail=f"{fa.slide_count} slides, {total_shapes} total shapes",
            ))
            fa.checks.append(CheckResult(
                name="no_overlaps", passed=(total_overlaps == 0),
                detail=f"{total_overlaps} overlap(s) detected" if total_overlaps else "",
                severity="warning",
            ))
            fa.checks.append(CheckResult(
                name="no_zero_dimensions", passed=(total_zero_dim == 0),
                detail=f"{total_zero_dim} zero-dimension shape(s)" if total_zero_dim else "",
            ))
            fa.checks.append(CheckResult(
                name="all_within_margins", passed=(total_oob == 0),
                detail=f"{total_oob} out-of-bounds shape(s)" if total_oob else "",
            ))
            fa.checks.append(CheckResult(
                name="all_coords_sane", passed=(total_sane == 0),
                detail=f"{total_sane} insane coordinate(s)" if total_sane else "",
            ))
            fa.checks.append(CheckResult(
                name="no_empty_textboxes", passed=(total_empty == 0),
                detail=f"{total_empty} empty textbox(es)" if total_empty else "",
                severity="warning",
            ))
            fa.checks.append(CheckResult(
                name="clustering_ok", passed=(clustering_fails == 0),
                detail=f"{clustering_fails} slide(s) with >{MAX_SHAPES_PER_SLIDE} shapes" if clustering_fails else "",
            ))

    except zipfile.BadZipFile:
        fa.error = "Not a valid ZIP/PPTX file"
        fa.checks.append(CheckResult(name="file_parseable", passed=False, detail=fa.error))
    except Exception as e:
        fa.error = f"Error: {e}"
        fa.checks.append(CheckResult(name="file_parseable", passed=False, detail=fa.error))

    fa.compute_score()
    return fa


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _score_color(score: float) -> str:
    if score >= 90:
        return "#3fb950"
    if score >= 70:
        return "#d29922"
    return "#f85149"


def _badge(passed: bool, severity: str = "error") -> str:
    if passed:
        return '<span class="badge badge-pass">PASS</span>'
    if severity == "warning":
        return '<span class="badge badge-warn">WARN</span>'
    return '<span class="badge badge-fail">FAIL</span>'


def generate_report(audits: List[FileAudit], output_path: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n_files = len(audits)
    all_checks = [c for a in audits for c in a.checks]
    n_pass = sum(1 for c in all_checks if c.passed)
    n_fail = len(all_checks) - n_pass
    avg_score = (sum(a.score for a in audits) / n_files) if n_files else 0

    # Overlap summary across all files
    overlap_details = []
    for a in audits:
        for sa in a.slides:
            for c in sa.checks:
                if c.name == "overlap" and not c.passed:
                    overlap_details.append((a.file_name, sa.slide_number, c.detail))

    rows_html = []
    for a in audits:
        sc = _score_color(a.score)
        rows_html.append(
            f'<tr>'
            f'<td><strong>{_esc(a.file_name)}</strong></td>'
            f'<td>{a.slide_count}</td>'
            f'<td style="color:{sc};font-weight:700">{a.score:.1f}%</td>'
            f'<td>{_badge(a.total_checks == a.passed_checks)}</td>'
            f'<td>{a.passed_checks}/{a.total_checks}</td>'
            f'<td class="detail-cell">{_render_checks(a.checks)}</td>'
            f'</tr>'
        )

    overlap_section = ""
    if overlap_details:
        items = "".join(
            f'<div class="overlap-item">{_esc(fn)} — Slide {sl}: {_esc(det)}</div>'
            for fn, sl, det in overlap_details
        )
        overlap_section = f'<h3>Overlap Details</h3><div class="detail">{items}</div>'

    # Per-file slide-level detail
    detail_sections = []
    for a in audits:
        if not a.slides:
            continue
        slide_cards = []
        for sa in a.slides:
            check_rows = []
            for c in sa.checks:
                detail_html = (
                    f'<span class="check-detail">{_esc(c.detail)}</span>' if c.detail else ""
                )
                check_rows.append(
                    f'<div class="check-row">{_badge(c.passed, c.severity)} '
                    f'<span class="check-name">{_esc(c.name)}</span>'
                    f'{detail_html}</div>'
                )
            check_rows = "".join(check_rows)
            slide_cards.append(
                f'<div class="slide-card">'
                f'<div class="slide-card-title">Slide {sa.slide_number} '
                f'({sa.shape_count} shapes)</div>{check_rows}</div>'
            )
        detail_sections.append(
            f'<details><summary class="file-summary">{_esc(a.file_name)}</summary>'
            f'<div class="slide-grid">{"".join(slide_cards)}</div></details>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Structural Audit Report</title>
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
.detail {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
.overlap-item {{ background: #da363322; border-left: 3px solid #da3633; padding: 4px 8px; margin: 4px 0; border-radius: 0 4px 4px 0; font-size: 12px; }}
.detail-cell {{ max-width: 360px; }}
.check-row {{ display: flex; align-items: center; gap: 6px; padding: 2px 0; font-size: 12px; }}
.check-name {{ color: #8b949e; min-width: 120px; }}
.check-detail {{ color: #c9d1d9; }}
.file-summary {{ cursor: pointer; padding: 10px 12px; background: #161b22; border: 1px solid #30363d; border-radius: 6px; margin-bottom: 8px; font-size: 14px; font-weight: 600; color: #58a6ff; list-style: none; }}
.file-summary::-webkit-details-marker {{ display: none; }}
.file-summary::before {{ content: "\\25B6 "; font-size: 10px; }}
details[open] > .file-summary::before {{ content: "\\25BC "; }}
.slide-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 8px; margin: 8px 0 20px; padding-left: 12px; }}
.slide-card {{ background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 10px; font-size: 12px; }}
.slide-card-title {{ color: #58a6ff; font-weight: 600; margin-bottom: 6px; }}
.score-bar-wrap {{ height: 12px; background: #21262d; border-radius: 6px; overflow: hidden; margin-top: 8px; }}
.score-bar {{ height: 100%; border-radius: 6px; transition: width .3s; }}
</style>
</head>
<body>
<h1>Structural Audit Report</h1>
<h2>Generated {now} | {n_files} PPTX files</h2>

<div class="summary">
  <div class="stat"><div class="stat-value" style="color:{_score_color(avg_score)}">{avg_score:.1f}%</div><div class="stat-label">Avg Score</div></div>
  <div class="stat"><div class="stat-value stat-pass">{n_pass}</div><div class="stat-label">Checks Passed</div></div>
  <div class="stat"><div class="stat-value stat-fail">{n_fail}</div><div class="stat-label">Checks Failed</div></div>
  <div class="stat"><div class="stat-value">{len(overlap_details)}</div><div class="stat-label">Overlap Pairs</div></div>
</div>

<h3>Per-File Results</h3>
<table>
<tr><th>File</th><th>Slides</th><th>Score</th><th>Status</th><th>Checks</th><th>Details</th></tr>
{"".join(rows_html)}
</table>

{overlap_section}

<h3>Slide-Level Detail</h3>
{"".join(detail_sections)}

</body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def _esc(text: str) -> str:
    """Minimal HTML escape."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _render_checks(checks: List[CheckResult]) -> str:
    fails = [c for c in checks if not c.passed]
    if not fails:
        return '<span class="badge badge-pass">ALL PASS</span>'
    parts = [_badge(c.passed, c.severity) for c in fails[:4]]
    extra = len(fails) - 4
    if extra > 0:
        parts.append(f'<span style="color:#8b949e">+{extra}</span>')
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    base_dir = Path(__file__).resolve().parent
    results_dir = base_dir / "test_results"

    # Find results JSON
    results_file = None
    for candidate in ["results.json", "organic_results.json"]:
        p = results_dir / candidate
        if p.exists():
            results_file = p
            break

    if results_file is None:
        print("ERROR: No results.json found in test_results/")
        sys.exit(1)

    print(f"Loading results from {results_file.name}")
    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    pptx_files = [
        r["output_path"] for r in results
        if r.get("success") and r.get("output_path")
    ]

    print(f"Found {len(pptx_files)} PPTX files to audit\n")

    audits: List[FileAudit] = []
    for pptx_path in pptx_files:
        name = os.path.basename(pptx_path)
        print(f"  Auditing {name}...", end=" ", flush=True)
        a = audit_pptx(pptx_path)
        audits.append(a)
        status = "OK" if a.error else f"{a.score:.0f}%"
        fails = a.total_checks - a.passed_checks
        print(f"{status}  ({a.passed_checks}/{a.total_checks} passed, {fails} failed)")

    # Generate HTML report
    output_path = str(results_dir / "structural_audit.html")
    generate_report(audits, output_path)
    print(f"\nReport saved to {output_path}")

    # Print summary
    all_checks = [c for a in audits for c in a.checks]
    n_pass = sum(1 for c in all_checks if c.passed)
    n_total = len(all_checks)
    avg = sum(a.score for a in audits) / len(audits) if audits else 0
    print(f"\n{'='*50}")
    print(f"  Overall: {n_pass}/{n_total} checks passed")
    print(f"  Average score: {avg:.1f}%")
    perfect = sum(1 for a in audits if a.score == 100)
    print(f"  Perfect scores: {perfect}/{len(audits)} files")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
