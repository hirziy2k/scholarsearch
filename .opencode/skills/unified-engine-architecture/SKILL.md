---
name: unified-engine-architecture
description: Use when working with the Unified Intelligence Engine — the complete opencode + OmniRoute integration system. Covers the 14-iteration architecture including async parallel dispatch, semantic validation, branded template compilation, interactive web output, distributed HITL, live data ingestion, RLHF feedback loop, headless HTTP orchestration, contextual partitioning, GIL-free compute, data sovereignty, idempotent resumption, ABAC domains, air-gapped NER, zero-persistence ephemeral buffers, SSRF firewall, cryptographic hash chains, autonomous self-diagnostics, pre-signed object storage, token-budget circuit breaker, distributed ephemeral relay, semantic versioning tree, dynamic volatility governor, cryptographic command gateway, M-of-N quorum, heterogeneous compute split, branching scenario simulation, operational dashboard, compliance PDF reverse-translation, and cryptographic credential minting.
---

# Unified Intelligence Engine — Complete Architecture

## Purpose

A headless, self-healing state machine that bridges PDF ingestion, scenario compilation, credential minting, and operational monitoring into a single production system. Runs on Windows with Python 3.12, SQLite (WAL mode), and OmniRoute LLM fleet.

## Runtime

| Component | Port | Purpose |
|-----------|------|---------|
| OmniRoute | 20128 | LLM fleet (oc/hy3-free primary) |
| HITL | 8081 | Human-in-the-loop command center |
| Export API | 8082 | Distributed HITL REST API |
| Orchestrator | 8083 | Unified Intelligence Engine |

## Core Files

| File | Purpose |
|------|---------|
| `orchestrate.py` | Main server — all endpoints, pipeline thread, SSE/callback egress |
| `slide_state.py` | Multi-table SQLite schema with WAL mode, ABAC domains |
| `parallel_dispatch.py` | ThreadPoolExecutor dispatcher + NER + compound citations |
| `vector_store.py` | NumPy cosine similarity + ABAC domain filtering |
| `entity_anonymizer.py` | Air-gapped NER with SHA-256 placeholders |
| `ontology_ledger.py` | Auto-discovering entity ledger |
| `semantic_bypass.py` | 98% Jaccard deduplication |
| `buffer_broker.py` | BufferBroker + DeliveryLedger + hash chain + DLQ |
| `egress_firewall.py` | SSRF protection (blocks private/loopback) |
| `compile_pptx.py` | Brand-immutable PPTX compiler (master_template.potx) |
| `compile_web.py` | Interactive web compiler |
| `validate_fidelity.py` | Gate 2 semantic examiner |
| `validate_blueprint.py` | Gate 1 schema validation |
| `repair_router.py` | No-retry repair via secondary model |
| `audit_ui.py` | HITL command center (port 8081) |
| `export_api.py` | Distributed HITL REST API (port 8082) |

## Divergence Layers (14 iterations)

### 1st–4th: Core Pipeline
- Async parallel dispatch with ThreadPoolExecutor
- Semantic validation (Gate 1: schema, Gate 2: fidelity)
- Brand-immutable PPTX compilation from master_template.potx
- Interactive web output (HTML with auto-refresh)

### 5th: Ontological Intelligence
- Ontological ledger auto-discovers entities before ingestion
- Semantic Bypass: clone existing slides if concept known (Zero-Execution)
- Bifurcated Egress: SSE stream + REST webhook for low-code clients

### 6th–7th: Operational Hardening
- Distributed HITL (port 8082) with REST API
- Live data ingestion with TTL-based volatile decay
- RLHF feedback loop for continuous improvement

### 8th–9th: Headless Orchestration
- Headless HTTP orchestration (all endpoints JSON)
- Contextual partitioning with ABAC domain filtering
- GIL-free compute via ThreadPoolExecutor

### 10th: Data Sovereignty
- Data sovereignty with ABAC clearance tiers
- Idempotent resumption (auto-resume stranded runs)
- Air-gapped NER (local anonymization before LLM)

