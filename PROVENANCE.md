# ScholarSearch — Provenance & Migration Record

## Origin

Migrated (copy, not move) from the legacy monorepo:

- Legacy root: `Default Project` (`C:\Users\hirzi\OneDrive\Documents\Default Project`)
- Legacy HEAD at migration: `d59ef515c085073371fcd3252790c01a5321f2bd`
  (`Post-remediation audit - all P0/P1 resolved`, 2026-09-13)
- Legacy remote: `https://github.com/hirziy2k/scholarsearch.git`
- Migration date: 2026-09-13
- Method: reversible file copy (`robocopy` + explicit `Copy-Item`); legacy repo untouched.
- Integrity: 150/150 in-scope files SHA-256 verified against checkpoint manifest
  (`scholarsearch_manifest.csv`, held outside the repo). 0 mismatches.
  Secrets sweep post-copy: no `.env`, `*.log`, `*.db`, `*.sqlite` present.

## Layout change (promoted to root)

In the legacy monorepo the engine lived under `services/scholarsearch/`.
This repo promotes it to the repository root (`apps/`, `packages/`, Docker files, etc.).
Path references updated mechanically as part of the move:

| File | Change |
|---|---|
| `opencode.json` | New (minimal). MCP `scholarsearch-sources` command `services/scholarsearch/packages/mcp-sources/dist/mcp-server.js` → `packages/mcp-sources/dist/mcp-server.js`. Permission/credential-deny guards preserved from legacy. `pdf-tools`/`powerpoint` MCP servers not migrated (non-ScholarSearch). |
| `.github/workflows/ci-scholarsearch.yml` | `paths:` filter removed (single-purpose repo: everything is in scope). `working-directory: services/scholarsearch` → `.`, `cache-dependency-path` → `package-lock.json`, `docker build -f Dockerfile .`. Build/unit/e2e steps otherwise unchanged. |
| `.opencode/skills/scholarsearch-architecture/SKILL.md` | Project-location + task paths rewritten to repo root. Content otherwise as-authored. KNOWN STALE (pre-existing): describes Postgres/4 models/2 routes; actual tree is SQLite/7 models/6 routes. Not silently corrected — flagged for a follow-up skill update. |
| `tools/stress_test_scholarsearch.py` | Hint `cd scholarsearch && npm start` → `npm start`. |
| `tests/extract_ingested_fields.py` | `SCAN_PATHS["scholarsearch"]` → `apps/server/src`. `pdf-engine` entry retained (harmless when run standalone; points at legacy checkout). |
| `README.md` | Unchanged — already written for a standalone `scholarsearch` checkout (`git clone … / cd scholarsearch / npm install`). |
| `.gitignore` | Legacy `services/scholarsearch/.gitignore` promoted + Python cache ignores appended for `tests/`/`tools/`. |

## Relocations

| Legacy path | New path |
|---|---|
| `services/scholarsearch/**` (minus excludes below) | `./` (repo root) |
| `.opencode/skills/scholarsearch-architecture/SKILL.md` | `.opencode/skills/scholarsearch-architecture/SKILL.md` |
| `.github/workflows/ci-scholarsearch.yml` | `.github/workflows/ci-scholarsearch.yml` |
| `tests/e2e_scholarsearch.py`, `tests/conftest.py` | `tests/` (conftest shared with pdf-engine; kept as-is) |
| `tests/cassettes/scholarsearch/` | `tests/cassettes/scholarsearch/` |
| `tests/schema_drift_detector.py`, `tests/extract_ingested_fields.py`, `tests/ingested_fields.json` | `tests/` |
| `services/pdf-engine/stress_test_scholarsearch.py` | `tools/stress_test_scholarsearch.py` |
| `services/pdf-engine/Academic_Search_Engines_Master_Document.md` | `docs/Academic_Search_Engines_Master_Document.md` |
| `Supplement_S1_Search_Strategies_v1.2.md`, `Scoping_Review_Protocol_v7.6.md`, `Scoping_Review_Operations_Manual_v1.6.md`, `scoping_review_benchmark_extraction_TABLE_FULL.md` | `docs/` |
| `reports/SCOPING_REVIEW_CONTROLLED_CLEANUP_20260911.md`, `reports/P0_bibliography_audit.json` | `reports/` |
| `flowcharts/` | `docs/flowcharts/` |

