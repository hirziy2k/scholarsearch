# PDF-to-PPTX Enterprise Architecture (Reference)

> Self-contained reference for building a production-grade, serverless, CI/CD-gated
> PDF-to-PPTX conversion **platform**. This is a separate design from the opencode MCP
> conversion workflow in `../SKILL.md` — it describes the source tree in the project root
> (a FastAPI microservice + queue/worker + AWS serverless deployment). It is retained for
> reference only and is **not** auto-loaded as a skill.

## Architecture Layers (12 Phases)

### Phase 0: Pre-flight PDF Sanitization
**File:** `pdf_sandbox.py`
- Byte-level validation (no C parser dependency)
- Strip JavaScript, XFA forms, embedded files
- Zip bomb detection (compression ratio > 100:1)
- Validates magic bytes, xref table, EOF markers
- `sanitize_pdf()` one-call API returns `SanitizeResult` (safe, threats, warnings)

### Phase 1: PyMuPDF Primary Extraction
**File:** `pdf_extractor.py`
- Extract ALL data natively (text+coords, tables, vectors)
- Complexity analysis for selective augmentation
- TextBlock → TextLine → TextSpan hierarchy

### Phase 2: MCP Augmentation (Selective)
**File:** `mcp_augment.py`
- Only augment complex pages (max 10 calls per PDF)
- Semantic reading order via MCP-PDF tools
- Graceful fallback to PyMuPDF only
- `MCPSession` has startup timeout (5s default) + per-call timeout

### Phase 3: Dynamic Clustering
**File:** `pdf_to_pptx.py` (cluster_spans function)
- Group spans into logical blocks
- Layout-aware clustering using coordinates
- Support for columns, tables, headers

### Phase 4: Binary Validation
**File:** `orchestrator_v2.py` (ValidationEngine)
- Reject hallucinated tables
- Validate table structure (rows/cols/data consistency)
- Mark fallbacks for diagnostic stubs

### Phase 4.5: Semantic Classification
**File:** `theme_mapper.py`
- Role classification: TITLE, SUBTITLE, BODY, LIST_ITEM, COLUMN_HEADER, HEADER, FOOTER, CAPTION
- Theme color snapping to PPTX theme XML
- Layout index selection (Title Slide, Title+Content, Blank)

### Phase 4.6: Font Metric Emulation
**File:** `font_emulator.py`
- System font detection (Windows/Mac/Linux)
- Fallback mapping: Helvetica→Arial, Times→Times New Roman, etc.
- Width recalculation via avg_width ratio
- `should_embed_or_substitute()` decision
- Docker layer installs Liberation + DejaVu + MS core fonts for cross-platform determinism

### Phase 4.7: Collision Resolution
**File:** `collision_matrix.py`
- Detect overlapping bounding boxes (>20% horizontal overlap)
- Iterative push-down (max 5 iterations)
- Split to new slide at slide margins
- `resolve_collisions()` one-call API

### Phase 5: PPTX Rendering
**File:** `orchestrator_v2.py` (PPTXRenderer)
- Emu coordinate mapping (PT_TO_EMU = 12700)
- Theme-aware layout selection
- Binary validation integration

### Phase 5.5: Auto-Reflow Grouping
**File:** `reflow_grouping.py`
- Vertical stack detection
- Resize-to-fit text boxes
- Native GroupShape creation
- Word wrap enabled

### Phase 5.6: Metadata Preservation
**File:** `metadata_layer.py`
- Hyperlink binding (bbox overlap matching)
- Bookmark → TOC slide + core_properties.subject
- Alt-text preservation

### Phase 6: Conversion Summary Slide
**File:** `summary_slide.py`
- Human-readable audit log appended to PPTX
- Active features, font substitutions, collision resolutions
- Metadata preserved, security events
- Dark navy header with white title
- Empty sections auto-skipped

## Infrastructure Components

