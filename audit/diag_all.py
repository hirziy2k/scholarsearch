#!/usr/bin/env python3
"""One-off corpus diagnosis -> audit/corpus_diagnosis.md. Read-only on corpus."""
import csv
import sys

sys.path.insert(0, "audit")
from parser_manual import _strip_md_edges  # noqa: E402

CORPUS = "scoping_review_benchmark_extraction_TABLE_FULL.md"
HEADER_LABELS = [
    "Rank", "Citation", "Journal", "Topic", "P", "C", "Cxt",
    "PCC explicit?", "JBI?", "PRISMA-ScR?", "Protocol/registration",
    "Databases + platforms", "Grey lit?", "Citation chasing",
    "Date range", "Controlled vocab", "Full strings?", "Designs",
    "T/A screening", "Full-text screening", "Charting / pilot",
    "Synthesis", "PRISMA flow/checklist", "Search reporting", "Tier",
    "Strengths", "Limitations",
]


def cells(line):
    return _strip_md_edges(
        next(
            csv.reader(
                [line],
                delimiter="|",
                skipinitialspace=True,
                escapechar=chr(92),
                strict=True,
            )
        )
    )


lines = open(CORPUS, encoding="utf-8").read().splitlines()
hdr = [x for x in lines if x.strip().lower().startswith("| rank")][0]
assert len(cells(hdr)) == 27, "header assumption broken"
rows = [
    (i + 1, x)
    for i, x in enumerate(lines)
    if x.strip().startswith("|")
    and not set(x.strip()) <= set("|-: ")
    and not x.strip().lower().startswith("| rank")
]
out = ["# Corpus diagnosis (FACT + INFERENCE, read-only)", "",
       f"Header cells: 27. Data rows: {len(rows)}.", ""]
for lineno, line in rows:
    cs = cells(line)
    out.append(f"## File line {lineno}: {len(cs)} cells (missing {27 - len(cs)})")
    for i, c in enumerate(cs[17:], start=17):
        out.append(f"- pos{i} [{HEADER_LABELS[i]}?]: {c[:60]}")
    out.append("")
open("audit/corpus_diagnosis.md", "w", encoding="utf-8").write("\n".join(out))
print(f"rows={len(rows)} written audit/corpus_diagnosis.md")
