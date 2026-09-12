#!/usr/bin/env python3
"""Delimiter-only corpus repair. Zero alphanumeric change. Fail-closed atomic.

Rule: data rows file-lines 17-28. Line 17 (26 cells): insert empty at idx 24.
Lines 18-28 (25 cells): insert empty at idx 17, then idx 24. Text-level insert
at escape-aware pipe offsets. Abort with NO WRITE unless all 12 rows verify
27 cells via parser_manual AND alphanumeric content is identical modulo
pipes/whitespace.
"""
import csv
import re
import sys

sys.path.insert(0, "audit")
from parser_manual import _strip_md_edges, parse_line  # noqa: E402

CORPUS = "scoping_review_benchmark_extraction_TABLE_FULL.md"
TARGETS = {17: [24], 18: [17, 24], 19: [17, 24], 20: [17, 24], 21: [17, 24],
           22: [17, 24], 23: [17, 24], 24: [17, 24], 25: [17, 24],
           26: [17, 24], 27: [17, 24], 28: [17, 24]}


def cell_count(line):
    return len(_strip_md_edges(
        next(csv.reader([line], delimiter="|", skipinitialspace=True,
                        escapechar=chr(92), strict=True))))


def insert_empty_cell(line, cell_idx):
    """Insert empty cell at 0-based cell index (edge-stripped coords).

    Row form: | c0 | ... | cN | (N+1 cells, N+2 pipes). Pipe k precedes
    cell k, so insert ' |' right after pipe k.
    """
    offs = [m.start() for m in re.finditer(r"(?<!\\)\|", line)]
    if len(offs) < cell_idx + 1:
        raise ValueError(f"pipe offset missing for idx {cell_idx}")
    at = offs[cell_idx] + 1
    return line[:at] + " |" + line[at:]


def alnum(s):
    return re.sub(r"[^0-9A-Za-z]", "", s)


def main():
    with open(CORPUS, encoding="utf-8") as f:
        lines = f.read().splitlines()
    new = list(lines)
    for lineno, idxs in TARGETS.items():
        orig = lines[lineno - 1]
        n0 = cell_count(orig)
        if n0 != 27 - len(idxs):
            raise SystemExit(
                f"F2 line {lineno}: has {n0}, expected {27 - len(idxs)}; abort, no write")
        line = orig
        for k in sorted(idxs):
            line = insert_empty_cell(line, k)
            # NOTE: indices chosen so sequential ascending application lands
            # correctly: idx 17 first, then 24 in post-insert coordinates.
            # For [24]-only rows this is a single insert. Verified below.
        d = parse_line(line)
        if len(d) != 27:
            raise SystemExit(f"F1 line {lineno}: got {len(d)}; abort, no write")
        if alnum(line) != alnum(orig):
            raise SystemExit(f"F4 line {lineno}: alphanumeric drift; abort, no write")
        new[lineno - 1] = line
    for lineno in TARGETS:
        parse_line(new[lineno - 1])
    with open(CORPUS, "w", encoding="utf-8") as f:
        f.write("\n".join(new) + "\n")
    print("REPAIR OK: 12 rows x 27 cells, alnum-identical")


if __name__ == "__main__":
    main()
