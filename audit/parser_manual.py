#!/usr/bin/env python3
"""Manual deterministic parser for TABLE_FULL v1.2 — stdlib only, csv-based.

Constraints honored: no .split('|'); csv.reader delimiter='|',
skipinitialspace=True, escapechar='\\', strict=True; declarative schema map;
no hardcoded row[i]; ValueError on malformed; mock-matrix only (no corpus run here).
"""
import csv

# Declarative schema map (Framework 1): header label -> stable key, order = file order.
SCHEMA = [
    ("Rank", "rank"),
    ("Citation", "citation"),
    ("Journal", "journal"),
    ("Topic", "topic"),
    ("P", "p"),
    ("C", "c"),
    ("Cxt", "cxt"),
    ("PCC explicit?", "pcc_explicit"),
    ("JBI?", "jbi"),
    ("PRISMA-ScR?", "prisma_scr"),
    ("Protocol/registration", "protocol_registration"),
    ("Databases + platforms", "databases_platforms"),
    ("Grey lit?", "grey_lit"),
    ("Citation chasing", "citation_chasing"),
    ("Date range", "date_range"),
    ("Controlled vocab", "controlled_vocab"),
    ("Full strings?", "full_strings"),
    ("Designs", "designs"),
    ("T/A screening", "ta_screening"),
    ("Full-text screening", "fulltext_screening"),
    ("Charting / pilot", "charting_pilot"),
    ("Synthesis", "synthesis"),
    ("PRISMA flow/checklist", "prisma_flow_checklist"),
    ("Search reporting", "search_reporting"),
    ("Tier", "tier"),
    ("Strengths", "strengths"),
    ("Limitations", "limitations"),
]
EXPECTED_N = len(SCHEMA)  # 27
KEYS = [k for _, k in SCHEMA]
# Positional null-allowance (amended): Designs=17, Tier=24 are legitimately
# uncharted in TABLE_FULL v1.2 (Tier judgments live in prose, not the table).
# Empty allowed ONLY here; all other positions keep the F1 tripwire.
# NOTE: authorization wrote [16,23]; corrected to [17,24] per measured header
# map (16:Full strings?, 23:Search reporting). Tests below prove placement.
NULLABLE = frozenset({17, 24})

def _strip_md_edges(cells: list) -> list:
    cells = [c.strip() for c in cells]
    while cells and cells[0] == "":
        cells.pop(0)
    while cells and cells[-1] == "":
        cells.pop()
    return cells

def parse_line(line: str) -> dict:
    """Parse one markdown table row -> structured dict. Raises ValueError."""
    if line is None or not line.strip():
        raise ValueError("empty row")
    reader = csv.reader(
        [line], delimiter="|", skipinitialspace=True,
        escapechar="\\", quoting=csv.QUOTE_MINIMAL, strict=True,
    )
    try:
        raw = next(reader)
    except csv.Error as e:
        raise ValueError(f"csv strict failure: {e}") from e
    cells = _strip_md_edges(raw)
    if len(cells) != EXPECTED_N:
        raise ValueError(f"expected {EXPECTED_N} cols, got {len(cells)}")
    for i, c in enumerate(cells):
        if c == "" and i not in NULLABLE:
            raise ValueError(f"empty cell in strict column {i}")
    if any(len(c) > 2000 for c in cells):
        raise ValueError("oversized cell")
    return dict(zip(KEYS, cells))

def parse_text(text: str) -> list:
    """Parse multi-line mock matrix (header + separator skipped)."""
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or set(s) <= set("|-: "):
            continue
        if s.lower().startswith("| rank"):
            continue
        out.append(parse_line(ln))
    return out

if __name__ == "__main__":
    raise SystemExit("import only; run audit/test_parser_manual.py for mock matrix")
