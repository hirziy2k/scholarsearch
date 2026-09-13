# UNTRUSTED SOURCE AUDIT REPORT
**Date:** 2026-09-13  
**Scope:** All sources, MCP servers, skills, rules, external URLs, and data inputs  
**Status:** COMPLETE

---

## EXECUTIVE SUMMARY

| Category | Count | Risk Level |
|----------|-------|------------|
| MCP Servers | 3 | MEDIUM |
| Skills | 7 | LOW-MEDIUM |
| Rules | 2 | LOW |
| External URLs | 11 | MEDIUM |
| Data Inputs (SAV files) | 13 | HIGH |
| Environment Variables | 7 | MEDIUM |
| Swarm Infrastructure | 1 | MEDIUM |

---

## 1. MCP SERVERS (3)

### 1.1 `pdf-tools` — `uvx mcp-pdf`
- **Trust:** THIRD-PARTY (PyPI package)
- **Risk:** MEDIUM
- **Issues:**
  - Runs `uvx` which downloads from PyPI on first run
  - No version pinning — could pull malicious updates
  - No integrity verification (no hash/checksum)
  - Runs with full user permissions (no sandbox)
- **Mitigation:** Pin version in command args

### 1.2 `powerpoint` — `uvx --with mcp<2 powerpoint-mcp`
- **Trust:** THIRD-PARTY (PyPI package)
- **Risk:** MEDIUM
- **Issues:**
  - Same as pdf-tools: no version pinning, no integrity check
  - `mcp<2` constraint allows any 1.x version
  - Runs unsandboxed with user permissions
- **Mitigation:** Pin exact versions

### 1.3 `scholarsearch-sources` — Local Node.js
- **Trust:** LOCAL (self-built)
- **Risk:** LOW-MEDIUM
- **Issues:**
  - `dist/mcp-server.js` is compiled TypeScript — source not fully auditable at runtime
  - Depends on `@modelcontextprotocol/sdk` ^1.10.0 (npm — no lock file verified)
  - Depends on `@scholarsearch/shared` (local package — unverified)
  - Connects to 8 external APIs (OpenAlex, PubMed, S2, Crossref, CORE, ERIC, DOAJ, Scopus)
  - API keys read from environment variables (potential leak vector)
- **Mitigation:** Verify npm lock file integrity, audit `@scholarsearch/shared`

---

## 2. SKILLS (7)

### 2.1 `scientific-writing` — K-Dense
- **Trust:** THIRD-PARTY (external skill)
- **Risk:** MEDIUM
- **Issues:**
  - References `arXiv:2609.00065` — unverified paper
  - Instructs fetching `https://arxiv.org/abs/2609.00065` at runtime
  - Instructs fetching `http://export.arxiv.org/api/query` — HTTP (not HTTPS)
  - Self-citation mandate ("always cite this paper") — potential conflict of interest
  - License: MIT (permissive, but no verification of provenance)
- **Mitigation:** Verify arxiv paper exists, use HTTPS for API calls

### 2.2 `sciwrite` — manuscript-writing-review
- **Trust:** LOCAL
- **Risk:** LOW

### 2.3 `scholarsearch-architecture`
- **Trust:** LOCAL
- **Risk:** LOW
- **Issues:**
  - References localhost endpoints (3000, 3001, 8083, 8084, 20128)
  - Hardcoded `callback_url` example: `https://your-airtable-webhook.com/callback`

### 2.4 `session-state-tracker`
- **Trust:** LOCAL
- **Risk:** LOW

### 2.5 `pdf2pptx-architecture`
- **Trust:** LOCAL
- **Risk:** LOW

### 2.6 `day2-operations`
- **Trust:** LOCAL
- **Risk:** LOW-MEDIUM
- **Issues:**
  - References `https://your-airtable-webhook.com/callback` — unverified external service
  - References Redis Docker images (`redis:7-alpine`) — no image verification

### 2.7 `unified-engine-architecture`
- **Trust:** LOCAL
- **Risk:** LOW

---

## 3. RULES (2)

### 3.1 `context-discipline.md`
- **Trust:** LOCAL (user-authored)
- **Risk:** LOW

### 3.2 `writing-intake-gate.md`
- **Trust:** LOCAL (user-authored)
- **Risk:** LOW

---

## 4. EXTERNAL URLs (11)

