#!/usr/bin/env python3
"""One-off structural diagnosis: numbered header vs row cells. Read-only."""
import csv
import sys

sys.path.insert(0, "audit")
from parser_manual import _strip_md_edges

lines = open(
    "scoping_review_benchmark_extraction_TABLE_FULL.md", encoding="utf-8"
).read().splitlines()


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


which = sys.argv[1] if len(sys.argv) > 1 else "header"
if which == "header":
    h = [x for x in lines if x.strip().lower().startswith("| rank")][0]
    for i, c in enumerate(cells(h)):
        print(f"{i}:{c[:44]}")
else:
    n = int(which)
    rows = [
        x
        for x in lines
        if x.strip().startswith("|")
        and not set(x.strip()) <= set("|-: ")
        and not x.strip().lower().startswith("| rank")
    ]
    target = rows[n]
    for i, c in enumerate(cells(target)):
        print(f"{i}:{c[:44]}")
