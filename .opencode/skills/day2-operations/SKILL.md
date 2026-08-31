---
name: day2-operations
description: Use when managing Day 2 operational safeguards for the Unified Intelligence Engine. Covers the Adversarial Shadow-Test Pipeline (model drift detection via golden chunks and Merkle roots), Edge Integration Layer (webhook receivers for Airtable/Softr/Zapier, platform adapters, rate limiting, async ingestion queue), and Automated Disaster Recovery Runbook Generator (dependency mapping, cold start sequences, service recovery, quorum recovery, emergency procedures). Also covers the operational baseline edict (no new features until ops are secured).
---

# Day 2 Operations — Operational Safeguards

## Purpose

Secures the operational lifecycle of the Unified Intelligence Engine against three terminal risks of live production:
1. **Model Drift** — LLM degradation silently poisoning outputs
2. **Ghost Town** — No automated user-acquisition pipeline
3. **Sole Maintainer** — Cognitive load of debugging a 33-module system

## Core Files

| File | Purpose |
|------|---------|
| `shadow_test.py` | Adversarial Shadow-Test Pipeline |
| `edge_integration.py` | Edge Integration Layer (webhook receivers) |
| `dr_runbook.py` | Automated Disaster Recovery Runbook Generator |

---

## 1. Adversarial Shadow-Test Pipeline

### Purpose
Detects model drift by running pre-solved "Golden Chunks" through the scenario compiler and comparing outputs against deterministic Merkle roots. Triggers global lockdown on drift.

### How It Works
1. **Golden Chunks**: 3 pre-solved test vectors (optometry, finance, crypto)
2. **Merkle Root**: Deterministic hash of expected scenario structure (nodes, edges, rubric keys, domain)
3. **Shadow Runner**: Background daemon runs every 72 hours
4. **Lockdown**: Halts all production ingestion until operator intervention
5. **Audit Trail**: Every shadow test result logged with timestamps

### Golden Chunks
| ID | Domain | Input | Expected |
|----|--------|-------|----------|
| `golden_optometry_snells_law` | optometry | Snells Law text | 1 node, 4 edges |
| `golden_xauusd_basic` | finance | XAU/USD spot data | 1 node, 4 edges |
| `golden_stomp_tokenomics` | crypto | STOMP Coin tokenomics | 1 node, 4 edges |

### API Endpoints
- `GET /api/shadow/status` — Current lockdown state, failure count, recent tests
- `POST /api/shadow/run` — Manual shadow test cycle
- `POST /api/shadow/unlock` — Lift lockdown (operator action)

### Lockdown Behavior
- **Trigger**: 2+ consecutive shadow test failures
- **Effect**: `POST /api/execute` returns `423 Locked`
- **Recovery**: `POST /api/shadow/unlock` after investigation

### Configuration
- `SHADOW_TEST_INTERVAL`: 259200 seconds (72 hours)
- `_max_failures_before_lockdown`: 2
- `MIN_BUDGET`: 10 tokens minimum per cycle

---

## 2. Edge Integration Layer

### Purpose
Bridges the headless API to outward-facing low-code platforms (Airtable, Softr, Zapier). Maps student/stakeholder interactions directly into ingestion and scenario endpoints.

### How It Works
1. **Webhook Receiver**: POST `/api/edge/webhook/<platform>`
2. **Platform Adapters**: Normalize platform-specific payloads
3. **Queue**: Async ingestion via internal message queue
4. **Auto-Evaluate**: Answer all questions with 'correct'
5. **Credential Mint**: Mint credential on completion
6. **Callback**: POST results back to platform

### Supported Platforms
| Platform | Auth Header | Rate Limit | Payload Format |
|----------|-------------|------------|----------------|
| `airtable` | `X-Airtable-Secret` | 60/min | `fields.Name`, `fields.Course`, `fields.Document` |
| `softr` | `X-Softr-Secret` | 30/min | `data.student_name`, `data.module`, `data.content` |
| `zapier` | `X-Zapier-Secret` | 100/min | `student.name`, `student.course`, `student.document` |
| `generic` | `X-Webhook-Secret` | 20/min | `user.id`, `document.text`, `document.format` |

### API Endpoints
- `POST /api/edge/webhook/airtable` — Airtable webhook
- `POST /api/edge/webhook/softr` — Softr webhook
- `POST /api/edge/webhook/zapier` — Zapier webhook
- `POST /api/edge/webhook/generic` — Generic webhook
- `GET /api/edge/stats` — Submission statistics
- `GET /api/edge/submissions` — List submissions
- `GET /api/edge/submissions/<id>` — Get submission
- `POST /api/edge/keygen` — Generate API key

