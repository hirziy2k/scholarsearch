#!/usr/bin/env python3
"""
ci_gate.py — Local CI gate that mirrors GitHub Actions.

Run before pushing to ensure your changes pass the full curriculum.

Usage:
    python ci_gate.py
    python ci_gate.py --fast  # skip organic tests
"""

import subprocess
import sys
import json
import time
from pathlib import Path

def run_step(name: str, cmd: list, timeout: int = 300) -> bool:
    """Run a step, print result, return True if passed."""
    print(f"\n{'='*60}")
    print(f"  STEP: {name}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        if result.returncode != 0:
            if result.stderr:
                print(f"STDERR: {result.stderr[-1000:]}")
            print(f"FAILED (exit code {result.returncode})")
            return False
        print("PASSED")
        return True
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT ({timeout}s)")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    fast_mode = "--fast" in sys.argv
    print("CI GATE — PDF-to-PPTX Conversion Pipeline")
    print(f"Mode: {'FAST' if fast_mode else 'FULL'}")
    
    steps = [
        ("Phase 1 Coordinate Test", [sys.executable, "pdf_to_pptx.py", "--test-phase1"]),
        ("Generate Curriculum", [sys.executable, "generate_curriculum.py"]),
        ("Run 51-Document Curriculum", [sys.executable, "run_curriculum.py"], 600),
        ("Structural Audit", [sys.executable, "structural_audit.py"]),
    ]
    
    if not fast_mode:
        steps.extend([
            ("Organic Hostile Tests", [sys.executable, "run_organic_tests.py"], 600),
            ("Concurrency Stress Test", [sys.executable, "stress_test.py"], 600),
        ])
    
    results = {}
    for step in steps:
        name, cmd = step[0], step[1]
        timeout = step[2] if len(step) > 2 else 300
        results[name] = run_step(name, cmd, timeout)
    
    # Check structural audit score
    print(f"\n{'='*60}")
    print(f"  CHECKING STRUCTURAL AUDIT SCORE")
    print(f"{'='*60}")
    try:
        with open("test_results/results.json") as f:
            data = json.load(f)
        total = len(data.get("results", []))
        passed = sum(1 for r in data.get("results", []) if r.get("success"))
        score = passed / total * 100 if total > 0 else 0
        print(f"Score: {score:.1f}% (threshold: 99.7%)")
        if score < 99.7:
            results["Audit Score"] = False
            print("FAILED: Score below 99.7%")
        else:
            results["Audit Score"] = True
            print("PASSED")
    except Exception as e:
        print(f"Could not check audit score: {e}")
        results["Audit Score"] = False
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  CI GATE SUMMARY")
    print(f"{'='*60}")
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    
    failed = sum(1 for p in results.values() if not p)
    total = len(results)
    
    if failed == 0:
        print(f"\n  ALL {total} GATES PASSED — safe to merge")
        return 0
    else:
        print(f"\n  {failed}/{total} GATES FAILED — merge blocked")
        return 1

if __name__ == "__main__":
    sys.exit(main())