## Deliberately excluded (left in legacy)

- Secrets & runtime: `services/scholarsearch/.env`, `apps/server/.env`
  (`DATABASE_URL` key only — recreate from `.env.example`), `*.log`, `*.db`/`*.sqlite`.
- Build artifacts: `node_modules/`, `.next/`, `.turbo/`, `dist/`, `*.tsbuildinfo`
  (rebuilt via `npm ci` / `npm run build`; `package-lock.json` migrated for reproducibility).
- Non-ScholarSearch monorepo: `services/pdf-engine/`, `services/mendeley-patcher/`,
  `.opencode/swarm/`, `.opencode/engine/`, `.opencode/orchestrate.py`, root `session-state.json`,
  other skills/rules, `tui.json`, `data/` (untracked psychometric SAV/CSV), untracked root
  scripts (`query_onedrive_dbs.py`, `sav_to_csv.py`, `validate_psychometric*.py`, `cran_index.html`, `r_index.html`).
- Shared/global (documented dependency, not copied): global `~/.config/opencode/opencode.jsonc`
  (OmniRoute provider), `BACKUP/`, `archive_superseded_20260903/` (superseded protocol versions;
  canonical current versions migrated to `docs/`), legacy CI workflows covering pdf-engine
  (`e2e-contract-gate.yml`, `schema-drift-detector.yml`, `dependabot-quarantine.yml`),
  `tests/{fuzz_server,spot_fuzzer,e2e_pdf_engine}.py`, `tests/DEPENDENCY_DASHBOARD_SPEC.md`.
- Legacy working-tree state at migration (not ScholarSearch, left untouched):
  modified `.opencode/skills/scientific-writing/SKILL.md`,
  `.opencode/swarm/literature_fetcher.py`; untracked `data/`, root scripts noted above.

## Git history note

This repo starts with a single squashed initial commit (fresh `git init`).
Full file history remains available in the legacy repo
(`Default Project`, HEAD `d59ef51`, remote above). Key ScholarSearch commits in legacy history:

- `291fc87` fix(core): clinical weights, abstract intersection, schema v2, Dockerfile prisma generate
- `3e12db0` deploy: production Docker stack with Caddy TLS + Litestream DR
- `19f661d` feat: clinical evidence pipeline v1.0.0 — 8-branch architecture
- `0b440db` fix: all unit and e2e tests pass
- `bd8069e` feat: database-native syntax registry integration (65/65 validation)

## Migration-necessitated fix (verified, new repo only — legacy untouched)

`apps/server/src/db.ts` — `PRAGMA journal_mode=WAL / busy_timeout / synchronous`
changed from `$executeRawUnsafe` to `$queryRawUnsafe`.
Reason: these PRAGMAs return result rows; Prisma ≥5 rejects result-returning
statements via executeRaw (P2010), so a fresh build crashed at startup.
The bug exists identically in legacy `src/db.ts` but was masked there by a stale
`dist/` predating the PRAGMA code (legacy dist serves `/health`; fresh build crashed).
Evidence: BEFORE (legacy dist, port 3002) `/health` → `ok`;
AFTER fix (new repo, sterile DB, port 3001) `/health` → `ok`, 8/8 e2e pass.
Risk: negligible (same statements, result ignored). Reversibility: 3-line diff.

## Pre-existing issues carried over (not introduced by migration)
1. `scholarsearch-architecture/SKILL.md` stale vs actual tree (Postgres/4-models/2-routes claim).
2. No global Fastify error handler (per-route try/catch only).
3. `railway.json` healthcheck `/health` assumes Caddy prefix routing.
4. `NEXT_PUBLIC_API_URL` build-time inlining vs compose `http://api:3001` vs `start.js` localhost.
5. Tracked legacy `.opencode/swarm/redis.env` (populated-like) stays in legacy scope — out of scope here,
   flagged for secret review in its own repo.
