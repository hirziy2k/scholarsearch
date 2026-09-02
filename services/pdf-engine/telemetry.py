"""Distributed Tracing & Structured Telemetry for PDF-to-PPTX conversion.

Lightweight manual W3C Trace Context implementation with no OpenTelemetry
dependency. Designed for production diagnostics without SSH access.

Usage:
    python telemetry.py          # generates a sample trace report
    python telemetry.py --json   # prints sample trace as JSON
"""

import sys
import json
import uuid
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Predefined phases for the PDF-to-PPTX orchestrator
# ---------------------------------------------------------------------------

ORCHESTRATOR_PHASES = [
    "sanitize",           # PDF sandbox validation
    "extract",            # PyMuPDF primary extraction
    "mcp_augment",        # MCP augmentation
    "cluster",            # Dynamic clustering
    "theme_classify",     # Semantic classification
    "font_emulate",       # Font metric emulation
    "validate",           # Binary table validation
    "collision_resolve",  # Collision matrix
    "render_pptx",        # PPTX rendering
    "reflow_apply",       # Auto-reflow grouping
    "metadata_bind",      # Hyperlink/bookmark binding
]

# ---------------------------------------------------------------------------
# Span
# ---------------------------------------------------------------------------

@dataclass
class Span:
    """Represents a single unit of work within a trace."""

    name: str
    start_time: float  # epoch seconds
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "ok"  # "ok" | "error" | "cancelled"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    parent_name: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Span":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# SpanHandle (context manager)
# ---------------------------------------------------------------------------

class SpanHandle:
    """Context manager for automatic span start/end timing.

    Usage::

        with trace.start_span("extract") as span:
            do_extraction()
            span.set_attribute("pages", 42)
    """

    def __init__(self, trace: "ConversionTrace", name: str,
                 attributes: Optional[Dict[str, Any]] = None):
        self._trace = trace
        self._name = name
        self._attributes: Dict[str, Any] = attributes or {}
        self._span: Optional[Span] = None

    # -- public helpers -----------------------------------------------------

    def set_attribute(self, key: str, value: Any) -> None:
        if self._span is not None:
            self._span.attributes[key] = value
        else:
            self._attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        if self._span is not None:
            self._span.events.append({
                "name": name,
                "time": time.time(),
                "attributes": attributes or {},
            })

    # -- context manager ----------------------------------------------------

    def __enter__(self) -> "SpanHandle":
        parent = self._trace.current_span_name
        self._span = Span(
            name=self._name,
            start_time=time.time(),
            status="ok",
            attributes=self._attributes,
            parent_name=parent,
        )
        self._trace.spans.append(self._span)
        self._trace.current_span_name = self._name
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        span = self._span
        if span is None:
            return False

        span.end_time = time.time()
        span.duration_ms = round((span.end_time - span.start_time) * 1000, 2)

        if exc_type is not None:
            span.status = "error"
            span.error = f"{exc_type.__name__}: {exc_val}"
        elif span.status == "ok":
            span.status = "ok"

        self._trace.current_span_name = span.parent_name
        return False  # do not suppress exceptions


# ---------------------------------------------------------------------------
# ConversionTrace
# ---------------------------------------------------------------------------

