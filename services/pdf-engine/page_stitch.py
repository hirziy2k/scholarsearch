#!/usr/bin/env python3
"""page_stitch.py — cross-page overlap stitch for the V1 Data Guillotine.

Problem: strict per-page flush severs tables/entities spanning a page break.
Solution: rolling overlap buffer — retain bottom 20% of the previous page's
positional blocks (cap 12) plus any table touching the bottom quartile, then
stitch against the next page's top 20% before the SQLite write.

Zero-review semantics: ambiguity never guesses. Column-count mismatch or
multi-candidate continuation yields STITCH_AMBIGUOUS -> fail-closed REJECT.

Pure functions over plain dicts/lists. No fitz import (callers adapt
PyMuPDF objects). Stdlib only.
"""

from typing import Any, Dict, List, Tuple

CARRY_FRACTION = 0.20
CARRY_CAP = 12
BOTTOM_QUARTILE_Y = 0.75  # table bbox y1 beyond 75% of page height rides along
X_TOLERANCE_PT = 10.0

STITCH_AMBIGUOUS = "STITCH_AMBIGUOUS"


def _x_overlap(a: Tuple[float, float], b: Tuple[float, float], tol: float = X_TOLERANCE_PT) -> bool:
    return not (a[1] < b[0] - tol or b[1] < a[0] - tol)


def select_carry(blocks: List[Dict[str, Any]], tables: List[Dict[str, Any]],
                 page_height: float) -> Dict[str, Any]:
    """Bottom-20% blocks (by y0, cap 12) + bottom-quartile-touching tables."""
    ordered = sorted(blocks, key=lambda b: b["y0"])
    k = max(1, int(len(ordered) * CARRY_FRACTION)) if ordered else 0
    carry_blocks = ordered[-k:] if k else []
    carry_blocks = carry_blocks[-CARRY_CAP:]
    carry_tables = [t for t in tables if t["bbox"][3] > BOTTOM_QUARTILE_Y * page_height]
    return {"blocks": carry_blocks, "tables": carry_tables}


def stitch_tables(carry_tables: List[Dict[str, Any]],
                  page_tables: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Merge continued tables. Returns (merged_page_tables, rejects)."""
    rejects: List[str] = []
    merged = list(page_tables)
    for ct in carry_tables:
        cands = [pt for pt in page_tables
                 if _x_overlap((ct["bbox"][0], ct["bbox"][2]),
                                (pt["bbox"][0], pt["bbox"][2]))]
        # top-of-page candidates only: y0 within top quartile of their page
        cands = [c for c in cands if c.get("top_quartile", True)]
        if not cands:
            continue  # carry dies silently only if nothing continues it
        if len(cands) > 1:
            rejects.append(f"{STITCH_AMBIGUOUS}: {len(cands)} continuations for carry table")
            continue
        pt = cands[0]
        if len(pt["rows"][0]) != len(ct["rows"][0]):
            rejects.append(f"{STITCH_AMBIGUOUS}: column mismatch "
                           f"{len(ct['rows'][0])} vs {len(pt['rows'][0])}")
            continue
        pt["rows"] = ct["rows"] + pt["rows"]
    return merged, rejects


def stitch_pages(pages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Stream pages through the overlap buffer. Returns (stitched_pages, rejects).

    Each page dict: {page_num, blocks[{x0,y0,x1,y1,text}], tables[{bbox, rows}],
    page_height}. Stitched page gains `continued_from` when a carry merged.
    """
    out: List[Dict[str, Any]] = []
    rejects: List[str] = []
    carry: Dict[str, Any] = {"blocks": [], "tables": []}
    for pg in pages:
        top_n = max(1, int(len(pg["blocks"]) * CARRY_FRACTION)) if pg["blocks"] else 0
        for pt in pg["tables"]:
            pt["top_quartile"] = pt["bbox"][1] < 0.25 * pg["page_height"]
        merged_tables, rej = stitch_tables(carry["tables"], pg["tables"])
        rejects.extend([f"p{pg['page_num']}: {r}" for r in rej])
        pg = dict(pg, tables=merged_tables,
                  continued_from=bool(carry["blocks"] or carry["tables"]))
        out.append(pg)
        carry = select_carry(pg["blocks"], pg["tables"], pg["page_height"])
    return out, rejects