### Redis-Backed Job Queue
**File:** `job_queue.py`
- `JobQueue` abstract base class
- `RedisJobQueue` with sorted set index
- `MemoryJobQueue` fallback
- 24-hour TTL, SET NX locking

### Dead Letter Queue
**File:** `dead_letter_queue.py`
- MAX_RETRIES = 2 (poison pill detection)
- `RedisDLQ` with 7-day TTL
- Retry count tracking
- Phases completed logging
- `retry_from_dlq()` resets retry count

### Rate Limiting & Cost Guardrails
**File:** `rate_limiter.py`
- 3 tiers: Free (10MB, 5rpm, 50/day), Pro (50MB, 30rpm, 1K/day), Enterprise (200MB, 100rpm, 10K/day)
- `RateLimiter` sliding-window minute/daily quota + concurrent job tracking
- `CostGuardrails` — monthly budget (80% throttle, 90% stop)
- `APIKeyManager` — key-to-tier mapping (JSON/env)
- `RateLimitMiddleware` — `X-RateLimit-*` response headers
- Lambda cost estimation: $0.0000166667/GB-second

### FastAPI Microservice
**File:** `api_server.py` (19 endpoints)
- POST /v1/convert (multipart upload)
- GET /v1/jobs/{id} (poll) / download / stream (SSE)
- DELETE /v1/jobs/{id} (cancel)
- GET /v1/health (queue + DLQ size)
- GET /v1/dlq, POST /v1/dlq/{id}/retry
- POST /v1/feedback, GET /v1/feedback(/stats|/dashboard), POST /v1/feedback/{id}/promote
- POST /v1/auth/token, POST /v1/auth/{id}/consume

### BFF Authentication Proxy
**File:** `auth_proxy.py`
- `ScopedToken` — short-lived (15min), HMAC-signed, max 1 upload
- `AuthProxy` — issue/validate/consume/revoke; master key never leaves server
- Tier-based expiry: free=10min, pro=15min, enterprise=30min
- `StripeIntegration` — checkout→key provisioning, subscription deletion→revocation
- `generate_presigned_upload_url()` for client-side uploads

### Server-Sent Events Streaming with Replay Buffer
**File:** `streaming.py`, `replay_buffer.py`
- `StreamEvent` — event type + JSON payload + event ID + retry
- `JobStreamManager` — multi-client subscribe/publish per job
- `ReplayBuffer` — Redis list (LPUSH + LTRIM 200) + 1-hour TTL; in-memory fallback
- `SSEReplayManager` — replay historical events → `replay_complete` marker → live stream
- Endpoint: `GET /v1/jobs/{job_id}/stream`
- Events: `phase_start`, `phase_end`, `progress`, `complete`, `error`, 30s `keepalive`
- Partial replay support via `since_id` for clients reconnecting mid-stream

### Distributed Tracing
**File:** `telemetry.py`
- `ConversionTrace` with UUID trace_id
- `SpanHandle` context manager
- `StructuredLogger` for phase events
- `DiagnosticReport` HTML waterfall
- Self-contained HTML output

### Ephemeral Storage
**File:** `ephemeral_storage.py`
- Auto-detect: S3 → ramdisk → local
- S3 with SSE-S3 encryption + lifecycle rules
- 3-pass DOD-style secure wipe
- `StorageLifecycle` for store → process → wipe

### User Feedback Loop
**File:** `feedback_loop.py`
- `FeedbackCollector` — submit/rate/archive conversions
- `CITestSuitUpdater` — promote bad PDFs to CI curriculum
- `FeedbackDashboard` — branded HTML trends
- Endpoints: submit, list, stats, promote, dashboard

### Synthetic PDF Generation (Privacy-Safe)
**File:** `synthetic_generator.py`
- `StructuralMatrix` — geometry-only (no text content)
- `StructureExtractor` — 3 paths (PDF, error log, cluster data), discards all strings
- `SyntheticPDFGenerator` — reportlab (or raw-bytes) rebuilds with Lorem Ipsum + gray rectangles
- `safe_promote_to_ci()` — extract→scrub→clone as `synth_*` PDF + `_matrix.json`
- **Never persists original user data** — satisfies privacy mandate