class ConversionTrace:
    """A lightweight trace context that flows through all conversion phases.

    NOT a full OpenTelemetry dependency (keeps deployment simple).
    Implements the W3C Trace Context concept manually.
    """

    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id: str = trace_id or uuid.uuid4().hex
        self.spans: List[Span] = []
        self.start_time: float = time.time()
        self.metadata: Dict[str, Any] = {}
        self.current_span_name: Optional[str] = None

    # -- span management ----------------------------------------------------

    def start_span(self, name: str,
                   attributes: Optional[Dict[str, Any]] = None) -> SpanHandle:
        """Start a new span, return a context manager handle."""
        return SpanHandle(self, name, attributes)

    # -- trace-level helpers ------------------------------------------------

    def add_event(self, name: str,
                  attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add a timestamped event to the current (most recent) span."""
        for span in reversed(self.spans):
            if span.end_time is None or span.parent_name is not None:
                span.events.append({
                    "name": name,
                    "time": time.time(),
                    "attributes": attributes or {},
                })
                return
        # fallback: attach as a trace-level event in metadata
        self.metadata.setdefault("events", []).append({
            "name": name,
            "time": time.time(),
            "attributes": attributes or {},
        })

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a trace-level attribute (e.g., pdf_name, total_pages)."""
        self.metadata[key] = value

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": self._end_time(),
            "total_duration_ms": self._total_duration_ms(),
            "metadata": self.metadata,
            "spans": [s.to_dict() for s in self.spans],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversionTrace":
        trace = cls(trace_id=data.get("trace_id"))
        trace.start_time = data.get("start_time", 0)
        trace.metadata = data.get("metadata", {})
        trace.spans = [Span.from_dict(s) for s in data.get("spans", [])]
        return trace

    # -- internals ----------------------------------------------------------

    def _end_time(self) -> Optional[float]:
        if not self.spans:
            return None
        ends = [s.end_time for s in self.spans if s.end_time is not None]
        return max(ends) if ends else None

    def _total_duration_ms(self) -> Optional[float]:
        end = self._end_time()
        if end is None:
            return None
        return round((end - self.start_time) * 1000, 2)


# ---------------------------------------------------------------------------
# StructuredLogger
# ---------------------------------------------------------------------------

class StructuredLogger:
    """Production-grade structured logging with trace context.

    Every log line is a single JSON object suitable for log aggregators
    (ELK, Datadog, CloudWatch, etc.).
    """

    def __init__(self, trace: ConversionTrace,
                 logger: Optional[logging.Logger] = None):
        self.trace = trace
        self._logger = logger or logging.getLogger("telemetry")

    def _emit(self, level: str, event: str, extra: Optional[Dict[str, Any]] = None) -> None:
        record: Dict[str, Any] = {
            "level": level,
            "event": event,
            "trace_id": self.trace.trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self.trace.current_span_name:
            record["span"] = self.trace.current_span_name
        if extra:
            record.update(extra)

        msg = json.dumps(record, default=str)
        log_level = getattr(logging, level.upper(), logging.INFO) if level != "metric" else logging.INFO
        self._logger.log(log_level, msg)

    def phase_start(self, phase: str, page: Optional[int] = None) -> None:
        extra: Dict[str, Any] = {"phase": phase}
        if page is not None:
            extra["page"] = page
        self._emit("info", "phase_start", extra)

    def phase_end(self, phase: str, duration_ms: float) -> None:
        self._emit("info", "phase_end", {"phase": phase, "duration_ms": duration_ms})

    def phase_error(self, phase: str, error: str, duration_ms: float) -> None:
        self._emit("error", "phase_error", {
            "phase": phase, "error": error, "duration_ms": duration_ms,
        })

    def warning(self, message: str, **kwargs: Any) -> None:
        self._emit("warning", "warning", {"message": message, **kwargs})

    def metric(self, name: str, value: float, unit: str = "ms") -> None:
        self._emit("metric", "metric", {"name": name, "value": value, "unit": unit})


# ---------------------------------------------------------------------------
# DiagnosticReport
# ---------------------------------------------------------------------------

class DiagnosticReport:
    """Generate visual waterfall HTML/SVG reports from a ConversionTrace."""

    # -- colour palette -----------------------------------------------------
    _STATUS_COLOURS = {
        "ok": "#22c55e",
        "error": "#ef4444",
        "cancelled": "#eab308",
        "skipped": "#9ca3af",
    }

    def generate_html(self, trace: ConversionTrace) -> str:
        """Generate a self-contained waterfall HTML report."""
        spans = trace.spans
        total_ms = trace._total_duration_ms() or 0
        start = trace.start_time

        # summary stats
        durations = [s.duration_ms for s in spans if s.duration_ms is not None]
        fastest = min(durations) if durations else 0
        slowest = max(durations) if durations else 0
        error_count = sum(1 for s in spans if s.status == "error")

        # build span rows
        rows_html = ""
        for s in spans:
            colour = self._STATUS_COLOURS.get(s.status, "#9ca3af")
            left_pct = ((s.start_time - start) / (total_ms / 1000)) * 100 if total_ms else 0
            width_pct = (s.duration_ms / total_ms) * 100 if total_ms else 0
            tooltip = self._span_tooltip(s)
            parent_label = f"  (child of {s.parent_name})" if s.parent_name else ""
            rows_html += f"""
            <tr>
              <td class="phase-name">{s.name}{parent_label}</td>
              <td class="bar-cell">
                <div class="bar" style="margin-left:{left_pct:.1f}%;width:{max(width_pct, 0.5):.1f}%;background:{colour};"
                     title="{tooltip}"></div>
              </td>
              <td class="duration">{s.duration_ms:.1f} ms</td>
              <td class="status" style="color:{colour}">{s.status}</td>
            </tr>"""

        # metadata rows
        meta_rows = ""
        for k, v in trace.metadata.items():
            if k == "events":
                continue
            meta_rows += f"<tr><td class='meta-key'>{k}</td><td>{v}</td></tr>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Conversion Trace {trace.trace_id[:12]}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background:#0f172a; color:#e2e8f0; padding:24px; }}
  h1 {{ font-size:1.4rem; margin-bottom:4px; }}
  .subtitle {{ color:#94a3b8; font-size:0.85rem; margin-bottom:20px; }}
  .summary {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:24px; }}
  .stat {{ background:#1e293b; border-radius:8px; padding:14px 20px; min-width:140px; }}
  .stat .label {{ font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; }}
  .stat .value {{ font-size:1.5rem; font-weight:700; margin-top:2px; }}
  .stat .value.error-val {{ color:#ef4444; }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:24px; }}
  th {{ text-align:left; padding:8px 12px; background:#1e293b; font-size:0.75rem; color:#94a3b8;
        text-transform:uppercase; letter-spacing:0.05em; border-bottom:1px solid #334155; }}
  td {{ padding:6px 12px; border-bottom:1px solid #1e293b; vertical-align:middle; }}
  .phase-name {{ white-space:nowrap; font-size:0.85rem; min-width:200px; }}
  .bar-cell {{ position:relative; height:22px; }}
  .bar {{ position:absolute; top:3px; height:16px; border-radius:4px; min-width:2px; cursor:pointer; }}
  .bar:hover {{ filter:brightness(1.3); }}
  .duration {{ font-variant-numeric:tabular-nums; font-size:0.85rem; color:#94a3b8; min-width:90px; }}
  .status {{ font-size:0.8rem; font-weight:600; min-width:70px; }}
  .meta-table {{ margin-bottom:24px; }}
  .meta-table td {{ padding:4px 12px; font-size:0.85rem; }}
  .meta-key {{ color:#94a3b8; font-weight:600; min-width:160px; }}
  .json-toggle {{ background:#334155; border:none; color:#e2e8f0; padding:8px 16px; border-radius:6px;
                  cursor:pointer; font-size:0.85rem; margin-bottom:12px; }}
  .json-toggle:hover {{ background:#475569; }}
  pre {{ background:#1e293b; border-radius:8px; padding:16px; overflow-x:auto; font-size:0.8rem;
         display:none; max-height:400px; overflow-y:auto; }}
  .legend {{ display:flex; gap:16px; margin-bottom:16px; font-size:0.8rem; color:#94a3b8; }}
  .legend span::before {{ content:''; display:inline-block; width:12px; height:12px; border-radius:3px;
                          margin-right:4px; vertical-align:middle; }}
  .legend .l-ok::before {{ background:#22c55e; }}
  .legend .l-error::before {{ background:#ef4444; }}
  .legend .l-cancelled::before {{ background:#eab308; }}
  .legend .l-skipped::before {{ background:#9ca3af; }}
</style>
</head>
<body>
  <h1>Conversion Trace Report</h1>
  <div class="subtitle">trace_id: {trace.trace_id} &mdash; generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</div>

  <div class="summary">
    <div class="stat"><div class="label">Total Time</div><div class="value">{total_ms:.1f} ms</div></div>
    <div class="stat"><div class="label">Phases</div><div class="value">{len(spans)}</div></div>
    <div class="stat"><div class="label">Fastest</div><div class="value">{fastest:.1f} ms</div></div>
    <div class="stat"><div class="label">Slowest</div><div class="value">{slowest:.1f} ms</div></div>
    <div class="stat"><div class="label">Errors</div><div class="value {'error-val' if error_count else ''}">{error_count}</div></div>
  </div>

  <div class="legend">
    <span class="l-ok">ok</span>
    <span class="l-error">error</span>
    <span class="l-cancelled">cancelled</span>
    <span class="l-skipped">skipped</span>
  </div>

  <table>
    <thead><tr><th>Phase</th><th>Timeline</th><th>Duration</th><th>Status</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>

  {f'''<h2 style="font-size:1rem;margin-bottom:8px;">Metadata</h2>
  <table class="meta-table">{meta_rows}</table>''' if meta_rows else ''}

  <button class="json-toggle" onclick="var p=document.getElementById('json');p.style.display=p.style.display==='block'?'none':'block';">
    Toggle Raw JSON
  </button>
  <pre id="json">{trace.to_json()}</pre>
</body>
</html>"""

    def generate_waterfall_svg(self, trace: ConversionTrace) -> str:
        """Generate an SVG waterfall chart for embedding in other reports."""
        spans = trace.spans
        total_ms = trace._total_duration_ms() or 1
        start = trace.start_time

        row_h = 28
        label_w = 170
        bar_area_w = 520
        total_w = label_w + bar_area_w + 80
        total_h = 40 + len(spans) * row_h + 20

        lines: List[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" '
            f'viewBox="0 0 {total_w} {total_h}" style="background:#0f172a;font-family:system-ui,sans-serif;">',
            '<defs><style>text{fill:#e2e8f0} .label{font-size:11px} .dur{font-size:10px;fill:#94a3b8} '
            '.hdr{font-size:10px;fill:#94a3b8;font-weight:600}</style></defs>',
        ]

        # header
        y = 24
        lines.append(f'<text x="8" y="{y}" class="hdr">PHASE</text>')
        lines.append(f'<text x="{label_w}" y="{y}" class="hdr">TIMELINE</text>')
        lines.append(f'<text x="{label_w + bar_area_w + 8}" y="{y}" class="hdr">DURATION</text>')
        y += 16
        lines.append(f'<line x1="0" y1="{y}" x2="{total_w}" y2="{y}" stroke="#334155" stroke-width="1"/>')
        y += 4

        for s in spans:
            colour = self._STATUS_COLOURS.get(s.status, "#9ca3af")
            left = ((s.start_time - start) / (total_ms / 1000)) * bar_area_w if total_ms else 0
            width = max((s.duration_ms / total_ms) * bar_area_w if total_ms else 0, 3)

            lines.append(f'<text x="8" y="{y + 14}" class="label" fill="#e2e8f0">{s.name}</text>')
            lines.append(
                f'<rect x="{label_w + left}" y="{y + 3}" width="{width}" height="14" rx="3" '
                f'fill="{colour}" opacity="0.9"/>'
            )
            lines.append(
                f'<text x="{label_w + bar_area_w + 8}" y="{y + 14}" class="dur">'
                f'{s.duration_ms:.1f} ms</text>'
            )
            y += row_h

        lines.append("</svg>")
        return "\n".join(lines)

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _span_tooltip(s: Span) -> str:
        parts = [f"Status: {s.status}"]
        if s.error:
            parts.append(f"Error: {s.error}")
        for ev in s.events:
            parts.append(f"Event: {ev.get('name', '?')}")
        for k, v in s.attributes.items():
            parts.append(f"{k}: {v}")
        return "&#10;".join(parts)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_conversion_trace(pdf_path: Optional[str] = None) -> ConversionTrace:
    """Factory that creates a trace with PDF metadata."""
    trace = ConversionTrace()
    if pdf_path:
        p = Path(pdf_path)
        trace.set_attribute("pdf_name", p.name)
        trace.set_attribute("pdf_size_bytes", p.stat().st_size)
    return trace


# ---------------------------------------------------------------------------
# Standalone demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    """Simulate a full conversion pipeline and produce a sample report."""
    import sys

    print("Building sample trace with all orchestrator phases ...")
    trace = create_conversion_trace()
    trace.set_attribute("pdf_name", "sample_report.pdf")
    trace.set_attribute("pdf_size_bytes", 2_457_600)
    trace.set_attribute("total_pages", 24)
    trace.set_attribute("output_pptx", "sample_report.pptx")

    sim_data = [
        ("sanitize",           12.4,  "ok",    None),
        ("extract",           387.2,  "ok",    None),
        ("mcp_augment",       214.6,  "ok",    None),
        ("cluster",            56.8,  "ok",    None),
        ("theme_classify",     31.2,  "ok",    None),
        ("font_emulate",      198.5,  "ok",    None),
        ("validate",           18.3,  "ok",    None),
        ("collision_resolve",   9.7,  "ok",    None),
        ("render_pptx",       442.1,  "ok",    None),
        ("reflow_apply",       67.4,  "ok",    None),
        ("metadata_bind",      23.9,  "error", "TimeoutError: bookmark HTTP request exceeded 5s"),
    ]

    for phase, dur_ms, status, err in sim_data:
        with trace.start_span(phase) as span:
            # simulate work
            time.sleep(dur_ms / 1000.0)
            span.set_attribute("duration_target_ms", dur_ms)
            span.add_event("started")
            if status == "error":
                span.status = "error"
                span.error = err
                raise RuntimeError(err)

    # Write HTML report
    report = DiagnosticReport()
    html = report.generate_html(trace)
    html_path = Path(__file__).parent / "trace_report.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML report written to: {html_path}")

    # Write SVG report
    svg = report.generate_waterfall_svg(trace)
    svg_path = Path(__file__).parent / "trace_waterfall.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(f"SVG  report written to: {svg_path}")

    if "--json" in sys.argv:
        print("\nJSON trace:\n")
        print(trace.to_json())
    else:
        print(f"\nTrace summary: {len(trace.spans)} phases, "
              f"total {trace._total_duration_ms():.1f} ms")


def _demo_safe() -> None:
    """Wrap the demo so the intentional error in the last phase doesn't crash."""
    trace = create_conversion_trace()
    trace.set_attribute("pdf_name", "sample_report.pdf")
    trace.set_attribute("pdf_size_bytes", 2_457_600)
    trace.set_attribute("total_pages", 24)
    trace.set_attribute("output_pptx", "sample_report.pptx")

    logger = StructuredLogger(trace)

    sim_data = [
        ("sanitize",           12.4,  "ok",    None),
        ("extract",           387.2,  "ok",    None),
        ("mcp_augment",       214.6,  "ok",    None),
        ("cluster",            56.8,  "ok",    None),
        ("theme_classify",     31.2,  "ok",    None),
        ("font_emulate",      198.5,  "ok",    None),
        ("validate",           18.3,  "ok",    None),
        ("collision_resolve",   9.7,  "ok",    None),
        ("render_pptx",       442.1,  "ok",    None),
        ("reflow_apply",       67.4,  "ok",    None),
        ("metadata_bind",      23.9,  "error", "TimeoutError: bookmark HTTP request exceeded 5s"),
    ]

    for phase, target_ms, target_status, err_msg in sim_data:
        logger.phase_start(phase, page=1)
        try:
            with trace.start_span(phase) as span:
                time.sleep(target_ms / 1000.0)
                span.set_attribute("target_ms", target_ms)
                span.add_event("completed")
                if target_status == "error":
                    raise RuntimeError(err_msg)
                logger.phase_end(phase, target_ms)
        except Exception:
            logger.phase_error(phase, err_msg or "unknown", target_ms)

    # summary metrics
    logger.metric("total_phases", len(sim_data), unit="count")
    logger.metric("error_phases", 1, unit="count")

    # reports
    report = DiagnosticReport()
    base = Path(__file__).parent
    html_path = base / "trace_report.html"
    svg_path = base / "trace_waterfall.svg"

    html_path.write_text(report.generate_html(trace), encoding="utf-8")
    print(f"HTML report written to: {html_path}")

    svg_path.write_text(report.generate_waterfall_svg(trace), encoding="utf-8")
    print(f"SVG  report written to: {svg_path}")

    print(f"\nTrace summary: {len(trace.spans)} phases, "
          f"total {trace._total_duration_ms():.1f} ms, "
          f"errors: {sum(1 for s in trace.spans if s.status == 'error')}")

    if "--json" in sys.argv:
        print("\nJSON trace:\n")
        print(trace.to_json())


if __name__ == "__main__":
    _demo_safe()
