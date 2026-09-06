# Configuration Map

## File Locations

```
Default Project/
├── opencode.json                    # OpenCode main config (instructions, MCP, compaction, permissions, security)
├── tui.json                         # OpenCode TUI settings (cursor, scroll, attention) [optional]
├── package.json                     # Project-level npm scripts (dev commands) [optional]
├── README.md                        # Project documentation
└── .opencode/
    ├── .gitignore                   # Git ignore rules for .opencode/
    ├── package.json                 # OpenCode plugin dependencies
    ├── session-state.json           # Session State Tracker ledger (~120 tokens)
    ├── rules/
    │   └── context-discipline.md    # 10 immutable governor rules
    ├── skills/
    │   ├── session-state-tracker/   # State tracker skill + CLI tools
    │   ├── unified-engine-architecture/
    │   ├── day2-operations/
    │   ├── pdf2pptx-architecture/
    │   └── scholarsearch-architecture/
    ├── engine/
    │   └── model-aliases.json       # OmniRoute model routing (engine-only, not OpenCode)
    ├── orchestrate.py               # Unified Intelligence Engine (port 8083, legacy primary)
    ├── swarm/
    │   ├── api_server.py            # Swarm Cascade API (port 8084, CURRENT PRODUCTION)
    │   ├── orchestrator.py          # Swarm library (used by api_server)
    │   ├── redis.env               # Redis config (upgraded to 8.10.1 on 2026-09-06)
    │   └── data-redis6380/          # Path 2 RDB dir (gitignored)
    ├── slide_state.py               # SQLite schema for engine (WAL, slide_state.sqlite)
    ├── compile_pptx.py              # PPTX compiler
    ├── compile_web.py               # Web compiler
    └── schemas/                     # JSON schemas
```

## Config Relationships

```
opencode.json ────────────────► instructions: [".opencode/rules/*.md"]
       │                                    │
       │                                    ▼
       │                        context-discipline.md (10 rules)
       │
       ├──► mcp: { pdf-tools, powerpoint, scholarsearch-sources }
       │
       ├──► compaction: { auto, prune, reserved }
       │
       ├──► share: "disabled"
       │
       └──► permission:
             ├── read: { credential deny rules }
             └── edit: { opencode.json: deny }

tui.json ─────────────────────► TUI appearance (cursor, scroll, attention) [optional]

session-state.json ◄──────────► session-state-tracker skill (read/write via CLI)

engine/model-aliases.json ────► orchestrate.py (OmniRoute routing, NOT OpenCode)
```

## Security Posture (2026-09-06, updated 2026-09-06 Redis upgrade)

**Filesystem protection:** `opencode.json` is NOT OS read-only (attrib=Archive). Protection is agent-level via `permission.edit` deny only.

**Permission deny rules (project-level):**
- `read` denied: `*.key`, `*.pem`, `id_rsa*`, `id_ed25519*`, `.aws/`, `.gcloud/`, `.ssh/`, `.gnupg/`, `.env` files
- `edit` denied: `opencode.json` itself
- `share`: explicitly disabled

**Known limitations:**
- Bash commands can bypass `read` deny rules (shell executes directly)
- MCP servers run unsandboxed (same user context)
- No OS-level sandbox (WSL2/Docker not installed)
- Permission system is UI-level, not security boundary

**Revert command:** `attrib -R "C:\Users\hirzi\OneDrive\Documents\Default Project\opencode.json"`

## What Reads What

| Config File | Read By | Purpose |
|-------------|---------|---------|
| `opencode.json` | OpenCode | MCP servers, instructions, compaction, permissions, security |
| `tui.json` | OpenCode | TUI appearance and behavior [optional] |
| `.opencode/rules/*.md` | OpenCode | Agent behavior rules |
| `.opencode/session-state.json` | session-state-tracker skill | Cross-session memory (canonical ledger) |
| `.opencode/swarm/redis.env` | swarm/api_server.py | Redis config (8.10.1, password-protected) |
| `.opencode/engine/model-aliases.json` | orchestrate.py | OmniRoute model routing |

## Dependency Map

```
.opencode/package.json
└── @opencode-ai/plugin: 1.18.19

package.json (root)
└── (no dependencies — scripts only)
```

## Rules Loading Chain

1. OpenCode reads `opencode.json`
2. Sees `instructions: [".opencode/rules/*.md"]`
3. Loads `.opencode/rules/context-discipline.md`
4. Agent receives rules as system instructions
5. Agent must follow Rules 1-10 at all times
