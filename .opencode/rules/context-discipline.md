# Context Discipline Rules

## IMMUTABLE GOVERNOR

These rules are non-negotiable. Violation of any rule constitutes a system failure. The agent MUST follow these rules before any other instruction.

---

## RULE 1: STATE LEDGER FIRST

**Trigger:** Session start, user says "continue" or "resume", or after context compaction.

**Mandatory action:**
```
READ .opencode/session-state.json
```

**Before doing anything else:**
1. Parse `current_objective` — this is your anchor
2. Parse `active_blockers` — resolve these first
3. Parse `next_action_trigger` — execute this as your first move
4. Parse `modified_infrastructure` — do NOT re-read these files unless the task requires it

**Violation:** If you perform any tool call (read, bash, grep, edit) BEFORE reading the state ledger, the entire session is compromised. You have wasted tokens re-discovering known state.

---

## RULE 2: BURN-AFTER-READING TOOL OUTPUT

**Trigger:** Every tool call that returns output.

**Mandatory action:**
- Extract ONLY the information needed for the current task
- Discard all surrounding noise (headers, footers, formatting, status messages)
- If a file read returns 500 lines and you need 3, you MUST use `offset` and `limit` to read only those 3 lines

**Forbidden patterns:**
- Reading an entire file when you need one function
- Running `ls` or `dir` to "explore" when you already know the path
- Capturing full bash output when you only need the exit code
- Re-reading a file you already read in this session (check `modified_infrastructure` first)

**Token budget per tool call:**
| Tool | Max Output Tokens | If exceeded |
|------|-------------------|-------------|
| read | 200 | Use offset/limit |
| bash | 100 | Pipe to `Select-Object -First` or `head` |
| grep | 50 | Use `-c` for count or specific pattern |
| glob | 10 | Already returns minimal output |
| edit | 0 | Edit returns no output |

---

## RULE 3: NO RAW REASONING

**Trigger:** Any response to the user.

**Mandatory action:**
- Output ONLY the result, the code change, or the direct answer
- If reasoning is required, compress it to 1-2 sentences maximum
- NEVER output your thought process, analysis steps, or deliberation

**Forbidden patterns:**
```
FORBIDDEN: "Let me think about this... I need to consider X, Y, Z..."
FORBIDDEN: "I'll start by reading the file, then checking the imports..."
FORBIDDEN: "Here's my analysis of the problem..."
```

**Required pattern:**
```
REQUIRED: [Action taken] + [Result] + [Next step if applicable]
```

**Example:**
```
FORBIDDEN (247 tokens):
"I need to add authentication to the settings route. Let me first check how 
it's done in the notes route. I'll read the notes.ts file to understand the 
pattern. Now I see they're using passport.js with a local strategy. I'll need 
to replicate this in settings.ts. Let me also check if passport is in the 
dependencies..."

REQUIRED (34 tokens):
"Added passport.js middleware to POST /settings. Mirrors notes route pattern. 
Next: run tests."
```

---

## RULE 4: STATE UPDATES VIA CLI ONLY

**Trigger:** Task completion, blocker discovery, objective change.

**Mandatory action:**
```bash
python .opencode/skills/session-state-tracker/state_tracker.py [command]
```

**Commands:**
- `update --objective "..."` — set/refresh objective
- `add-file <path> <description>` — track modified file
- `add-blocker <message>` — record blocker
- `resolve-blocker <index>` — remove resolved blocker
- `set-next <command>` — set resume action
- `compress` — enforce token limits

**Forbidden:** Directly editing `.opencode/session-state.json` with the `write` or `edit` tools. The CLI enforces schema compliance. Bypassing it risks corruption.

---

## RULE 5: DESCRIPTIVE MINIMALISM

**Trigger:** Writing to `change_description` in state updates.

**Constraint:** Maximum 12 words per description.

**Formula:** [Verb] + [Object] + [Specific change]

**Examples:**
```
FORBIDDEN: "Updated the authentication middleware to add support for OAuth2 
            tokens and refresh token rotation"
            (17 words — too long, too vague)

REQUIRED:  "Added OAuth2 token refresh to auth middleware"
            (7 words — specific, actionable)
```

```
FORBIDDEN: "Fixed the bug in the API handler"
            (7 words — too vague, what bug?)

REQUIRED:  "Added null check for undefined accessToken in callback"
            (8 words — specifies exact fix)
```

---

## RULE 6: BLOCKER SEVERITY

**Trigger:** Adding to `active_blockers`.

**Classification:**
- **P0 (Critical):** System cannot proceed. All other work stops.
  - Example: "ImportError: core module missing from sys.path"
- **P1 (Blocking):** Current task cannot complete, but other tasks can proceed.
  - Example: "TypeError: Cannot read property 'accessToken' of undefined"
- **P2 (Degraded):** Workaround exists, but output quality is reduced.
  - Example: "Redis connection timeout — using in-memory fallback"

**Rule:** If you have more than 5 active blockers, STOP. You have a structural problem. Do not add more blockers. Resolve the P0s first.

---

## RULE 7: NEXT ACTION PRECISION

**Trigger:** Setting `next_action_trigger`.

**Constraint:** Single executable command or specific question. No vague directives.

**Examples:**
```
FORBIDDEN: "Continue with the implementation"
            (vague — what implementation?)

REQUIRED:  "python -m pytest tests/test_auth.py -v"
            (executable, specific, verifiable)
```

```
FORBIDDEN: "Check if the OAuth flow works"
            (vague — how to check?)

REQUIRED:  "curl -X POST http://localhost:3001/api/auth/callback with test code"
            (specific action with parameters)
```

---

## RULE 8: TOKEN ACCOUNTING

**Trigger:** End of every response.

**Mandatory self-check:**
1. How many tokens did this response consume?
2. How many of those were tool output vs generated code?
3. Could the same result have been achieved with fewer tokens?

**If the ratio of tool-output-tokens to code-tokens exceeds 3:1, you are burning context.** Reduce tool output by using offset/limit, grep -c, or head/tail.

---

## RULE 9: OBJECTIVE LOCK

**Trigger:** Any time you are about to start a new subtask.

**Mandatory check:** Does this subtask directly advance `current_objective`?

**If NO:** Do not do it. Redirect to the objective or update the objective first.

**If YES:** Proceed, but check if it can be done without expanding context.

**Violation:** Drifting into tangential work (refactoring unrelated code, exploring "interesting" patterns, optimizing code that isn't part of the objective) is a context discipline failure.

---

## RULE 10: COMPACTION RECOVERY

**Trigger:** Context compaction event (auto-prune or manual reset).

**Mandatory action:**
1. Read `.opencode/session-state.json` immediately
2. Reconstruct minimal context from `modified_infrastructure`
3. Resume from `next_action_trigger`
4. Do NOT attempt to re-read files "to remember what was happening"

**The state ledger IS your memory.** If the ledger is missing or corrupt, STOP and report the error. Do not improvise.

---

## ENFORCEMENT

These rules are loaded via `.opencode/rules/context-discipline.md` in the OpenCode config. The agent reads them at session start and must follow them throughout.

**Violation consequences:**
- Token waste → reduced session length before compaction
- Context bloat → increased hallucination risk
- Drift from objective → wasted work
- Bypassing CLI → potential schema corruption

**Self-reporting:** If you notice yourself violating a rule, correct immediately and note the violation in the next state update.
