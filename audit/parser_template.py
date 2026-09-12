#!/usr/bin/env python3
"""Deterministic parser template — human review gate, stdlib only.

Gate: refuses to run unless audit/APPROVED exists with reviewer initials + date.
Flow: LLM proposes -> `python -m ast` parse -> human review -> APPROVED -> run on allowlisted inputs only.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def require_approval():
    p = os.path.join(ROOT, "audit", "APPROVED")
    if not os.path.exists(p):
        raise SystemExit("HALT: audit/APPROVED missing (reviewer initials + date required). No corpus execution.")
    with open(p, encoding="utf-8") as f:
        txt = f.read().strip()
    if len(txt) < 3:
        raise SystemExit("HALT: APPROVED empty. Manual sign-off required.")

def validate_source(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)  # SyntaxError -> halt, no exec

if __name__ == "__main__":
    require_approval()
    print("gate passed (no extraction implemented in scaffold)")