### Payload Examples

#### Airtable
```json
{
  "table": "Students",
  "action": "create",
  "fields": {
    "Name": "John Doe",
    "Email": "john@example.com",
    "Course": "Refraction Module",
    "Document": "Snells Law text..."
  },
  "callback_url": "https://your-airtable-webhook.com/callback"
}
```

#### Softr
```json
{
  "event": "form_submit",
  "data": {
    "student_name": "Jane Doe",
    "student_email": "jane@example.com",
    "module": "STOMP Coin Analysis",
    "content": "Tokenomics text...",
    "format": "web"
  }
}
```

### Pipeline Flow
```
Webhook → Rate Limit → Normalize → Queue → Scenario Compile → Evaluate → Credential Mint → Callback
```

### Database Tables
- `edge_submissions`: All submissions with status tracking
- `edge_api_keys`: Platform API keys (active/inactive)

---

## 3. Automated Disaster Recovery Runbook

### Purpose
Generates a deterministic, zero-knowledge Runbook that maps every dependency, restart sequence, and recovery step so a colleague can cold-start the system without the original operator.

### How It Works
1. **Dependency Mapper**: Auto-discovers all Python imports, file dependencies, service dependencies
2. **Sequence Generator**: Produces step-by-step recovery procedures
3. **Health Validator**: Checks each step's success criteria
4. **Export**: Produces JSON summary and text runbook

### Runbook Sections (10)
| Section | Steps | Description |
|---------|-------|-------------|
| 1. Prerequisites | 5 | Python, API key, directory, SQLite, template |
| 2. Cold Start Sequence | 6 | Start OmniRoute → Wait → Verify → Start Engine → Wait → Verify |
| 3. Service Recovery | 2 | OmniRoute/Orchestrator restart |
| 4. Data Recovery | 4 | WAL mode, hash chain, orphaned runs, backup |
| 5. Quorum Recovery | 3 | Status check, keyholder fragments, emergency bypass |
| 6. Shadow Test Recovery | 4 | Lockdown check, investigate, manual test, lift |
| 7. Edge Integration Recovery | 4 | Stats, stuck submissions, API keys, re-generation |
| 8. Health Checks | 6 | Engine, budget, topology, relay, dashboard, diagnostic |
| 9. Emergency Procedures | 4 | Pipeline abort, DLQ flush, budget reset, nuclear restart |
| 10. Dependency Map | 0 | Full Python module dependency map |

### API Endpoints
- `GET /api/dr/runbook` — Runbook summary (sections, environment, services)
- `GET /api/dr/runbook/hash` — Content hash for integrity verification
- `POST /api/dr/export` — Export filepath

### Cold Start Sequence (Critical Path)
```
1. Start OmniRoute:     cmd.exe /c omniroute serve --daemon --no-open --port 20128
2. Wait 10s:            Start-Sleep -Seconds 10
3. Verify OmniRoute:    GET http://localhost:20128/v1/models
4. Start Engine:        python .opencode/orchestrate.py
5. Wait 5s:             Start-Sleep -Seconds 5
6. Verify Engine:       GET http://localhost:8083/api/health
```

### Emergency Procedures
```
Pipeline Abort:    POST /api/command {"command": "<signed> PIPELINE ABORT"}
DLQ Flush:         POST /api/command {"command": "<signed> DLQ FLUSH"}
Budget Reset:      POST /api/command {"command": "<signed> BUDGET RESET"}
Nuclear Restart:   Get-Process python* | Stop-Process -Force; python orchestrate.py
```

---

## Dashboard Integration

The operational dashboard (`GET /dashboard`) includes three new sections:

### Shadow Test Card
- Lockdown status (CLEAR/ACTIVE)
- Consecutive failures
- Golden chunk count
- Test interval
- Recent test results

### Edge Integration Card
- Total submissions
- Submissions by platform
- Submissions by status (queued/processing/completed/failed)

### Credentials Card
- Total credentials issued

---

## Operational Baseline Edict

**The architecture is locked. The code is frozen.**

Until Day 2 operations are secured:
- No new features
- No new divergence layers
- No new modules
- Focus on: reliability, monitoring, recovery, documentation

The purpose of the engineering gauntlet was to reclaim cognitive bandwidth, not consume it. If the dashboard requires constant attention, the automation has failed.
