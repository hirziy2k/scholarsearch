#!/usr/bin/env python3
"""Validate session-state.json against the schema and print a report.

Usage:
  python validate_state.py                    # Full validation report
  python validate_state.py --json             # Machine-readable output
  python validate_state.py --check-compliance # Exit code 0 if valid, 1 if not
"""

import json
import sys
from pathlib import Path

STATE_FILE = Path(__file__).parent.parent / "session-state.json"


def validate(state):
    errors = []
    warnings = []
    metrics = {}

    # --- STRUCTURAL VALIDATION ---

    required_keys = {"current_objective", "modified_infrastructure", "active_blockers", "next_action_trigger", "meta"}
    actual_keys = set(state.keys())
    missing = required_keys - actual_keys
    extra = actual_keys - required_keys
    if missing:
        errors.append(f"Missing top-level keys: {missing}")
    if extra:
        warnings.append(f"Unexpected top-level keys: {extra}")

    # current_objective
    obj = state.get("current_objective")
    if obj is not None:
        if not isinstance(obj, str):
            errors.append("current_objective: must be string or null")
        else:
            words = len(obj.split())
            metrics["objective_words"] = words
            if words > 30:
                warnings.append(f"current_objective: {words} words (max 30)")
    else:
        warnings.append("current_objective: null — no active objective")

    # modified_infrastructure
    files = state.get("modified_infrastructure", [])
    if not isinstance(files, list):
        errors.append("modified_infrastructure: must be array")
    else:
        metrics["file_count"] = len(files)
        desc_words_list = []
        for i, entry in enumerate(files):
            if not isinstance(entry, dict):
                errors.append(f"modified_infrastructure[{i}]: must be object")
                continue
            if "path" not in entry:
                errors.append(f"modified_infrastructure[{i}]: missing 'path'")
            if "change_description" not in entry:
                errors.append(f"modified_infrastructure[{i}]: missing 'change_description'")
            else:
                desc_words = len(entry["change_description"].split())
                desc_words_list.append(desc_words)
                if desc_words > 12:
                    warnings.append(
                        f"modified_infrastructure[{i}].change_description: "
                        f"{desc_words} words (max 12)"
                    )
            if "last_edit" not in entry:
                warnings.append(f"modified_infrastructure[{i}]: missing 'last_edit'")

        if desc_words_list:
            metrics["avg_description_words"] = round(
                sum(desc_words_list) / len(desc_words_list), 1
            )

        if len(files) > 20:
            warnings.append(f"modified_infrastructure: {len(files)} entries (max 20)")

    # active_blockers
    blockers = state.get("active_blockers", [])
    if not isinstance(blockers, list):
        errors.append("active_blockers: must be array")
    else:
        metrics["blocker_count"] = len(blockers)
        for i, b in enumerate(blockers):
            if not isinstance(b, str):
                errors.append(f"active_blockers[{i}]: must be string")
        if len(blockers) > 5:
            warnings.append(f"active_blockers: {len(blockers)} entries (max 5)")

    # next_action_trigger
    nxt = state.get("next_action_trigger")
    if nxt is not None:
        if not isinstance(nxt, str):
            errors.append("next_action_trigger: must be string or null")
        else:
            words = len(nxt.split())
            metrics["next_action_words"] = words
            if words > 20:
                warnings.append(f"next_action_trigger: {words} words (max 20)")
    else:
        warnings.append("next_action_trigger: null — no resume action defined")

    # meta
    meta = state.get("meta", {})
    if not isinstance(meta, dict):
        errors.append("meta: must be object")
    else:
        if "schema_version" not in meta:
            errors.append("meta: missing 'schema_version'")
        if "session_count" not in meta:
            warnings.append("meta: missing 'session_count'")
        if "total_tokens_saved" not in meta:
            warnings.append("meta: missing 'total_tokens_saved'")
        metrics["session_count"] = meta.get("session_count", 0)
        metrics["total_tokens_saved"] = meta.get("total_tokens_saved", 0)

    # --- TOKEN BUDGET ---
    blob = json.dumps(state, ensure_ascii=False)
    token_estimate = len(blob) // 4
    metrics["estimated_tokens"] = token_estimate

    if token_estimate > 500:
        warnings.append(f"Token budget: ~{token_estimate} tokens (target: <200)")
    elif token_estimate > 200:
        warnings.append(f"Token budget: ~{token_estimate} tokens (soft target: <200)")

    return errors, warnings, metrics


def main():
    if not STATE_FILE.exists():
        print(f"ERROR: {STATE_FILE} not found")
        sys.exit(1)

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    errors, warnings, metrics = validate(state)
    json_mode = "--json" in sys.argv
    compliance_mode = "--check-compliance" in sys.argv

    if json_mode:
        print(json.dumps({
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }, indent=2))
    elif compliance_mode:
        if errors:
            print(f"FAIL: {len(errors)} error(s)")
            for e in errors:
                print(f"  [ERR] {e}")
            sys.exit(1)
        print("PASS")
        sys.exit(0)
    else:
        print("=== Session State Validation Report ===\n")
        print(f"Objective: {state.get('current_objective') or '(none)'}")
        print(f"Files tracked: {metrics.get('file_count', 0)}")
        print(f"Active blockers: {metrics.get('blocker_count', 0)}")
        print(f"Session count: {metrics.get('session_count', 0)}")
        print(f"Estimated tokens: ~{metrics.get('estimated_tokens', 0)}")
        print(f"Tokens saved historically: ~{metrics.get('total_tokens_saved', 0)}")

        if errors:
            print(f"\nERRORS ({len(errors)}):")
            for e in errors:
                print(f"  [ERR] {e}")
        if warnings:
            print(f"\nWARNINGS ({len(warnings)}):")
            for w in warnings:
                print(f"  [WARN] {w}")
        if not errors and not warnings:
            print("\nOK State is fully compliant")

        print(f"\nVerdict: {'PASS' if not errors else 'FAIL'}")


if __name__ == "__main__":
    main()