### 11th: Security Layer
- Zero-persistence ephemeral buffers (300s TTL)
- SSRF firewall (blocks private/loopback subnets)
- Cryptographic hash chain (append-only delivery ledger)

### 12th: Advanced Systems
- Autonomous self-diagnostic daemon (120s interval)
- Pre-signed object storage (content-addressable)
- Token-budget circuit breaker (daily limits)

### 13th: Meta-Divergence
- Distributed ephemeral relay (SHA-256 content-addressable)
- Git-compatible semantic versioning (Merkle hash tree)
- Dynamic volatility governor (variance-based budgets)
- Cryptographic command gateway (HMAC-SHA256 signed commands)

### 14th: Operational Divergence
- M-of-N cryptographic quorum (2-of-3 multi-sig)
- Heterogeneous compute split (GPU/CPU probe, batch gate)
- Branching scenario simulation API (replaces .pptx)
- Unified operational dashboard (auto-refresh 30s)
- Compliance PDF reverse-translation
- Cryptographic credential minting (HMAC-SHA256)

## API Endpoints

### Pipeline
- `POST /api/execute` — Main ingestion (budget gate → compute gate → pipeline)
- `GET /api/status/<run_id>` — Pipeline status
- `GET /api/result/<run_id>` — Pipeline result
- `GET /api/stream/<run_id>` — SSE stream
- `GET /api/stranded` — Stranded runs for idempotent resume

### Scenarios
- `POST /api/scenario/compile` — Compile chunks into scenario graph
- `POST /api/scenario/start` — Start evaluation session
- `POST /api/scenario/respond` — Submit response
- `GET /api/scenario/<id>` — Get scenario details
- `GET /api/scenario/session/<id>` — Get session status

### Credentials
- `POST /api/credential/mint` — Mint credential on passing score
- `GET /api/credential/verify/<id>` — Verify credential
- `POST /api/credential/credentials` — List credentials

### Security
- `POST /api/command` — HMAC-signed command gateway
- `POST /api/quorum/create` — Create quorum session
- `POST /api/quorum/submit` — Submit fragment
- `GET /api/quorum/pending` — Pending sessions

### Versioning
- `POST /api/version/create` — Create document version
- `POST /api/version/diff` — Diff two versions
- `GET /api/version/<doc_id>` — Version history

### Relay
- `POST /api/relay/pin` — Pin content to distributed relay
- `GET /api/relay/stats` — Relay statistics

### Monitoring
- `GET /api/health` — System health
- `GET /api/budget` — Volatility governor budgets
- `GET /api/compute/topology` — GPU/CPU probe
- `GET /api/diagnostic` — Self-diagnostic triggers
- `GET /api/dlq` — Dead letter queue
- `GET /api/broker/stats` — Buffer broker stats
- `GET /api/dashboard/data` — Dashboard JSON
- `GET /dashboard` — HTML dashboard

## Key Configuration

- **API Key**: `oma_live_1rczQUSkElshykDzRaZkA4iHmz95trFEqO9UutWsIJM` (env: `OMNIROUTE_API_KEY`)
- **Default Model**: `oc/hy3-free` (pinned for stateful work)
- **DB**: `slide_state.sqlite` (WAL mode, `PRAGMA busy_timeout=10000`)
- **Buffer TTL**: 300s (Volatile Decay Edict)
- **Emergency Credit**: 50 tokens per cycle

## Database Tables

Core: `documents`, `chunks`, `slides`, `jobs`, `overrides`, `pipeline_runs`
Advanced: `delivery_events`, `dlq_items`, `delivery_ledger`, `version_chunks`, `doc_versions`
Budgets: `volatility_budgets`, `arrival_log`, `ingress_budgets`
Quorum: `quorum_sessions`, `quorum_fragments`, `quorum_keyholders`
Scenarios: `scenario_graphs`, `scenario_nodes`, `scenario_edges`, `scenario_sessions`, `scenario_responses`
Credentials: `issued_credentials`
Relay: `relay_pins`, `relay_tokens`
Shadow: `shadow_tests`, `shadow_lockdown`
Edge: `edge_submissions`, `edge_api_keys`
