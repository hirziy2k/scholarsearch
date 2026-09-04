# Configuration Map

## File Locations

```
Default Project/
├── opencode.json                    # OpenCode main config (instructions, MCP, compaction)
├── tui.json                         # OpenCode TUI settings (cursor, scroll, attention)
├── package.json                     # Project-level npm scripts (dev commands)
├── compression_config.json          # ORPHANED — not used by OpenCode (legacy)
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
    │   ├── redis6380.env            # Path 2 Redis config (degraded on 3.0.504 until 7+)
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
       ├──► mcp: { pdf-tools, powerpoint }
       │
       └──► compaction: { auto, prune, reserved }

tui.json ─────────────────────► TUI appearance (cursor, scroll, attention)

session-state.json ◄──────────► session-state-tracker skill (read/write via CLI)

engine/model-aliases.json ────► orchestrate.py (OmniRoute routing, NOT OpenCode)
```

## What Reads What

| Config File | Read By | Purpose |
|-------------|---------|---------|
| `opencode.json` | OpenCode | MCP servers, instructions, compaction |
| `tui.json` | OpenCode | TUI appearance and behavior |
| `.opencode/rules/*.md` | OpenCode | Agent behavior rules |
| `.opencode/session-state.json` | session-state-tracker skill | Cross-session memory (canonical ledger) |
| `.opencode/swarm/redis6380.env` | swarm/api_server.py | Redis Path 2 config (see swarm section) |
| `.opencode/engine/model-aliases.json` | orchestrate.py | OmniRoute model routing |
| `compression_config.json` | Nothing (orphaned) | Legacy, can be deleted |

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