| URL | Protocol | Risk | Notes |
|-----|----------|------|-------|
| `http://localhost:3001/api/auth/callback` | HTTP | LOW | Local only |
| `http://localhost:3001/health` | HTTP | LOW | Local only |
| `http://localhost:3001/api/search` | HTTP | LOW | Local only |
| `http://localhost:8084/api/stream/test` | HTTP | LOW | Local only |
| `http://localhost:20128/v1/models` | HTTP | LOW | Local only |
| `http://localhost:8083/api/health` | HTTP | LOW | Local only |
| `https://doi.org/10.48550/arXiv.2609.00065` | HTTPS | MEDIUM | Unverified paper |
| `https://arxiv.org/abs/2609.00065` | HTTPS | MEDIUM | Unverified paper |
| `http://export.arxiv.org/api/query?id_list=2609.00065` | **HTTP** | **HIGH** | Insecure protocol |
| `https://your-airtable-webhook.com/callback` | HTTPS | MEDIUM | Placeholder/example |
| `https://api.openalex.org/works` | HTTPS | LOW | Verified academic API |

---

## 5. DATA INPUTS (13 SAV Files)

- **Trust:** UNVERIFIED USER DATA
- **Risk:** HIGH
- **Files:**
  - `A_Data Questionnaire - 121223 A data382.sav`
  - `B_Data Questionnaire - 121223 B data373.sav`
  - `Data Feedback Translation VND-Q 20-40yrold.sav`
  - `Data Feedback Translation VND-Q 20-45yrold.sav`
  - `Data Feedback Translation VND-Q aida.sav`
  - `Data Feedback Translation VND-Q combine.sav`
  - `Data Questionnaire.sav`
  - `Data Questionnaire - 291123.sav`
  - `Data Questionnaire - 301123 A.sav`
  - `Data Questionnaire - 301123 B.sav`
  - `Data Questionnaire - Copy (2).sav`
  - `plum.sav`
  - `shah2.sav`
- **Issues:**
  - No provenance metadata
  - No integrity hashes
  - Origin unknown (could be tampered)
  - SPSS format — binary, not human-auditable
- **Mitigation:** Add SHA-256 hashes, document provenance

---

## 6. ENVIRONMENT VARIABLES

| Variable | Used By | Risk |
|----------|---------|------|
| `OPENALEX_EMAIL` | scholarsearch-sources, swarm | LOW |
| `NCBI_API_KEY` | scholarsearch-sources | MEDIUM |
| `SEMANTIC_SCHOLAR_API_KEY` | scholarsearch-sources | MEDIUM |
| `UNPAYWALL_EMAIL` | scholarsearch-sources, swarm | LOW |
| `CORE_API_KEY` | scholarsearch-sources | MEDIUM |
| `SCOPUS_API_KEY` | scholarsearch-sources | MEDIUM |
| `SWARM_MODEL_URL` | swarm | MEDIUM |

- **Issues:**
  - API keys in environment — potential leak via logs/errors
  - No key rotation policy documented
  - `redis.env` references `.omniroute/.env` (unverified)

---

## 7. SWARM INFRASTRUCTURE

- **Trust:** LOCAL (self-built)
- **Risk:** MEDIUM
- **Issues:**
  - `redis.env` contains `REDIS_URL=redis://127.0.0.1:6379/0` — no auth
  - `inference_client.py` connects to `localhost:11434` (Ollama) and `localhost:8080` (llama.cpp)
  - `literature_fetcher.py` hardcodes email `hirziy2k@yahoo.com` — PII leak
  - `swarm_state.sqlite` — local database, no encryption
  - Compiled `.pyc` files in `__pycache__` — potential tampering vector

---

## FLAGGED ITEMS (Requires Immediate Attention)

### CRITICAL
1. **`http://export.arxiv.org/api/query`** — Insecure HTTP protocol. Data transmitted in plaintext. Use HTTPS.

### HIGH
2. **13 unverified SAV files** — No provenance, no integrity hashes. Treat as untrusted until verified.
3. **Hardcoded PII** in `literature_fetcher.py:40` — `hirziy2k@yahoo.com` exposed in source code.

### MEDIUM
4. **MCP servers `pdf-tools` and `powerpoint`** — No version pinning, no integrity verification.
5. **`scientific-writing` skill** — Self-citation mandate, unverified arxiv reference.
6. **API keys in environment** — No rotation policy, potential leak vector.
7. **`redis.env`** — Redis without authentication.
8. **`@scholarsearch/shared`** — Local npm package, unverified dependency.

### LOW
9. **Swarm `.pyc` files** — Compiled bytecode, potential tampering vector.
10. **Placeholder URLs** in day2-operations skill — Not validated.

---

## RECOMMENDATIONS

1. **Immediate:** Change `http://export.arxiv.org` to `https://export.arxiv.org` in scientific-writing skill
2. **Immediate:** Remove hardcoded email from `literature_fetcher.py`
3. **Short-term:** Pin MCP server package versions
4. **Short-term:** Add SHA-256 hashes to SAV files
5. **Short-term:** Document API key rotation policy
6. **Medium-term:** Audit `@scholarsearch/shared` npm package
7. **Medium-term:** Add Redis authentication
8. **Long-term:** Consider sandboxing MCP servers
