#!/usr/bin/env python3
"""Session State Tracker — validates and manages .opencode/session-state.json.

Usage:
  python state_tracker.py read                    # Print current state
  python state_tracker.py validate                # Validate schema compliance
  python state_tracker.py update --objective "..." # Set objective
  python state_tracker.py add-file <path> <desc>  # Add modified file
  python state_tracker.py add-blocker <message>   # Add active blocker
  python state_tracker.py resolve-blocker <index> # Remove blocker by index
  python state_tracker.py set-next <command>      # Set next action trigger
  python state_tracker.py compress                # Remove stale entries, enforce limits
  python state_tracker.py reset                   # Reset to empty state
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(__file__).parent.parent / "session-state.json"

SCHEMA = {
    "current_objective": (str, type(None)),
    "modified_infrastructure": list,
    "active_blockers": list,
    "next_action_trigger": (str, type(None)),
    "meta": dict,
}

MAX_MODIFIED_ENTRIES = 20
MAX_BLOCKERS = 5
MAX_DESCRIPTION_WORDS = 12
MAX_SESSIONS_BEFORE_CLEANUP = 3


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_state():
    if not STATE_FILE.exists():
        return create_empty_state()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    state["meta"]["last_updated"] = now_iso()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"State saved to {STATE_FILE}")


def create_empty_state():
    return {
        "current_objective": None,
        "modified_infrastructure": [],
        "active_blockers": [],
        "next_action_trigger": None,
        "meta": {
            "schema_version": "1.0.0",
            "last_updated": now_iso(),
            "session_count": 0,
            "total_tokens_saved": 0,
        },
    }


def validate_state(state):
    errors = []
    warnings = []

    # Check top-level keys
    expected_keys = set(SCHEMA.keys())
    actual_keys = set(state.keys())
    if expected_keys != actual_keys:
        errors.append(f"Top-level keys mismatch: missing {expected_keys - actual_keys}, extra {actual_keys - expected_keys}")

    # Validate current_objective
    obj = state.get("current_objective")
    if obj is not None:
        if not isinstance(obj, str):
            errors.append("current_objective must be string or null")
        elif len(obj.split()) > 30:
            warnings.append(f"current_objective is {len(obj.split())} words — aim for <=30")

    # Validate modified_infrastructure
    files = state.get("modified_infrastructure", [])
    if not isinstance(files, list):
        errors.append("modified_infrastructure must be array")
    else:
        for i, entry in enumerate(files):
            if not isinstance(entry, dict):
                errors.append(f"modified_infrastructure[{i}] must be object")
                continue
            if "path" not in entry:
                errors.append(f"modified_infrastructure[{i}] missing 'path'")
            if "change_description" not in entry:
                errors.append(f"modified_infrastructure[{i}] missing 'change_description'")
            elif len(entry["change_description"].split()) > MAX_DESCRIPTION_WORDS:
                warnings.append(
                    f"modified_infrastructure[{i}].change_description is "
                    f"{len(entry['change_description'].split())} words — max {MAX_DESCRIPTION_WORDS}"
                )
            if "last_edit" not in entry:
                warnings.append(f"modified_infrastructure[{i}] missing 'last_edit' timestamp")

        if len(files) > MAX_MODIFIED_ENTRIES:
            warnings.append(f"modified_infrastructure has {len(files)} entries — max {MAX_MODIFIED_ENTRIES}")

    # Validate active_blockers
    blockers = state.get("active_blockers", [])
    if not isinstance(blockers, list):
        errors.append("active_blockers must be array")
    else:
        for i, b in enumerate(blockers):
            if not isinstance(b, str):
                errors.append(f"active_blockers[{i}] must be string")
        if len(blockers) > MAX_BLOCKERS:
            warnings.append(f"active_blockers has {len(blockers)} entries — max {MAX_BLOCKERS}")

    # Validate next_action_trigger
    nxt = state.get("next_action_trigger")
    if nxt is not None:
        if not isinstance(nxt, str):
            errors.append("next_action_trigger must be string or null")
        elif len(nxt.split()) > 20:
            warnings.append(f"next_action_trigger is {len(nxt.split())} words — aim for <=20")

    # Validate meta
    meta = state.get("meta", {})
    if not isinstance(meta, dict):
        errors.append("meta must be object")
    else:
        if "schema_version" not in meta:
            errors.append("meta missing 'schema_version'")
        if "last_updated" not in meta:
            warnings.append("meta missing 'last_updated'")
        if "session_count" not in meta:
            warnings.append("meta missing 'session_count'")

    return errors, warnings


def estimate_tokens(state):
    """Rough token estimate (1 token ≈ 4 chars)."""
    blob = json.dumps(state, ensure_ascii=False)
    return len(blob) // 4


def cmd_read():
    state = load_state()
    print(json.dumps(state, indent=2, ensure_ascii=False))
    tokens = estimate_tokens(state)
    print(f"\nEstimated token cost: ~{tokens} tokens")


def cmd_validate():
    state = load_state()
    errors, warnings = validate_state(state)
    tokens = estimate_tokens(state)

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  X {e}")
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ! {w}")
    if not errors and not warnings:
        print("OK State is valid")

    print(f"\nEstimated token cost: ~{tokens} tokens")
    print(f"Entries: {len(state.get('modified_infrastructure', []))} files, "
          f"{len(state.get('active_blockers', []))} blockers")


def cmd_update_objective(obj):
    state = load_state()
    state["current_objective"] = obj
    save_state(state)
    print(f"Objective set: {obj}")


def cmd_add_file(path, desc):
    state = load_state()
    entry = {
        "path": path,
        "last_edit": now_iso(),
        "change_description": desc,
    }
    state["modified_infrastructure"].append(entry)
    save_state(state)
    print(f"Added file: {path}")


def cmd_add_blocker(message):
    state = load_state()
    if len(state["active_blockers"]) >= MAX_BLOCKERS:
        print(f"ERROR: Max {MAX_BLOCKERS} blockers. Resolve some first.")
        sys.exit(1)
    state["active_blockers"].append(message)
    save_state(state)
    print(f"Added blocker: {message}")


def cmd_resolve_blocker(index):
    state = load_state()
    if index < 0 or index >= len(state["active_blockers"]):
        print(f"ERROR: No blocker at index {index}")
        sys.exit(1)
    removed = state["active_blockers"].pop(index)
    save_state(state)
    print(f"Resolved blocker: {removed}")


def cmd_set_next(command):
    state = load_state()
    state["next_action_trigger"] = command
    save_state(state)
    print(f"Next action set: {command}")


def cmd_compress():
    state = load_state()
    initial_files = len(state["modified_infrastructure"])
    initial_tokens = estimate_tokens(state)

    # Remove entries older than 3 sessions (rough: entries without recent timestamps)
    cutoff_sessions = state["meta"].get("session_count", 0) - MAX_SESSIONS_BEFORE_CLEANUP
    if cutoff_sessions > 0:
        state["modified_infrastructure"] = [
            e for e in state["modified_infrastructure"]
            if e.get("session_added", state["meta"].get("session_count", 0)) >= cutoff_sessions
        ]

    # Enforce limits
    state["modified_infrastructure"] = state["modified_infrastructure"][-MAX_MODIFIED_ENTRIES:]
    state["active_blockers"] = state["active_blockers"][-MAX_BLOCKERS:]

    # Truncate descriptions
    for entry in state["modified_infrastructure"]:
        words = entry.get("change_description", "").split()
        if len(words) > MAX_DESCRIPTION_WORDS:
            entry["change_description"] = " ".join(words[:MAX_DESCRIPTION_WORDS]) + "..."

    # Truncate next_action
    nxt = state.get("next_action_trigger")
    if nxt:
        words = nxt.split()
        if len(words) > 20:
            state["next_action_trigger"] = " ".join(words[:20]) + "..."

    final_files = len(state["modified_infrastructure"])
    final_tokens = estimate_tokens(state)
    saved = initial_tokens - final_tokens

    state["meta"]["total_tokens_saved"] = state["meta"].get("total_tokens_saved", 0) + saved
    save_state(state)

    print(f"Compressed: {initial_files} -> {final_files} files")
    print(f"Tokens saved this compress: ~{saved}")
    print(f"Total tokens saved: ~{state['meta']['total_tokens_saved']}")


def cmd_reset():
    state = create_empty_state()
    save_state(state)
    print("State reset to empty")


def cmd_session_start():
    """Increment session count and print resume instructions."""
    state = load_state()
    state["meta"]["session_count"] = state["meta"].get("session_count", 0) + 1
    save_state(state)

    print(f"=== Session #{state['meta']['session_count']} ===")
    if state["current_objective"]:
        print(f"\nObjective: {state['current_objective']}")
    if state["active_blockers"]:
        print(f"\nActive blockers:")
        for i, b in enumerate(state["active_blockers"]):
            print(f"  [{i}] {b}")
    if state["next_action_trigger"]:
        print(f"\nNext action: {state['next_action_trigger']}")
    if state["modified_infrastructure"]:
        print(f"\nModified files ({len(state['modified_infrastructure'])}):")
        for e in state["modified_infrastructure"][-5:]:  # Last 5
            print(f"  {e['path']}: {e['change_description']}")
    tokens = estimate_tokens(state)
    print(f"\nContext cost: ~{tokens} tokens (vs ~10000+ raw)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "read":
        cmd_read()
    elif cmd == "validate":
        cmd_validate()
    elif cmd == "update":
        if "--objective" not in sys.argv:
            print("Usage: state_tracker.py update --objective \"...\"")
            sys.exit(1)
        idx = sys.argv.index("--objective")
        obj = " ".join(sys.argv[idx + 1:])
        cmd_update_objective(obj)
    elif cmd == "add-file":
        if len(sys.argv) < 4:
            print("Usage: state_tracker.py add-file <path> <description>")
            sys.exit(1)
        cmd_add_file(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "add-blocker":
        if len(sys.argv) < 3:
            print("Usage: state_tracker.py add-blocker <message>")
            sys.exit(1)
        cmd_add_blocker(" ".join(sys.argv[2:]))
    elif cmd == "resolve-blocker":
        if len(sys.argv) < 3:
            print("Usage: state_tracker.py resolve-blocker <index>")
            sys.exit(1)
        cmd_resolve_blocker(int(sys.argv[2]))
    elif cmd == "set-next":
        if len(sys.argv) < 3:
            print("Usage: state_tracker.py set-next <command>")
            sys.exit(1)
        cmd_set_next(" ".join(sys.argv[2:]))
    elif cmd == "compress":
        cmd_compress()
    elif cmd == "reset":
        cmd_reset()
    elif cmd == "session-start":
        cmd_session_start()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