### Vector Fuzzing & Metadata Annihilation
**File:** `vector_fuzzer.py`
- `VectorFuzzer` — ±3% spatial jitter on all coordinates (never negative, never exceeds page bounds)
- `fuzz_font_name()` — CustomFont-01, SystemSansSerif, SystemSerif, SystemMono
- `strip_metadata()` — removes /Author, /Creator, /Producer, /Title, /Subject, /Keywords, /ModDate, /CreationDate, XMP blocks, URI strings
- `fuzz_structural_matrix()` — jitters text blocks, table cells, vector paths; genericizes fonts; strips URIs; deterministic hash for audit
- `verify_no_leakage()` — confirms no identical coordinates, no matching font names, no URIs remain
- `safe_promote_to_ci_v2()` — full pipeline: extract → fuzz → annihilate → generate synthetic → save with audit hash

### Cross-Platform Compatibility Matrix
**File:** `cross_platform.py`
- `PlatformRenderer` enum: POWERPOINT, GOOGLE_SLIDES, KEYNOTE, LIBREOFFICE
- `RenderTarget` — per-platform capabilities (ignores_custom_spacing, overrides_font_fallback, supports_alternate_content)
- `CrossPlatformEngine` — font mapping table: Helvetica→Arial/Roboto/Helvetica, Times→Times New Roman/Roboto Serif/Times, etc.
- `inject_alternate_content()` — wraps in `mc:AlternateContent` (PowerPoint gets full, web gets simplified)
- `GoogleSlidesOptimizer` — forces single spacing, maps to Google Fonts, adds `<a:fontRef>` hints
- `KeynoteOptimizer` — maps to Apple system fonts (Helvetica Neue, Courier)
- `CrossPlatformValidator` — validates XML, counts AlternateContent, checks font fallbacks
- `apply_cross_platform(prs, platform)` — one-call integration

### Visual Branding
**File:** `branding.py` — strict 3-color system
- Canvas: `#FAFAFA` (off-white), Charcoal: `#1A1A1A`, Accent: `#F5C518` (banana-yellow)
- `BrandTheme.html_wrapper()` — self-contained branded HTML
- `BrandedDiagnosticReport`, `BrandedSummarySlide`
- `apply_branding()` monkey-patches startup

## Deployment

### Docker (Multi-Stage)
**File:** `Dockerfile`
- Builder: compile dependencies
- Runtime: Liberation + DejaVu + MS core fonts (Arial, Times New Roman, Courier)
- Non-root `pptxuser` user
- Health check on /v1/health
- `fc-cache -fv` for deterministic rendering

### Docker Compose
**File:** `docker-compose.yml`
- API service + Redis 7
- Port 8000, volume mounts

### CI/CD (GitHub Actions)
**Files:** `.github/workflows/ci.yml`, `deploy.yml`, `dependency-check.yml`, `.github/dependabot.yml`
- 51-document curriculum gate
- 99.7% structural integrity threshold
- Organic hostile tests, concurrency stress test, Docker build + health check
- Dependabot: weekly pip, monthly Docker, weekly GH Actions
- Weekly `pip-audit` security scan

### Serverless (AWS)
**File:** `serverless_handler.py`, `deploy/template.yaml`
- Lambda + SQS + DynamoDB + S3
- ConversionQueue with DLQ (maxReceiveCount=3)
- StorageBucket: uploads expire 1 day, outputs 7 days, AES256
- ConversionFunction: 300s timeout, 1024MB, SQS trigger
- Pay-per-execution (zero idle cost)

### Local CI Gate
**File:** `ci_gate.py`
- Mirrors GitHub Actions locally
- `--fast` flag skips organic tests
- Parses results.json for 99.7% score

