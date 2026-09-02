---
name: scholarsearch-architecture
description: ScholarSearch academic literature search engine — PRISMA-compliant multi-source federated search with transparent ranking, clinical research elevation, and offline-first PWA architecture
license: MIT
compatibility: opencode
metadata:
  tech-stack: Next.js 14, Fastify, TypeScript, Tailwind CSS, Serwist PWA, Prisma, PostgreSQL
  sources: OpenAlex, PubMed, Semantic Scholar, Crossref, CORE, ERIC, DOAJ, Scopus
  llm: Anthropic Claude, OpenAI GPT-4o
---

# ScholarSearch Architecture Skill

Use when working with the ScholarSearch academic literature search engine — a PRISMA-compliant, multi-source federated search platform with transparent ranking, clinical research elevation, and offline-first PWA architecture.

## Project Location

`C:\Users\hirzi\OneDrive\Documents\Default Project\services\scholarsearch`

## Monorepo Structure

```
services/scholarsearch/
├── apps/
│   ├── client/              # Next.js 14 PWA (port 3000)
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── page.tsx              # Main search page
│   │   │   │   ├── layout.tsx            # Root layout with PWA meta tags
│   │   │   │   ├── globals.css           # Charcoal-and-Bone CSS variables
│   │   │   │   ├── sw.ts                 # Serwist service worker source
│   │   │   │   └── ~offline/page.tsx     # React offline fallback (IndexedDB access)
│   │   │   ├── components/
│   │   │   │   ├── ResultCard.tsx        # Card with flex-graph entities, hover-to-audit
│   │   │   │   ├── ResultList.tsx        # Singleton IntersectionObserver + useLayoutEffect re-paint
│   │   │   │   ├── CommandPalette.tsx    # Keyboard-navigable exclusion picker
│   │   │   │   ├── SearchBar.tsx         # Search input with loading spinner
│   │   │   │   ├── ModeSelector.tsx      # Search mode dropdown
│   │   │   │   └── RankingPanel.tsx      # Ranking weight sliders
│   │   │   ├── hooks/
│   │   │   │   ├── useSSESearch.ts       # SSE search + IndexedDB + session management
│   │   │   │   └── useHotkeys.ts         # Mutable ref controller + JIT state sync
│   │   │   ├── lib/
│   │   │   │   ├── session-db.ts         # IndexedDB wrapper with 24h TTL
│   │   │   │   ├── ris-export.ts         # RIS generation with L1/L2/UR tags
│   │   │   │   ├── archive-export.ts     # ZIP builder (no deps)
│   │   │   │   ├── session-manifest.ts   # Cryptographic manifest with errata detection
│   │   │   │   ├── levenshtein.ts        # Fuzzy anchor resolution
│   │   │   │   └── api.ts               # Fetch wrapper for backend API
│   │   │   └── workers/
│   │   │       └── anchor-finder.worker.ts  # Web Worker for off-main-thread Levenshtein
│   │   ├── public/                      # Static assets (sw.js, manifest.json)
│   │   ├── next.config.js               # Serwist integration
│   │   └── package.json
│   │
│   └── server/              # Fastify API server (port 3001)
│       ├── src/
│       │   ├── server.ts                # Fastify config, CORS, route registration
│       │   ├── routes/
│       │   │   ├── health.ts            # GET /health
│       │   │   └── search.ts            # SSE + sync routes, /api/paper/abstract
│       │   └── services/
│       │       ├── search-orchestrator.ts  # Full pipeline: circuit breaker → AST → dispatch → dedup
│       │       └── doi-verification.ts     # Retraction detection, abstract hash-diff
│       ├── prisma/
│       │   └── schema.prisma            # PostgreSQL schema (4 models)
│       └── package.json
│
├── packages/
│   ├── shared/              # @scholarsearch/shared
│   │   ├── src/
│   │   │   ├── schemas/
│   │   │   │   ├── paper.ts             # ScholarlyWork Zod master schema
│   │   │   │   └── search.ts            # SearchQuery, SearchMode, RankingWeights
│   │   │   ├── utils/
│   │   │   │   ├── document-tiers.ts    # PeerReviewTier, GreyLiteratureTier classification
│   │   │   │   ├── query-parser.ts      # AST parser, 8-source query compilers
│   │   │   │   ├── ranking.ts           # OPENNESS_WEIGHTS, calculateOpennessScore()
│   │   │   │   ├── query-versioning.ts  # SHA-256 hash with cardinality + top DOIs
│   │   │   │   ├── predatory-quarantine.ts  # checkPredatory(), getPredatoryMultiplier()
│   │   │   │   ├── gap-analysis.ts      # analyzeResearchGaps(), GapAuditTrail
│   │   │   │   ├── vocabulary-crosswalk.ts  # Malay clinical crosswalk, ERIC/DOAJ
│   │   │   │   ├── dedup.ts             # Entity-aware deduplication with shadow merge
│   │   │   │   ├── circuit-breaker.ts   # Circuit breaker + Score Lock
│   │   │   │   ├── cardinality.ts       # AND-unsafe cardinality pre-flight
│   │   │   │   └── oa-resolver.ts       # Open Access URL resolution
│   │   │   └── data/
│   │   │       ├── malay-clinical.ts    # 40+ Malay clinical terms
│   │   │       ├── predatory-publishers.ts  # Known predatory publisher list
│   │   │       ├── eric-descriptors.ts  # ERIC controlled vocabulary
│   │   │       └── doaj-subjects.ts     # DOAJ subject crosswalk
│   │   └── package.json
│   │
│   ├── mcp-sources/         # @scholarsearch/mcp-sources (8 source API clients)
│   │   ├── src/
│   │   │   ├── index.ts                 # Exports all 8 source clients
│   │   │   ├── shared.ts                # RateLimiter, fetchWithRetry, SourceClient interface
│   │   │   ├── openalex.ts              # OpenAlex with abstract_inverted_index decoding
│   │   │   ├── pubmed.ts                # PubMed E-utilities
│   │   │   ├── semantic-scholar.ts      # Semantic Scholar
│   │   │   ├── crossref.ts              # Crossref with batchResolveDois()
│   │   │   ├── core.ts                  # CORE open access
│   │   │   ├── eric.ts                  # ERIC education research
│   │   │   ├── doaj.ts                  # DOAJ directory
│   │   │   └── scopus.ts               # Scopus/Elsevier
│   │   └── package.json
│   │
│   └── omniroute/           # @scholarsearch/omniroute
│       ├── src/
│       │   ├── router.ts                # TaskType routing to Haiku/GPT-4o-mini
│       │   └── providers/
│       │       ├── anthropic.ts         # Anthropic SDK wrapper
│       │       └── openai.ts            # OpenAI SDK wrapper
│       └── package.json
│
├── start.js                 # Production startup script (concurrent backend + frontend)
├── turbo.json               # Turborepo configuration
├── tsconfig.base.json       # Shared TS config (ES2022, NodeNext, composite)
├── docker-compose.yml       # PostgreSQL + Redis + backend + frontend
├── railway.json             # Railway deployment config
├── .env.example             # Environment variable template
└── README.md                # Full documentation
```

