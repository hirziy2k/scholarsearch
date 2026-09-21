#!/usr/bin/env python3
"""strict_stage.py — Phase 4.8: behavioral enforcement gate for the orchestrator.

Connects conversion output to the locked candidate_config (100x asymmetric
floors) and emits the Rejection Ledger: every candidate field gets an
explicit verdict — PASS | QUARANTINE_VALID | REJECT:<code> — never silence.
Upstream senders read exact reason codes (TRUNCATION_BOUNDARY,
SUSPECT_FONT_ENCODING, ...) instead of void. Doc-level strict_status:
ALL_PASS | PARTIAL (some rejects) | ALL_REJECT | NO_CANDIDATES.
"""

import json
import os
from functools import partial
from pathlib import Path
from typing import Any, Dict, List

from pdf_meta import (build_meta, ocr_field, continuation_ink, probe_end,
                      find_columns, column_limit, find_grid_cells, grid_cap,
                      void_check)
from field_validation import validate_field, _locate_run, _locate_best_window, _line_reach
from scaffold import chunk

TYPE_MAP = {"amount": "amount", "account_id": "account_id",
            "proper_noun": "proper_noun", "date": "date"}

CONFIG_PATH = Path(__file__).parent / "candidate_config.locked.json"


def load_locked_config() -> Dict[str, Any]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return cfg["config"]


def _verdict(ok: bool, reason: str) -> str:
    if not ok:
        return "REJECT"
    return "QUARANTINE_VALID" if "hull:COMPROMISED" in reason else "PASS"


def run_strict_stage(pdf_path: str, max_fields_per_page: int = 12,
                     max_pages: int = 0) -> Dict[str, Any]:
    """Execute strict gates over scaffold candidates. Returns ledger dict."""
    import fitz
    cfg = load_locked_config()
    ink_floor = float(cfg.get("ink_ratio_floor", 0.02))
    ledger: List[Dict[str, Any]] = []
    if os.name == "nt" and len(pdf_path) > 240 and not pdf_path.startswith("\\\\?\\"):
        pdf_path = "\\\\?\\" + os.path.abspath(pdf_path)
    doc = fitz.open(pdf_path)
    try:
        pages = range(len(doc)) if not max_pages else range(min(len(doc), max_pages))
        for pno in pages:
            pg = doc[pno]
            spans, fonts, words = build_meta(pg, doc)
            src = pg.get_text()
            cols = find_columns(words, pg.rect.width, pg.rect.height)
            grid = find_grid_cells(pg, words)

            def inkfn(rb, reach, _pg=pg, _wo=words, _co=cols, _gr=grid):
                end = probe_end(_wo, _co, rb, reach)
                gc = grid_cap(_gr, rb)
                if gc is not None:
                    end = min(end, gc)
                lim = column_limit(_co, rb)
                return continuation_ink(_pg, rb, reach, ink_ratio_floor=ink_floor,
                                        x_limit=lim, x_end=end)

            def ocrfn(bb, psm=None, dpi=300, _pg=pg):
                return ocr_field(_pg, bb, psm=psm if psm else 6, dpi=dpi)

            def voidfn(bb, _pg=pg, _wo=words):
                return void_check(_pg, bb, words=_wo)

            for c in chunk(src)[:max_fields_per_page]:
                fld = {"type": TYPE_MAP.get(c["type"], "verbatim"),
                       "name": f"{c['type']}:{c['text'][:24]}"}
                value = c["text"]
                try:
                    ok, reason = validate_field(
                        fld, value, src, spans, fonts, words, True,
                        ocr_fn=partial(ocrfn), ink_fn=inkfn, void_fn=voidfn)
                except Exception as e:  # noqa: BLE001 — a crashing gate is a verdict, not silence
                    ok, reason = False, f"REJECT:GATE-CRASH:{type(e).__name__}"
                ledger.append({"page": pno + 1, "field": fld["name"], "value": value,
                               "verdict": _verdict(ok, reason), "reason": reason})
    finally:
        doc.close()
    n_pass = sum(1 for r in ledger if r["verdict"] == "PASS")
    n_quar = sum(1 for r in ledger if r["verdict"] == "QUARANTINE_VALID")
    n_rej = sum(1 for r in ledger if r["verdict"] == "REJECT")
    status = "NO_CANDIDATES" if not ledger else (
        "ALL_PASS" if n_rej == 0 and n_quar == 0 else (
            "ALL_REJECT" if n_pass == 0 and n_quar == 0 else "PARTIAL"))
    codes: Dict[str, int] = {}
    for r in ledger:
        if r["verdict"] == "REJECT":
            codes[r["reason"][:64]] = codes.get(r["reason"][:64], 0) + 1
    return {"ledger": ledger,
            "summary": {"n": len(ledger), "pass": n_pass, "quarantine": n_quar,
                        "reject": n_rej, "strict_status": status,
                        "floors": {"ink_ratio_floor": ink_floor,
                                   "ssim_floor": cfg.get("ssim_floor")},
                        "top_codes": sorted(codes.items(), key=lambda kv: -kv[1])[:8]}}
