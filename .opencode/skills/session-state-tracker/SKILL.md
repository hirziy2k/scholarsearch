---
name: session-state-tracker
description: Use at the END of every major task loop to serialize session progress into a compressed relational ledger. Prevents context amnesia across sessions by tracking objectives, modified files, active blockers, and next actions. Read this file at session START to resume work without re-discovering architecture.
---

# Session State Tracker

## Purpose

Cures context amnesia by treating session history as a relational dataset, not a raw conversational log. Every major task boundary triggers a state serialization that compresses 10,000+ tokens of context into a ~200-token JSON ledger.

## Core File

| File | Purpose |
|------|---------|
| `.opencode/session-state.json` | Compressed session state ledger |

## Schema

```json
{
  "current_objective": "string — the overarching goal anchoring all work",
  "modified_infrastructure": [
    {
      "path": "relative/path/to/file",
      "last_edit": "ISO 8601 timestamp",
      "change_description": "exact logic changed, not vague summary"
    }
  ],
  "active_blockers": [
    "string — unhandled exception, failed test, or dependency conflict"
  ],
  "next_action_trigger": "string — single-step executable command for session resume",
  "meta": {
    "schema_version": "1.0.0",
    "last_updated": "ISO 8601 timestamp",
    "session_count": "integer — incremented on each resume",
    "total_tokens_saved": "integer — estimated tokens saved via compression"
  }
}
```

## Field Definitions

### `current_objective`
- **Type:** String or null
- **Purpose:** The single overarching goal. Acts as an anchor to prevent drift during complex refactors.
- **Example:** `"Implement OAuth2 authentication for the /settings route"`
- **Rule:** Must be a single, specific sentence. No multi-paragraph descriptions.

### `modified_infrastructure`
- **Type:** Array of objects
- **Purpose:** Tracks every file touched during the session with the exact change made.
- **Each object:**
  - `path`: Relative to project root (e.g., `services/pdf-engine/orchestrator.py`)
  - `last_edit`: ISO 8601 timestamp of last modification
  - `change_description`: MUST describe the exact logic changed, not just "updated"
- **Good example:** `"Added rate limiting middleware to POST /api/execute endpoint"`
- **Bad example:** `"Updated file"`

### `active_blockers`
- **Type:** Array of strings
- **Purpose:** Anything that halted execution. Must be specific enough to resume from.
- **Good example:** `"ImportError: parallel_dispatch module not found in .opencode/"`
- **Bad example:** `"Something broke"`

### `next_action_trigger`
- **Type:** String or null
- **Purpose:** The immediate, single-step command to execute upon session resume.
- **Example:** `"Run python -m pytest tests/test_auth.py to verify the middleware"`
- **Rule:** Must be an executable command or a specific question to answer. Never a vague directive.

## Triggers

### When to UPDATE state (write):
1. **After completing a major task** (not after every tool call)
2. **When a blocker is discovered** that halts progress
3. **When the objective changes** (scope shift detected)
4. **At natural session breaks** (user goes idle, task finished)

### When to READ state (load):
1. **At session start** — before any other action
2. **When the user says "continue" or "resume"**
3. **When switching between unrelated tasks** in the same session
4. **After a context compaction** event

## Execution Protocol

### Session Start (Read)
```
1. Read .opencode/session-state.json
2. Parse current_objective — this is your anchor
3. Check active_blockers — resolve these before new work
4. Execute next_action_trigger — this is your first move
5. Do NOT re-read files already in modified_infrastructure unless explicitly asked
```

### Task Completion (Write)
```
1. Identify what changed: files modified, logic altered, new dependencies
2. Identify what broke: errors, test failures, blockers
3. Identify what's next: the immediate next step
4. Update modified_infrastructure: add/modify entries for changed files
5. Update active_blockers: add new blockers, remove resolved ones
6. Update next_action_trigger: set the resume command
7. Update meta.last_updated: current timestamp
8. Write .opencode/session-state.json
```

### Compression Rules
- **modified_infrastructure**: Only include files changed in THIS session. Remove entries older than 3 sessions unless they contain unresolved blockers.
- **change_description**: Max 12 words. If you can't describe it in 12 words, the change is too large — split it.
- **active_blockers**: Max 5 entries. If you have more than 5 blockers, you have a structural problem — stop and reassess.
- **next_action_trigger**: Max 1 command. If you need multiple steps, pick the FIRST one only.

## Token Budget

| Component | Max Tokens | Notes |
|-----------|------------|-------|
| current_objective | 30 | One sentence |
| modified_infrastructure (per entry) | 40 | path + description |
| active_blockers (per entry) | 25 | Specific error |
| next_action_trigger | 20 | One command |
| meta | 15 | Timestamps only |
| **Total** | **~200** | **vs 10,000+ raw context** |

## Example State

```json
{
  "current_objective": "Add OAuth2 authentication to the /settings route",
  "modified_infrastructure": [
    {
      "path": "services/scholarsearch/server/routes/settings.ts",
      "last_edit": "2026-09-01T07:30:00Z",
      "change_description": "Added passport.js middleware to POST handler"
    },
    {
      "path": "services/scholarsearch/package.json",
      "last_edit": "2026-09-01T07:25:00Z",
      "change_description": "Added passport and passport-oauth2 dependencies"
    }
  ],
  "active_blockers": [
    "TypeError: Cannot read property 'accessToken' of undefined in OAuth2 callback"
  ],
  "next_action_trigger": "Check the OAuth2 callback URL configuration in the provider settings",
  "meta": {
    "schema_version": "1.0.0",
    "last_updated": "2026-09-01T07:32:00Z",
    "session_count": 1,
    "total_tokens_saved": 9800
  }
}
```

## Integration with Other Skills

- **unified-engine-architecture**: When working on orchestrate.py, update state after each pipeline step
- **day2-operations**: When managing operational safeguards, track shadow test results and lockdown state
- **pdf2pptx-architecture**: When modifying the PDF pipeline, track phase changes and validation results
- **scholarsearch-architecture**: When editing ScholarSearch, track API changes and database migrations

## Anti-Patterns

1. **Don't** update state after every tool call — only at task boundaries
2. **Don't** write vague descriptions — if you can't be specific, the change isn't understood
3. **Don't** leave stale blockers — if you fixed it, remove it
4. **Don't** set multiple next actions — only the FIRST step goes here
5. **Don't** store raw conversation history — this is a delta ledger, not a log
