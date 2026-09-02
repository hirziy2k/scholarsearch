# ScholarSearch — Academic Literature Search Engine

A PRISMA-compliant, multi-source federated academic search engine with transparent ranking, clinical research elevation, and offline-first PWA architecture.

## What It Does

ScholarSearch queries 7 academic databases simultaneously, deduplicates results using entity-aware blocking, classifies evidence tiers, and provides a keyboard-driven screening interface designed for clinical research workflows.

### Sources

| Source | Type | Rate Limit |
|---|---|---|
| OpenAlex | Open access index | Polite pool (100k/day) |
| PubMed | Biomedical literature | 3 req/sec (NCBI key) |
| Semantic Scholar | AI-enhanced search | 100 req/5min |
| Crossref | Metadata + DOIs | Free tier |
| CORE | Open access full-text | API key required |
| ERIC | Education research | Free |
| DOAJ | Directory of open access | Free |

### Key Features

- **7-Source Federated Search** — Parallel dispatch with circuit breaker pattern
- **Entity-Aware Deduplication** — Title + author + DOI fuzzy matching with Levenshtein distance
- **Score Lock** — Prevents ranking manipulation from merged shadow records
- **Query Versioning** — Cryptographic hash of query parameters for reproducibility
- **Gap Analysis** — Identifies missing evidence domains in search results
- **Predatory OA Quarantine** — Flags journals from known predatory publishers
- **Two-Phase Screening** — Title/abstract + full-text exclusion with PRISMA shadow ledger
- **Keyboard Navigation** — Vim-style J/K/Space/P/E hotkeys for terminal-velocity screening
- **Command Palette** — Number-key exclusion reason picker (PICO-based)
- **Offline PWA** — Serwist service worker with React offline fallback
- **IndexedDB Session** — 24h TTL, incognito mode, session export/import
- **Manifest Reconciliation** — Cryptographic session manifest with errata detection
- **RIS/CSV/JSON/ZIP Export** — Batch export with PRISMA flowchart generation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ScholarSearch v0.1.0                      │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Next.js 14)          Backend (Fastify)           │
│  ├─ Port 3000                   ├─ Port 3001                │
│  ├─ Serwist SW (offline)        ├─ 7-source orchestrator    │
│  ├─ IndexedDB session           ├─ Circuit breaker          │
│  ├─ Hotkey controller           ├─ Entity-aware dedup       │
│  ├─ Flex-graph entities         ├─ Score lock               │
│  └─ Command palette             ├─ Query versioning         │
│                                  └─ Gap analysis             │
├─────────────────────────────────────────────────────────────┤
│  Sources: OpenAlex · PubMed · Semantic Scholar · Crossref  │
│           CORE · ERIC · DOAJ                                │
├─────────────────────────────────────────────────────────────┤
│  LLM: Anthropic (Sonnet/Haiku) · OpenAI (GPT-4o/4o-mini)   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Node.js 20+
- npm 10+

### Installation

```bash
git clone https://github.com/hirziy2k/scholarsearch.git
cd scholarsearch
npm install
```

### Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required keys (free tiers available):
- `ANTHROPIC_API_KEY` — For LLM-powered summaries (optional)
- `OPENAI_API_KEY` — Alternative LLM provider (optional)
- `SEMANTIC_SCHOLAR_API_KEY` — Higher rate limits (optional)
- `NCBI_API_KEY` — PubMed rate limit boost (optional)
- `CORE_API_KEY` — CORE access (optional)

The search works without any API keys (using free tier defaults).

### Development

```bash
npm run dev
```

Frontend: http://localhost:3000
Backend: http://localhost:3001

### Production

```bash
npm run build
npm start
```

## Hotkey Reference

| Key | Action |
|---|---|
| `J` / `↓` | Next paper |
| `K` / `↑` | Previous paper |
| `Space` | Expand/collapse abstract |
| `P` | Promote to full-text |
| `E` | Open exclusion palette |
| `1`-`9` | Select exclusion reason |
| `Escape` | Close palette/modal |

## Monorepo Structure

```
scholarsearch/
├── packages/
│   ├── shared/          # TypeScript schemas, utils, data
│   ├── backend/         # Fastify API server
│   ├── frontend/        # Next.js 14 PWA
│   ├── mcp-sources/     # 7 source API clients
│   └── omniroute/       # LLM routing (Anthropic + OpenAI)
├── start.js             # Production startup script
├── turbo.json           # Turborepo configuration
└── docker-compose.yml   # Optional: PostgreSQL + Redis
```

## Export Formats

- **JSON** — Full session data with metadata
- **RIS** — Import into Zotero/EndNote/Mendeley
- **CSV** — Spreadsheet-compatible
- **ZIP** — Bundle with RIS + session manifest + PRISMA flowchart + offline HTML

## License

MIT
