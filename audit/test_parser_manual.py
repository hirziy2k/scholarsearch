#!/usr/bin/env python3
"""Mock-matrix unit tests — 5 fabricated edge cases, no corpus, no network."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from parser_manual import parse_line, EXPECTED_N

def row(cells):
    return "| " + " | ".join(cells) + " |"

def base():
    return [f"C{i}" for i in range(1, EXPECTED_N + 1)]

fails = 0
def expect_valueerror(name, line):
    global fails
    try:
        parse_line(line)
        print(f"FAIL {name}: no ValueError")
        fails += 1
    except ValueError:
        print(f"PASS {name}")

# valid control (not counted in 5)
d = parse_line(row(base()))
assert len(d) == EXPECTED_N, "valid control column count"
print("PASS valid-control")

# exactly 5 edge cases
b = base()
expect_valueerror("missing-cols", row(b[:20]))                       # 1
c = base(); c[5] = ""
expect_valueerror("empty-cell", row(c))                              # 2
e = base(); e[3] = "X" * 2001
expect_valueerror("oversized-cell", row(e))                          # 3
expect_valueerror("empty-row", "   ")                                # 4
expect_valueerror("bad-csv-quote", '| "unclosed | ' + " | ".join(b[1:]) + " |")  # 5

# amendment: positional null-allowance at Designs=17, Tier=24
def expect_pass(name, line, check_idx, check_val=""):
    global fails
    try:
        d = parse_line(line)
        assert d[check_idx] == check_val, f"{name}: wrong value at {check_idx}"
        print(f"PASS {name}")
    except Exception as e:
        print(f"FAIL {name}: {e}")
        fails += 1

from parser_manual import KEYS
n = base(); n[17] = ""
expect_pass("empty-designs-17-passes", row(n), KEYS[17])
t = base(); t[24] = ""
expect_pass("empty-tier-24-passes", row(t), KEYS[24])
q = base(); q[16] = ""
expect_valueerror("empty-fullstrings-16-fails", row(q))
w = base(); w[23] = ""
expect_valueerror("empty-searchrep-23-fails", row(w))

sys.exit(1 if fails else 0)
