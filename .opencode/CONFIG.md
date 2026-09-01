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
    ├── orchestrate.py               # Unified Intelligence Engine
    ├── slide_state.py               # SQLite schema for engine
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
| `.opencode/session-state.json` | session-state-tracker skill | Cross-session memory |
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