## Key Design Decisions

### Charcoal-and-Bone Design System
CSS variables in `globals.css`:
- `--color-bone: #FAFAF8` (background)
- `--color-charcoal: #1A1A1A` (text)
- `--color-accent-gap: #E8C547` (banana-yellow — ONLY for gap banners and active card focus)
- `--font-mono` for tick-data formatting

### Score Lock
Prevents ranking manipulation from merged shadow records. Once a paper's score is calculated, it's locked and cannot be inflated by duplicate merges. Implemented in `circuit-breaker.ts`.

### Shadow Merge + PRISMA Ledger
Every UI action on merged cards expands to all constituent source records for PRISMA compliance. The `sourceRecords[]` array tracks the provenance of each merged paper.

### Entity-Aware Blocking
Deduplication uses title + author + DOI fuzzy matching with Levenshtein distance, not just exact string matching. Implemented in `dedup.ts` with a Web Worker (`anchor-finder.worker.ts`) for off-main-thread processing.

### Query Versioning
Cryptographic SHA-256 hash of query parameters (including cardinality and top DOIs) for reproducibility and audit trails.

### Gap Analysis
Identifies missing evidence domains in search results with `GapAuditTrail` tracking query parameters, sources queried, taxonomy nodes checked, and tier distribution.

### Predatory OA Quarantine
Flags journals from known predatory publishers and applies a multiplier penalty to their ranking scores.

### Keyboard Navigation (Vim-style)
- `useHotkeys` hook uses `useRef(0)` for mutable index (zero re-renders on J/K)
- Direct DOM class mutation via `document.querySelectorAll("[data-paper-id]")`
- `useLayoutEffect` re-paint hook in ResultList survives React re-renders
- Just-in-Time state sync: reads DOM `data-paper-id` on E/P press

### HTML/CSS Flex-Graph (not SVG)
Entity visualization uses standard `<div>` + `<span>` elements for:
- Native text selection (`user-select: text`)
- Screen reader accessibility (`aria-label="Clinical Relationship Graph"`)
- CSS clamping (`max-width: 120px` + `text-overflow: ellipsis`)
- Native tooltips via `title` attribute

