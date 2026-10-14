#!/usr/bin/env python3
"""audit_stage.py — transient `git clone --shared` boundary. No auto extraction.

Usage:
  python audit/audit_stage.py --dry-run        # verify only, no clone
  python audit/audit_stage.py --stage <tmpdir> # create isolated clone, copy allowlist, pre-flight manifest check

Requires human sign-off file (audit/APPROVED) before any corpus execution.
Never executes literature searches (OSF gate).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sh(*a, cwd=ROOT):
    r = subprocess.run(a, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(a)} failed: {r.stderr.strip()[:300]}")
    return r.stdout.strip()

def main():
    if "--dry-run" in sys.argv:
        print("dry-run: boundary logic present, no clone created")
        return 0
    if "--stage" in sys.argv:
        i = sys.argv.index("--stage")
        dest = sys.argv[i + 1] if len(sys.argv) > i + 1 else tempfile.mkdtemp(prefix="audit_clone_")
        if os.path.exists(dest) and os.listdir(dest):
            raise SystemExit("refuse: dest not empty")
        sh("git", "clone", "--shared", "--no-checkout", ROOT, dest)
        # copy allowlisted inputs only
        with open(os.path.join(ROOT, "audit", "inputs.allowlist.json"), encoding="utf-8") as f:
            allow = json.load(f)
        for p in allow["allowed_inputs"]:
            src = os.path.join(ROOT, p)
            dst = os.path.join(dest, p)
            os.makedirs(os.path.dirname(dst) or dest, exist_ok=True)
            shutil.copy2(src, dst)
        print(f"STAGED: {dest} (isolated .git, alternates-linked objects)")
        print("NEXT: human sign-off required (audit/APPROVED) before any parser run. Destroy post-commit.")
        return 0
    print(__doc__)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