## Low-Code Integration
**Files:** `docs/integrations/`
- `openapi.yaml` — strict OpenAPI 3.0 spec
- `make_com.json` — Make.com module + polling aggregator
- `airtable_automation.js` — Airtable Automation script
- `bubble_io_connector.json` — Bubble.io API Connector

## Design Patterns

### Graceful Degradation
Every layer has try/except with fallback:
```python
try:
    from advanced_module import advanced_function
    ADVANCED_AVAILABLE = True
except ImportError:
    ADVANCED_AVAILABLE = False
```

### Dual-Mode Operation
Queue backends, storage backends, DLQ backends, replay buffers all support Redis + in-memory fallback.

### Structured Telemetry
Every phase wrapped in trace spans:
```python
with trace.start_span("phase_name") if trace else None:
    # phase logic
```

### Binary Validation
Reject hallucinated content before rendering:
```python
if not validation_engine.validate(data):
    return fallback_stub()
```

### Defense in Depth (Security)
1. Pre-flight sandbox strips JS/XFA before any parsing
2. Ephemeral storage — inputs wiped after success, S3 lifecycle 1/7 days
3. BFF proxy — master key never reaches browser, scoped 15-min JWTs
4. Rate limiter + cost guardrails — tiered quotas, budget throttle/stop
5. Synthetic CI promotion — never persists user data to repo
6. Vector fuzzing — ±3% spatial jitter destroys original geometry
7. Metadata annihilation — strips author tags, URIs, font fingerprints
8. Non-root Docker user, minimal slim base image

### Privacy-by-Design (Feedback Loop)
1. User flags bad conversion
2. Extract structural matrix (geometry only)
3. Apply ±3% spatial jitter
4. Genericize all font names
5. Strip all metadata and URIs
6. Generate synthetic PDF with Lorem Ipsum
7. Save fuzzed matrix JSON for audit trail
8. **Original user data never touches CI repo**

## Key Metrics (Baseline)

| Metric | Value |
|--------|-------|
| Phase 1 coordinates | ±1 EMU |
| 51 synthetic PDFs | 51/51 pass |
| 10 organic hostile PDFs | 7/10 pass (3 timeouts = processing time) |
| 20 concurrent requests | 20/20 pass |
| Structural audit | 99.7% (356/357 checks) |
| Throughput | 0.83 conv/s |
| Peak memory | 150 MB |
| API endpoints | 19 |
| CI gate threshold | ≥99.7% |
| SSE replay buffer | 200 events / 1hr TTL |
| Vector fuzzing jitter | ±3% spatial |

## Usage Pattern

When building similar document conversion pipelines:

1. **Start with PyMuPDF primary** — fastest extraction, no MCP dependency
2. **Add selective augmentation** — complexity analysis → MCP only for hard pages
3. **Dynamic clustering** — don't hardcode layouts, group by coordinates
4. **Binary validation** — reject hallucinations before rendering
5. **Theme awareness** — role classification + color snapping
6. **Font emulation** — detect missing fonts, force cross-platform fallbacks
7. **Collision resolution** — detect overlaps after font expansion
8. **Auto-reflow** — enable native PowerPoint resize-to-fit
9. **Metadata preservation** — hyperlinks, bookmarks, alt-text
10. **Summary slide** — end-user transparency
11. **Telemetry** — trace every phase, generate waterfall reports
12. **Persistent queue** — Redis + DLQ for production reliability
13. **Rate limit early** — tiered quotas prevent bill shock
14. **BFF auth** — keep master keys server-side, issue scoped JWTs
15. **SSE streaming** — real-time progress without polling
16. **Replay buffer** — instant history replay on reconnect
17. **Feedback loop** — capture bad outputs, promote synthetic clones to CI
18. **Cross-platform** — mc:AlternateContent + Google Font mapping for web/Keynote
19. **Vector fuzzing** — ±3% jitter + metadata annihilation for privacy
20. **CI/CD gate** — block merges below the structural integrity threshold
