# Academic AI Engine

A monorepo containing academic research tools orchestrated by an AI agent via OpenCode MCP.

## Repository Structure

```
.
├── opencode.json              # OpenCode main config
├── tui.json                   # OpenCode TUI settings
├── package.json               # Project scripts
├── .opencode/
│   ├── rules/                 # Agent behavior rules
│   │   └── context-discipline.md
│   ├── skills/                # Specialized agent skills
│   │   ├── session-state-tracker/
│   │   ├── unified-engine-architecture/
│   │   ├── day2-operations/
│   │   ├── pdf2pptx-architecture/
│   │   └── scholarsearch-architecture/
│   ├── engine/                # OmniRoute engine config
│   │   └── model-aliases.json
│   ├── swarm/                 # Swarm Cascade deep research engine
│   │   ├── api_server.py      # HTTP API (port 8084, CURRENT PRODUCTION)
│   │   ├── orchestrator.py    # Swarm library
│   │   └── dashboard.html     # Intelligence dashboard
│   ├── orchestrate.py         # Unified Intelligence Engine (legacy)
│   ├── CONFIG.md              # Complete configuration map
│   └── session-state.json     # Cross-session state ledger
├── services/
│   ├── pdf-engine/            # PDF-to-PPTX conversion (Python)
│   ├── scholarsearch/         # Academic search engine (TypeScript)
│   │   └── packages/mcp-sources/  # MCP stdio wrapper (8 academic sources)
│   └── mendeley-patcher/      # Mendeley metadata correction (Python)
└── .github/                   # CI/CD workflows
```

## Quick Start

```bash
# Install OpenCode (if not installed)
curl -fsSL https://opencode.ai/install | bash

# Start OpenCode in this project
opencode

# The agent will:
# 1. Load rules from .opencode/rules/context-discipline.md
# 2. Read session state from .opencode/session-state.json
# 3. Resume from next_action_trigger (if set)
```

## Services

### PDF-to-PPTX Engine (`services/pdf-engine/`)
12-phase Python pipeline for PDF-to-PowerPoint conversion.

- **Stack:** Python 3.11, PyMuPDF, python-pptx, FastAPI, Redis
- **Run:** `cd services/pdf-engine && pip install -r requirements.txt && python orchestrator_v2.py`

### ScholarSearch (`services/scholarsearch/`)
PRISMA-compliant multi-source academic search engine.

- **Stack:** TypeScript, Next.js 14, Fastify, Turborepo, Prisma, PostgreSQL
- **Run:** `cd services/scholarsearch && npm install && npm run dev`

### Mendeley Patcher (`services/mendeley-patcher/`)
Mendeley metadata correction tool.

- **Stack:** Python, requests, SQLite
- **Run:** `cd services/mendeley-patcher && pip install -r requirements.txt && python orchestrator.py`

## AI Agent Architecture

The OpenCode agent operates with:

- **10 immutable rules** (context-discipline.md) enforcing token discipline
- **Session state tracker** for cross-session memory (~120 tokens vs ~10,000 raw)
- **5 specialized skills** for domain-specific tasks
- **3 MCP servers** (pdf-tools, powerpoint, scholarsearch-sources) for tool access

## Configuration

See `.opencode/CONFIG.md` for the complete configuration map and dependency relationships.
