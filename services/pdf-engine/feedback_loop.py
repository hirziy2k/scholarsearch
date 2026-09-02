from __future__ import annotations

import json
import shutil
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VALID_RATINGS = {"good", "bad", "partial"}
VALID_CATEGORIES = {"layout", "missing_content", "extra_content", "font", "color", "other"}
VALID_STATUSES = {"new", "reviewing", "added_to_ci", "dismissed"}
ISO_FMT = "%Y-%m-%dT%H:%M:%S%z"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO_FMT)


def _load_json(path: Path) -> List[Dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save_json(path: Path, data: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _entry_to_dict(entry: FeedbackEntry) -> Dict[str, Any]:
    return asdict(entry)


def _dict_to_entry(d: Dict[str, Any]) -> FeedbackEntry:
    return FeedbackEntry(**d)


@dataclass
class FeedbackEntry:
    feedback_id: str
    job_id: str
    rating: str
    category: str
    description: str
    page_numbers: List[int]
    created_at: str
    api_key: Optional[str]
    pdf_name: str
    pdf_stored_path: Optional[str]
    status: str = "new"


class FeedbackCollector:
    def __init__(self, storage_dir: Optional[str] = None, redis_url: Optional[str] = None):
        base = Path(storage_dir) if storage_dir else Path("test_results") / "feedback_archive"
        self.storage_dir: Path = base
        self.feed_file: Path = self.storage_dir / "feedback_entries.json"
        self.redis_url = redis_url

    def _entries(self) -> List[FeedbackEntry]:
        return [_dict_to_entry(d) for d in _load_json(self.feed_file)]

    def _persist(self, entries: List[FeedbackEntry]) -> None:
        _save_json(self.feed_file, [_entry_to_dict(e) for e in entries])

    async def submit_feedback(
        self,
        job_id: str,
        rating: str,
        category: str = "other",
        description: str = "",
        page_numbers: Optional[List[int]] = None,
        api_key: Optional[str] = None,
        pdf_path: Optional[str] = None,
    ) -> FeedbackEntry:
        rating = rating.lower().strip()
        category = category.lower().strip()
        if rating not in VALID_RATINGS:
            raise ValueError(f"Invalid rating {rating!r}, must be one of {VALID_RATINGS}")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category {category!r}, must be one of {VALID_CATEGORIES}")

        feedback_id = str(uuid.uuid4())
        stored_path: Optional[str] = None

        if rating in ("bad", "partial") and pdf_path:
            src = Path(pdf_path)
            if src.exists():
                dest_dir = self.storage_dir / feedback_id
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / "input.pdf"
                shutil.copy2(str(src), str(dest))
                stored_path = str(dest)

        entry = FeedbackEntry(
            feedback_id=feedback_id,
            job_id=job_id,
            rating=rating,
            category=category,
            description=description,
            page_numbers=page_numbers or [],
            created_at=_utcnow_iso(),
            api_key=api_key,
            pdf_name=Path(pdf_path).name if pdf_path else "",
            pdf_stored_path=stored_path,
            status="new",
        )

        entries = self._entries()
        entries.append(entry)
        self._persist(entries)
        return entry

    async def get_feedback(self, feedback_id: str) -> Optional[FeedbackEntry]:
        for e in self._entries():
            if e.feedback_id == feedback_id:
                return e
        return None

    async def list_feedback(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[FeedbackEntry]:
        entries = self._entries()
        if status:
            entries = [e for e in entries if e.status == status]
        return entries[-limit:]

    async def get_feedback_stats(self) -> Dict[str, Any]:
        entries = self._entries()
        rating_counts = Counter(e.rating for e in entries)
        category_counts = Counter(e.category for e in entries)
        page_counter: Counter[int] = Counter()
        for e in entries:
            for p in e.page_numbers:
                page_counter[p] += 1

        top_issues = [
            {"category": cat, "count": cnt, "sample": _find_sample(entries, cat)}
            for cat, cnt in category_counts.most_common(5)
        ]

        return {
            "total_count": len(entries),
            "by_rating": {r: rating_counts.get(r, 0) for r in VALID_RATINGS},
            "by_category": {c: category_counts.get(c, 0) for c in VALID_CATEGORIES},
            "by_page": dict(page_counter.most_common(20)),
            "top_issues": top_issues,
        }


def _find_sample(entries: List[FeedbackEntry], category: str) -> str:
    for e in entries:
        if e.category == category and e.description:
            return e.description[:120]
    return ""


class CITestSuitUpdater:
    def __init__(
        self,
        curriculum_dir: str = "curriculum",
        feedback_archive_dir: str = "test_results/feedback_archive",
    ):
        self.curriculum_dir = Path(curriculum_dir)
        self.archive_dir = Path(feedback_archive_dir)

    async def promote_to_ci(self, feedback: FeedbackEntry) -> bool:
        if not feedback.pdf_stored_path:
            return False

        src = Path(feedback.pdf_stored_path)
        if not src.exists():
            return False

        self.curriculum_dir.mkdir(parents=True, exist_ok=True)
        dest = self.curriculum_dir / f"feedback_{feedback.feedback_id}_{feedback.pdf_name}"
        shutil.copy2(str(src), str(dest))

        baseline = await self.generate_baseline(str(dest))
        if baseline is None:
            pass

        collector = FeedbackCollector(storage_dir=str(self.archive_dir))
        entries = collector._entries()
        for e in entries:
            if e.feedback_id == feedback.feedback_id:
                e.status = "added_to_ci"
                break
        collector._persist(entries)
        return True

    async def generate_baseline(self, pdf_path: str) -> Optional[str]:
        p = Path(pdf_path)
        if not p.exists():
            return None
        out = p.with_suffix(".pptx")
        try:
            from subprocess import run as _run
            result = _run(
                ["python", "-m", "orchestrator", pdf_path, "-o", str(out)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0 and out.exists():
                return str(out)
        except Exception:
            pass
        return None

    async def get_pending_feedback(self) -> List[FeedbackEntry]:
        collector = FeedbackCollector(storage_dir=str(self.archive_dir))
        return await collector.list_feedback(status="new")


class FeedbackDashboard:
    BRAND_CANVAS = "#FAFAFA"
    BRAND_CHARCOAL = "#1A1A1A"
    BRAND_ACCENT = "#F5C518"

    def generate_html(self, stats: Dict[str, Any], entries: List[FeedbackEntry]) -> str:
        total = stats["total_count"]
        by_rating = stats["by_rating"]
        by_category = stats["by_category"]
        by_page = stats["by_page"]
        top_issues = stats.get("top_issues", [])

        max_cat = max(by_category.values()) if by_category else 1
        max_page = max(by_page.values()) if by_page else 1

        cat_bars = ""
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            pct = (count / max_cat) * 100 if max_cat else 0
            cat_bars += f"""
            <div class="bar-row">
              <span class="bar-label">{cat}</span>
              <div class="bar-track">
                <div class="bar-fill" style="width:{pct}%"></div>
              </div>
              <span class="bar-value">{count}</span>
            </div>"""

        page_bars = ""
        for pg, count in sorted(by_page.items(), key=lambda x: -x[1])[:15]:
            pct = (count / max_page) * 100 if max_page else 0
            page_bars += f"""
            <div class="bar-row">
              <span class="bar-label">Page {pg}</span>
              <div class="bar-track">
                <div class="bar-fill accent" style="width:{pct}%"></div>
              </div>
              <span class="bar-value">{count}</span>
            </div>"""

        rows = ""
        for e in reversed(entries[-50:]):
            badge_cls = {"good": "badge-good", "bad": "badge-bad", "partial": "badge-partial"}.get(e.rating, "")
            status_cls = f"status-{e.status}"
            rows += f"""
            <tr>
              <td>{e.feedback_id[:8]}</td>
              <td>{e.job_id[:8]}</td>
              <td><span class="badge {badge_cls}">{e.rating}</span></td>
              <td>{e.category}</td>
              <td class="desc">{_esc(e.description[:80])}</td>
              <td><span class="status {status_cls}">{e.status}</span></td>
              <td>{e.created_at[:10]}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Conversion Feedback Dashboard</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: {self.BRAND_CANVAS}; color: {self.BRAND_CHARCOAL};
    padding: 24px;
  }}
  h1 {{ font-size: 22px; margin-bottom: 20px; }}
  .cards {{ display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }}
  .card {{
    background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
    padding: 18px 24px; min-width: 140px; text-align: center;
  }}
  .card .num {{ font-size: 28px; font-weight: 700; }}
  .card .lbl {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .card.accent .num {{ color: {self.BRAND_ACCENT}; }}
  .section {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
              padding: 20px; margin-bottom: 20px; }}
  .section h2 {{ font-size: 15px; margin-bottom: 14px; }}
  .bar-row {{ display: flex; align-items: center; margin-bottom: 6px; }}
  .bar-label {{ width: 130px; font-size: 13px; text-align: right; padding-right: 10px; }}
  .bar-track {{ flex: 1; height: 18px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }}
  .bar-fill {{ height: 100%; background: {self.BRAND_CHARCOAL}; border-radius: 4px; transition: width .3s; }}
  .bar-fill.accent {{ background: {self.BRAND_ACCENT}; }}
  .bar-value {{ width: 40px; font-size: 13px; text-align: right; padding-left: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 10px; border-bottom: 2px solid #e0e0e0; font-weight: 600; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #f0f0f0; }}
  .desc {{ max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .badge {{ padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; color: #fff; }}
  .badge-good {{ background: #4caf50; }}
  .badge-bad {{ background: #e53935; }}
  .badge-partial {{ background: {self.BRAND_ACCENT}; color: {self.BRAND_CHARCOAL}; }}
  .status {{ padding: 2px 8px; border-radius: 10px; font-size: 11px; }}
  .status-new {{ background: #e3f2fd; color: #1565c0; }}
  .status-reviewing {{ background: #fff3e0; color: #e65100; }}
  .status-added_to_ci {{ background: #e8f5e9; color: #2e7d32; }}
  .status-dismissed {{ background: #f5f5f5; color: #757575; }}
</style>
</head>
<body>
<h1>Conversion Feedback Dashboard</h1>

<div class="cards">
  <div class="card"><div class="num">{total}</div><div class="lbl">Total Feedback</div></div>
  <div class="card accent"><div class="num">{by_rating.get("good", 0)}</div><div class="lbl">Good</div></div>
  <div class="card"><div class="num" style="color:#e53935">{by_rating.get("bad", 0)}</div><div class="lbl">Bad</div></div>
  <div class="card"><div class="num" style="color:#f9a825">{by_rating.get("partial", 0)}</div><div class="lbl">Partial</div></div>
</div>

<div style="display:flex; gap:20px; flex-wrap:wrap;">
  <div class="section" style="flex:1; min-width:320px;">
    <h2>Issues by Category</h2>
    {cat_bars if cat_bars else '<p style="color:#aaa;font-size:13px">No data yet.</p>'}
  </div>
  <div class="section" style="flex:1; min-width:320px;">
    <h2>Page Hotspot Map</h2>
    {page_bars if page_bars else '<p style="color:#aaa;font-size:13px">No page-specific issues reported.</p>'}
  </div>
</div>

<div class="section">
  <h2>Top Issues</h2>
  <table>
    <tr><th>Category</th><th>Count</th><th>Sample Description</th></tr>
    {"".join(f'<tr><td>{i["category"]}</td><td>{i["count"]}</td><td>{_esc(i["sample"])}</td></tr>' for i in top_issues) if top_issues else '<tr><td colspan="3" style="color:#aaa">No issues yet.</td></tr>'}
  </table>
</div>

<div class="section">
  <h2>Recent Feedback</h2>
  <table>
    <tr><th>ID</th><th>Job</th><th>Rating</th><th>Category</th><th>Description</th><th>Status</th><th>Date</th></tr>
    {rows if rows else '<tr><td colspan="7" style="color:#aaa">No feedback submitted yet.</td></tr>'}
  </table>
</div>
</body>
</html>"""
        return html


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


async def _demo() -> None:
    import asyncio

    collector = FeedbackCollector(storage_dir="test_results/feedback_archive")

    samples = [
        ("job-001", "good", "layout", "", []),
        ("job-002", "bad", "font", "All headings rendered in wrong font", [1, 3]),
        ("job-003", "partial", "missing_content", "Page 5 table was dropped", [5]),
        ("job-004", "bad", "color", "Background colors not preserved", [2]),
        ("job-005", "good", "other", "", []),
        ("job-006", "bad", "extra_content", "Header/footer duplicated on every slide", [1, 2, 3, 4]),
        ("job-007", "partial", "layout", "Two-column layout merged into one", [7]),
    ]

    for job_id, rating, cat, desc, pages in samples:
        await collector.submit_feedback(
            job_id=job_id,
            rating=rating,
            category=cat,
            description=desc,
            page_numbers=pages,
        )

    stats = await collector.get_feedback_stats()
    entries = await collector.list_feedback()

    dashboard = FeedbackDashboard()
    html = dashboard.generate_html(stats, entries)

    out = Path("test_results") / "feedback_dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {out.resolve()}")
    print(f"Stats: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_demo())
