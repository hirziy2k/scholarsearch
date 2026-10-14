#!/usr/bin/env python3
"""audit_verify.py — deterministic CI/gate check, stdlib only. No corpus execution.

Checks: gc.auto==0, allowlist paths exist, manifest validates fail-closed,
transient clone (if given) has isolated .git/config+hooks (not shared commonDir).
Exit 0 pass, exit 2 FAIL CLOSED.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sh(*a):
    return subprocess.run(a, cwd=ROOT, capture_output=True, text=True)

def main():
    errs = []
    r = sh("git", "config", "--get", "gc.auto")
    if r.stdout.strip() != "0":
        errs.append("gc.auto != 0 (alternates race open)")
    try:
        with open(os.path.join(ROOT, "audit", "inputs.allowlist.json"), encoding="utf-8") as f:
            allow = json.load(f)
        for p in allow.get("allowed_inputs", []):
            if not os.path.exists(os.path.join(ROOT, p)):
                errs.append(f"allowlisted input missing: {p}")
    except Exception as e:
        errs.append(f"allowlist unreadable: {e}")
    # manifest import + fail-closed smoke (missing fields must raise)
    sys.path.insert(0, os.path.join(ROOT, "audit"))
    try:
        from manifest import AuditManifest, validate_fail_closed
        try:
            validate_fail_closed(AuditManifest(run_id="", timestamp="", git_commit=""))
            errs.append("fail-closed broken: empty manifest passed")
        except ValueError:
            pass
    except Exception as e:
        errs.append(f"manifest import failed: {e}")
    # optional clone isolation check: argv[1] = clone path
    if len(sys.argv) > 1:
        clone = sys.argv[1]
        for sub in (".git/config", ".git/hooks"):
            if not os.path.exists(os.path.join(clone, sub)):
                errs.append(f"clone missing {sub}: not an isolated clone")
        alt = os.path.join(clone, ".git/objects/info/alternates")
        if not os.path.exists(alt):
            errs.append("clone missing alternates: not --shared as mandated")
    if errs:
        print("FAIL CLOSED:")
        for e in errs:
            print(f" - {e}")
        return 2
    print("AUDIT VERIFY: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