### Offline PWA (Serwist)
- `@serwist/next` with `swSrc: "src/app/sw.ts"`
- React-based `~offline/page.tsx` route (IndexedDB hooks remain mounted)
- `skipWaiting: true` for immediate cache invalidation

### Session Persistence
- IndexedDB with 24h TTL via `idb` library
- 60s hidden wipe on tab hide
- `beforeunload` wipe
- Incognito toggle disables all writes
- Manifest import/export with cryptographic hash verification

### Prisma ORM
PostgreSQL schema with 4 models:
- `SearchSession` — search query + filters + audit record
- `SearchResult` — individual paper records with ranking scores
- `SavedPaper` — user bookmarks with screening status
- `AuditLog` — PRISMA-compliant action tracking

### DOI Verification
Batch DOI verification via Crossref + OpenAlex for:
- Retraction detection
- Abstract hash-diff errata detection

## Startup Commands

```bash
# Development
npm run dev              # Starts all packages via Turborepo

# Production
npm run build            # Builds all packages
npm start                # Starts backend (3001) + frontend (3000)

# Individual
npm run start:backend    # Port 3001
npm run start:frontend   # Port 3000
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Backend health check |
| `/api/search` | POST | SSE search stream |
| `/api/search/sync` | POST | Synchronous search (supports `?compact=true`) |
| `/api/paper/abstract` | GET | Micro-summary + anchors (`?doi=`) |

## Search Query Schema

```typescript
interface SearchQuery {
  raw_query: string;
  mode: "discovery" | "clinical" | "systematic" | "evidence" | ...;
  weights: RankingWeights;
  max_results?: number;
  region?: string;
}
```

## Exclusion Reasons (PICO-based)

1. Wrong population
2. Wrong intervention
3. Wrong outcome
4. Wrong study design
5. Wrong setting
6. Duplicate (missed dedup)
7. Not original research
8. Insufficient data
9. Custom reason...

## Key Patterns

### SSE Search Flow
```
Client → POST /api/search → Backend orchestrator
  → Circuit breaker check
  → AST parse → cardinality pre-flight
  → Parallel dispatch to 8 sources
  → Local intersection → dedup + entity blocking
  → Tier classification → score lock
  → Query versioning → gap analysis
  → SSE events back to client
```

### Hotkey Navigation Flow
```
J/K press → activeIndexRef.current++ (mutable, no re-render)
  → useLayoutEffect re-applies .is-active-card class
  → setActiveCardId (only for expand-modal lookup)

E press → getLivePaperId() reads DOM data-paper-id
  → setActiveCardId(liveId) → setIsPaletteOpen(true)

P press → getLivePaperId() reads DOM data-paper-id
  → find paper in results → callbacks.onPromote(paper)
```

### Offline Flow
```
Network drops → Serwist SW serves cached app shell
  → React tree mounts → ~offline/page.tsx renders
  → IndexedDB hooks remain mounted
  → User can view bookmarks, exclusions, export manifest
  → Reconnect → NetworkFirst strategy fetches fresh HTML
```

## Common Tasks

### Adding a new source client
1. Create `services/scholarsearch/packages/mcp-sources/src/newsource.ts`
2. Implement `SourceClient` interface from `shared/src/index.ts`
3. Add to `search-orchestrator.ts` dispatch list
4. Add query compiler to `query-parser.ts`

### Adding a new exclusion reason
1. Add to `EXCLUSION_REASONS` array in `useHotkeys.ts`
2. Update `CommandPalette.tsx` if custom UI needed

### Modifying ranking weights
1. Edit `DEFAULT_WEIGHTS` in `page.tsx`
2. Adjust `OPENNESS_WEIGHTS` in `ranking.ts` for OA scoring

### Changing CSS design tokens
1. Edit CSS variables in `globals.css` `:root` block
2. All components reference these variables

## Testing

```bash
# Build all packages
npm run build

# Run individual package builds
cd services/scholarsearch/packages/shared && npm run build
cd services/scholarsearch/packages/mcp-sources && npm run build
cd services/scholarsearch/packages/omniroute && npm run build
cd services/scholarsearch/apps/server && npm run build
cd services/scholarsearch/apps/client && npm run build

# Health check
curl http://localhost:3001/health

# Search test
curl -X POST http://localhost:3001/api/search \
  -H "Content-Type: application/json" \
  -d '{"raw_query":"paracetamol fever","mode":"discovery","max_results":10}'
```

## Deployment

- **Node.js 20+** required
- PostgreSQL via Docker Compose or Railway
- Free API tiers work out of the box
- `npm start` runs both services concurrently
- PWA works offline after first visit
- Railway deployment via `railway.json` (Nixpacks builder)
