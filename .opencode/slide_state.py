#!/usr/bin/env python3
"""Zero-Context Slide State Machine - SQLite-backed persistence for PDF->PPTX.

Implements the "Zero-Context State Machine" constraint: all document state is
pushed to a LOCAL SQLite database by the MCP tools. The active LLM retains ZERO
memory of PDF content between steps. The model queries only the specific chunks
needed to build the CURRENT slide. On OmniRoute failover, the new model reads the
database (e.g. "slide 4 pending") instead of relying on any relay context-
summary - eliminating both the data-sovereignty leak and the state-shatter risk.

Async parallel dispatch: each chunk becomes an independent job in the ledger.
Multiple workers can claim jobs simultaneously. No linear cursor.

Usage (CLI):
  python slide_state.py init --source <file> --pages <N>
  python slide_state.py ingest --doc <id> --page <N> --chunk <idx> --text "<content>"
  python slide_state.py chunks --doc <id> [--page <N>]
  python slide_state.py create-jobs --doc <id>
  python slide_state.py claim-job --doc <id> [--model <name>]
  python slide_state.py complete-job --doc <id> --slide <idx> --title <t> [--bullets "..."] [--notes "..."] [--source-page <N>]
  python slide_state.py fail-job --doc <id> --slide <idx> [--error <msg>]
  python slide_state.py override-job --doc <id> --slide <idx> --title <t> [--bullets "..."] [--notes "..."] [--source-page <N>]
  python slide_state.py jobs --doc <id>
  python slide_state.py slide get --doc <id> --slide <idx>
  python slide_state.py slide status-set --doc <id> --slide <idx> --status <s>
  python slide_state.py slides-detail --doc <id>
  python slide_state.py rollback-check --doc <id> [--threshold <seconds>]
  python slide_state.py status --doc <id>

States: pending -> building -> done   (per slide, via jobs)
Jobs:   pending -> claimed -> done/failed/override
"""

import sqlite3
import sys
import os
import json
import threading
import queue

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "slide_state.sqlite",
)

# ---------------- Single-Writer Thread ----------------
# All writes go through this queue. A single thread consumes and executes them.
# Worker processes push (sql, params) tuples. Zero concurrent write collisions.
_write_queue = queue.Queue(maxsize=10000)
_writer_thread = None
_writer_lock = threading.Lock()


def _writer_loop():
    """Single-writer thread: consumes SQL writes from the queue."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.executescript(SCHEMA)
    while True:
        try:
            item = _write_queue.get(timeout=60)
            if item is None:
                break
            sql, params = item
            conn.execute(sql, params or ())
            conn.commit()
        except queue.Empty:
            continue
        except Exception as e:
            sys.stderr.write("DB writer error: {}\n".format(e))
            sys.stderr.flush()
    conn.close()


def _ensure_writer():
    """Start the single-writer thread if not running."""
    global _writer_thread
    with _writer_lock:
        if _writer_thread is None or not _writer_thread.is_alive():
            _writer_thread = threading.Thread(target=_writer_loop, daemon=True)
            _writer_thread.start()


def db_write(sql, params=None):
    """Queue a write operation for the single-writer thread."""
    _ensure_writer()
    _write_queue.put((sql, params), timeout=5)


def db_read(sql, params=None):
    """Direct read (safe for concurrent reads in WAL mode)."""
    conn = connect()
    row = conn.execute(sql, params or ()).fetchall()
    conn.close()
    return row

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    page_count  INTEGER NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS chunks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id            INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page              INTEGER NOT NULL,
    chunk_index       INTEGER NOT NULL,
    content           TEXT NOT NULL,
    precursor_context TEXT NOT NULL DEFAULT '',
    source_type       TEXT NOT NULL DEFAULT 'pdf',
    source_url        TEXT NOT NULL DEFAULT '',
    ttl_seconds       INTEGER,
    expires_at        TEXT,
    clearance_tier    TEXT NOT NULL DEFAULT 'Public'
                      CHECK(clearance_tier IN ('Public','Internal','Restricted','Confidential')),
    clearance_domains TEXT NOT NULL DEFAULT '["General"]',
    UNIQUE(doc_id, page, chunk_index)
);
CREATE TABLE IF NOT EXISTS slides (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id            INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    slide_index       INTEGER NOT NULL,
    title             TEXT NOT NULL DEFAULT '',
    bullets           TEXT NOT NULL DEFAULT '[]',
    notes             TEXT NOT NULL DEFAULT '',
    source_page       INTEGER,
    chunk_id          INTEGER REFERENCES chunks(id),
    layout_directive  TEXT NOT NULL DEFAULT 'content',
    visual_metadata   TEXT NOT NULL DEFAULT '{}',
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK(status IN ('pending','building','done','failed','override')),
    attempt           INTEGER NOT NULL DEFAULT 0,
    locked_at         TEXT,
    UNIQUE(doc_id, slide_index)
);
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id      INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    slide_index INTEGER NOT NULL,
    chunk_id    INTEGER NOT NULL REFERENCES chunks(id),
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','claimed','done','failed','override')),
    model       TEXT,
    started_at  TEXT,
    completed_at TEXT,
    error       TEXT,
    UNIQUE(doc_id, slide_index)
);
CREATE TABLE IF NOT EXISTS rlhf_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id          INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    slide_index     INTEGER NOT NULL,
    original_chunk  TEXT NOT NULL,
    llm_output      TEXT NOT NULL,
    human_correction TEXT NOT NULL,
    failure_reason  TEXT NOT NULL DEFAULT '',
    model_used      TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL UNIQUE,
    doc_id          INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','running','done','failed')),
    current_step    TEXT NOT NULL DEFAULT 'init',
    payload_json    TEXT NOT NULL DEFAULT '{}',
    result_json     TEXT NOT NULL DEFAULT '{}',
    error           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.executescript(SCHEMA)
    return conn


def now():
    import datetime
    return datetime.datetime.utcnow().isoformat()


# ---------------- Documents ----------------
def init_doc(source_file, page_count):
    conn = connect()
    cur = conn.execute(
        "INSERT INTO documents(source_file, page_count) VALUES(?,?)",
        (source_file, page_count),
    )
    doc_id = cur.lastrowid
    conn.commit()
    conn.close()
    return doc_id


# ---------------- Chunks ----------------
def add_chunk(doc_id, page, chunk_index, content, precursor_context="", clearance_tier="Public", clearance_domains=None):
    if clearance_domains is None:
        clearance_domains = ["General"]
    domains_json = json.dumps(clearance_domains) if isinstance(clearance_domains, list) else clearance_domains
    db_write(
        "INSERT OR REPLACE INTO chunks(doc_id, page, chunk_index, content, precursor_context, clearance_tier, clearance_domains) VALUES(?,?,?,?,?,?,?)",
        (doc_id, page, chunk_index, content, precursor_context, clearance_tier, domains_json),
    )


def query_chunks(doc_id, page=None):
    conn = connect()
    if page is None:
        rows = conn.execute(
            "SELECT chunk_index, page, content FROM chunks WHERE doc_id=? ORDER BY page, chunk_index",
            (doc_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT chunk_index, page, content FROM chunks WHERE doc_id=? AND page=? ORDER BY chunk_index",
            (doc_id, page),
        ).fetchall()
    conn.close()
    return [{"chunk_index": r[0], "page": r[1], "content": r[2]} for r in rows]


# ---------------- Slides ----------------
def create_slide(doc_id, slide_index, title, bullets, notes="", source_page=None):
    conn = connect()
    conn.execute(
        """INSERT OR REPLACE INTO slides
           (doc_id, slide_index, title, bullets, notes, source_page, status)
           VALUES(?,?,?,?,?,?,'pending')""",
        (doc_id, slide_index, title, json.dumps(bullets) if isinstance(bullets, list) else bullets,
         notes, source_page),
    )
    conn.commit()
    conn.close()


def get_slide(doc_id, slide_index):
    conn = connect()
    row = conn.execute(
        "SELECT id, slide_index, title, bullets, notes, source_page, status FROM slides WHERE doc_id=? AND slide_index=?",
        (doc_id, slide_index),
    ).fetchone()
    conn.close()
    if not row:
        return None
    def safe_json(s):
        try:
            return json.loads(s) if s else []
        except (json.JSONDecodeError, TypeError):
            return [s] if s else []
    return {
        "id": row[0], "slide_index": row[1], "title": row[2],
        "bullets": safe_json(row[3]), "notes": row[4],
        "source_page": row[5], "status": row[6],
    }


def set_slide_status(doc_id, slide_index, status):
    conn = connect()
    conn.execute("UPDATE slides SET status=? WHERE doc_id=? AND slide_index=?",
                 (status, doc_id, slide_index))
    conn.commit()
    conn.close()


# ---------------- Job Ledger (async parallel dispatch) ----------------
def create_jobs_for_doc(doc_id):
    """Create one job per chunk for parallel slide generation.

    Each chunk becomes an independent job. The model reads its own chunk
    from SQLite, generates a slide, and writes back atomically. No linear
    cursor — all pending jobs can be claimed simultaneously.
    """
    from datetime import datetime
    conn = connect()
    try:
        chunks = conn.execute(
            "SELECT id, page, chunk_index FROM chunks WHERE doc_id=? ORDER BY page, chunk_index",
            (doc_id,),
        ).fetchall()
        created = []
        for i, (chunk_id, page, chunk_idx) in enumerate(chunks, 1):
            try:
                conn.execute(
                    "INSERT INTO jobs(doc_id, slide_index, chunk_id, status) VALUES(?,?,?,'pending')",
                    (doc_id, i, chunk_id),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO slides(doc_id, slide_index, title, bullets, notes, source_page, chunk_id, status) "
                    "VALUES(?,?,?,?,?,?,?,'pending')",
                    (doc_id, i, '', '[]', '', page, chunk_id),
                )
                created.append({"slide_index": i, "chunk_id": chunk_id, "page": page})
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        conn.close()
        return {"ok": True, "jobs_created": len(created), "jobs": created}
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}


def claim_next_job(doc_id, model="unknown"):
    """Claim the next pending job for parallel execution.

    Returns the job details (chunk content + slide index) so the model
    can generate the slide. Multiple workers can call this simultaneously —
    each gets a different pending job via atomic UPDATE+RETURN.
    """
    from datetime import datetime
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        job = conn.execute(
            "SELECT j.id, j.slide_index, j.chunk_id, c.page, c.content, c.precursor_context "
            "FROM jobs j JOIN chunks c ON c.id = j.chunk_id "
            "WHERE j.doc_id=? AND j.status='pending' "
            "ORDER BY j.slide_index LIMIT 1",
            (doc_id,),
        ).fetchone()
        if not job:
            conn.execute("COMMIT")
            conn.close()
            return None
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE jobs SET status='claimed', model=?, started_at=? WHERE id=?",
            (model, now, job[0]),
        )
        conn.execute(
            "UPDATE slides SET status='building', attempt=attempt+1, locked_at=? "
            "WHERE doc_id=? AND slide_index=?",
            (now, doc_id, job[1]),
        )
        conn.commit()
        conn.close()
        return {
            "job_id": job[0], "slide_index": job[1], "chunk_id": job[2],
            "page": job[3], "content": job[4], "precursor_context": job[5] or "",
            "model": model, "claimed_at": now,
        }
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}


def complete_job(doc_id, slide_index, title, bullets, notes="", source_page=None,
                  layout_directive="content", visual_metadata=None):
    """Mark a job as done after Gate 1 + Gate 2 validation pass.

    Writes the slide content and marks both slide and job as done.
    """
    conn = connect()
    try:
        bullets_json = json.dumps(bullets) if isinstance(bullets, list) else bullets
        vm_json = json.dumps(visual_metadata) if visual_metadata else "{}"
        conn.execute(
            "UPDATE slides SET title=?, bullets=?, notes=?, source_page=?, "
            "layout_directive=?, visual_metadata=?, status='done', "
            "locked_at=NULL WHERE doc_id=? AND slide_index=?",
            (title, bullets_json, notes, source_page, layout_directive, vm_json, doc_id, slide_index),
        )
        conn.execute(
            "UPDATE jobs SET status='done', completed_at=datetime('now') "
            "WHERE doc_id=? AND slide_index=?",
            (doc_id, slide_index),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "committed_slide": slide_index}
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}


def fail_job(doc_id, slide_index, error="unknown"):
    """Mark a job as failed (Gate 1/2 failure). Slide stays for repair router."""
    conn = connect()
    try:
        conn.execute(
            "UPDATE slides SET status='failed', locked_at=NULL WHERE doc_id=? AND slide_index=?",
            (doc_id, slide_index),
        )
        conn.execute(
            "UPDATE jobs SET status='failed', error=?, completed_at=datetime('now') "
            "WHERE doc_id=? AND slide_index=?",
            (error, doc_id, slide_index),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "failed_slide": slide_index, "error": error}
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}


def override_job(doc_id, slide_index, title, bullets, notes="", source_page=None):
    """HITL override: manually approve a slide that failed heuristic checks.

    Sets status='override' — bypasses all validation gates.
    """
    conn = connect()
    try:
        bullets_json = json.dumps(bullets) if isinstance(bullets, list) else bullets
        conn.execute(
            "UPDATE slides SET title=?, bullets=?, notes=?, source_page=?, status='override', "
            "locked_at=NULL WHERE doc_id=? AND slide_index=?",
            (title, bullets_json, notes, source_page, doc_id, slide_index),
        )
        conn.execute(
            "UPDATE jobs SET status='override', completed_at=datetime('now') "
            "WHERE doc_id=? AND slide_index=?",
            (doc_id, slide_index),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "overridden_slide": slide_index}
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}


def get_jobs(doc_id):
    """Return all jobs with their status for the HITL dashboard."""
    conn = connect()
    rows = conn.execute(
        "SELECT j.id, j.slide_index, j.chunk_id, j.status, j.model, j.started_at, j.completed_at, j.error, "
        "c.page, c.content "
        "FROM jobs j JOIN chunks c ON c.id = j.chunk_id "
        "WHERE j.doc_id=? ORDER BY j.slide_index",
        (doc_id,),
    ).fetchall()
    conn.close()
    return [{"job_id": r[0], "slide_index": r[1], "chunk_id": r[2], "status": r[3],
             "model": r[4], "started_at": r[5], "completed_at": r[6], "error": r[7],
             "page": r[8], "content_preview": r[9][:100] if r[9] else ""} for r in rows]


# ---------------- RLHF Ledger (Synthetic Fine-Tuning) ----------------
def record_override(doc_id, slide_index, original_chunk, llm_output, human_correction,
                    failure_reason="", model_used=""):
    """Record a human override for future LoRA fine-tuning.

    Captures the triple (chunk, LLM output, human correction) as a
    training pair for Reinforcement Learning from Human Feedback.
    """
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO rlhf_ledger(doc_id, slide_index, original_chunk, llm_output, "
            "human_correction, failure_reason, model_used) VALUES(?,?,?,?,?,?,?)",
            (doc_id, slide_index, original_chunk, llm_output, human_correction,
             failure_reason, model_used),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "recorded": True}
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}


def export_rlhf_jsonl(doc_id=None):
    """Export RLHF ledger as JSONL for LoRA training."""
    conn = connect()
    if doc_id:
        rows = conn.execute(
            "SELECT original_chunk, llm_output, human_correction, failure_reason "
            "FROM rlhf_ledger WHERE doc_id=? ORDER BY created_at", (doc_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT original_chunk, llm_output, human_correction, failure_reason "
            "FROM rlhf_ledger ORDER BY created_at"
        ).fetchall()
    conn.close()
    lines = []
    for r in rows:
        lines.append(json.dumps({
            "input": r[0], "rejected": r[1], "chosen": r[2], "reason": r[3]
        }))
    return "\n".join(lines)


# ---------------- Temporal Ingestion (Live Webhook Data) ----------------
def add_live_chunk(doc_id, page, chunk_index, content, source_url="",
                   ttl_seconds=3600, clearance_tier="Public", clearance_domains=None):
    """Ingest a live chunk from a webhook with TTL."""
    from datetime import datetime, timedelta
    if clearance_domains is None:
        clearance_domains = ["General"]
    domains_json = json.dumps(clearance_domains) if isinstance(clearance_domains, list) else clearance_domains
    try:
        expires = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        db_write(
            "INSERT OR REPLACE INTO chunks(doc_id, page, chunk_index, content, "
            "source_type, source_url, ttl_seconds, expires_at, clearance_tier, clearance_domains) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (doc_id, page, chunk_index, content, "live", source_url, ttl_seconds, expires, clearance_tier, domains_json),
        )
        return {"ok": True, "expires_at": expires}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def sweep_expired_chunks():
    """Remove expired live chunks. Returns count of removed chunks."""
    from datetime import datetime
    conn = connect()
    try:
        now = datetime.utcnow().isoformat()
        expired = conn.execute(
            "SELECT id FROM chunks WHERE source_type='live' AND expires_at IS NOT NULL AND expires_at < ?",
            (now,),
        ).fetchall()
        if expired:
            ids = [r[0] for r in expired]
            placeholders = ",".join("?" * len(ids))
            conn.execute(f"DELETE FROM chunks WHERE id IN ({placeholders})", ids)
        conn.commit()
        conn.close()
        return {"expired": len(expired)}
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}


def check_stale_jobs(doc_id, max_age_seconds=120):
    """Detect and auto-rollback stale claimed jobs (latency-threshold stop-loss)."""
    from datetime import datetime
    conn = connect()
    try:
        stale = conn.execute(
            "SELECT j.id, j.slide_index, j.started_at FROM jobs j "
            "WHERE j.doc_id=? AND j.status='claimed' AND j.started_at IS NOT NULL",
            (doc_id,),
        ).fetchall()
        rolled_back = []
        for job_id, si, started_at in stale:
            if started_at is None:
                continue
            age = (datetime.utcnow() - datetime.fromisoformat(started_at)).total_seconds()
            if age > max_age_seconds:
                conn.execute("UPDATE jobs SET status='pending', started_at=NULL, model=NULL WHERE id=?", (job_id,))
                conn.execute("UPDATE slides SET status='pending', locked_at=NULL WHERE doc_id=? AND slide_index=?", (doc_id, si))
                rolled_back.append({"slide_index": si, "age_seconds": round(age)})
        conn.commit()
        conn.close()
        return {"checked": len(stale), "rolled_back": rolled_back, "threshold_seconds": max_age_seconds}
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}


def get_slides_detail(doc_id):
    """Return all slides with full detail for the audit UI."""
    conn = connect()
    rows = conn.execute(
        "SELECT slide_index, title, bullets, notes, source_page, status, attempt, locked_at "
        "FROM slides WHERE doc_id=? ORDER BY slide_index",
        (doc_id,),
    ).fetchall()
    conn.close()
    def safe_json(s):
        try:
            return json.loads(s) if s else []
        except (json.JSONDecodeError, TypeError):
            return [s] if s else []
    return [{"slide_index": r[0], "title": r[1], "bullets": safe_json(r[2]), "notes": r[3],
             "source_page": r[4], "status": r[5], "attempt": r[6], "locked_at": r[7]} for r in rows]


def status(doc_id):
    conn = connect()
    doc = conn.execute("SELECT id, source_file, page_count, created_at FROM documents WHERE id=?", (doc_id,)).fetchone()
    slides = conn.execute(
        "SELECT slide_index, title, status FROM slides WHERE doc_id=? ORDER BY slide_index", (doc_id,)).fetchall()
    cnt = conn.execute("SELECT COUNT(*) FROM slides WHERE doc_id=?", (doc_id,)).fetchone()[0]
    jobs = conn.execute(
        "SELECT status, COUNT(*) FROM jobs WHERE doc_id=? GROUP BY status", (doc_id,)).fetchall()
    conn.close()
    if not doc:
        return None
    job_summary = {r[0]: r[1] for r in jobs}
    return {
        "doc_id": doc[0], "source_file": doc[1], "page_count": doc[2], "created_at": doc[3],
        "slides_total": cnt,
        "slides_done": sum(1 for s in slides if s[2] in ("done", "override")),
        "slides": [{"slide_index": s[0], "title": s[1], "status": s[2]} for s in slides],
        "jobs": job_summary,
    }


# ---------------- CLI ----------------
def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]

    if cmd == "init" and "--source" in argv and "--pages" in argv:
        src = argv[argv.index("--source") + 1]
        pages = int(argv[argv.index("--pages") + 1])
        print(json.dumps({"doc_id": init_doc(src, pages)}))
        return 0

    if cmd == "ingest":
        doc = int(argv[argv.index("--doc") + 1])
        page = int(argv[argv.index("--page") + 1])
        ci = int(argv[argv.index("--chunk") + 1])
        text = argv[argv.index("--text") + 1]
        precursor = argv[argv.index("--precursor") + 1] if "--precursor" in argv else ""
        add_chunk(doc, page, ci, text, precursor)
        print(json.dumps({"ok": True, "doc_id": doc, "page": page, "chunk_index": ci}))
        return 0

    if cmd == "chunks":
        doc = int(argv[argv.index("--doc") + 1])
        page = int(argv[argv.index("--page") + 1]) if "--page" in argv else None
        print(json.dumps({"chunks": query_chunks(doc, page)}))
        return 0

    if cmd == "slide" and len(argv) >= 3:
        sub = argv[2]
        doc = int(argv[argv.index("--doc") + 1])
        idx = int(argv[argv.index("--slide") + 1])
        if sub == "create":
            title = argv[argv.index("--title") + 1]
            bullets = argv[argv.index("--bullets") + 1] if "--bullets" in argv else "[]"
            notes = argv[argv.index("--notes") + 1] if "--notes" in argv else ""
            sp = int(argv[argv.index("--source-page") + 1]) if "--source-page" in argv else None
            create_slide(doc, idx, title, bullets, notes, sp)
            print(json.dumps({"ok": True, "doc_id": doc, "slide": idx}))
            return 0
        if sub == "get":
            print(json.dumps(get_slide(doc, idx)))
            return 0
        if sub == "status-set":
            st = argv[argv.index("--status") + 1]
            set_slide_status(doc, idx, st)
            print(json.dumps({"ok": True}))
            return 0
        if sub == "lock":
            print(json.dumps(lock_slide(doc, idx)))
            return 0
        if sub == "commit":
            title = argv[argv.index("--title") + 1]
            bullets = argv[argv.index("--bullets") + 1] if "--bullets" in argv else "[]"
            notes = argv[argv.index("--notes") + 1] if "--notes" in argv else ""
            sp = int(argv[argv.index("--source-page") + 1]) if "--source-page" in argv else None
            print(json.dumps(commit_slide(doc, idx, title, bullets, notes, sp)))
            return 0
        if sub == "rollback":
            reason = argv[argv.index("--reason") + 1] if "--reason" in argv else "manual"
            print(json.dumps(rollback_slide(doc, idx, reason)))
            return 0
        if sub == "attempt":
            print(json.dumps(get_attempt(doc, idx)))
            return 0

    if cmd == "rollback-check":
        doc = int(argv[argv.index("--doc") + 1])
        threshold = int(argv[argv.index("--threshold") + 1]) if "--threshold" in argv else 120
        print(json.dumps(check_stale_jobs(doc, threshold)))
        return 0

    if cmd == "slides-detail":
        doc = int(argv[argv.index("--doc") + 1])
        print(json.dumps(get_slides_detail(doc)))
        return 0

    if cmd == "create-jobs":
        doc = int(argv[argv.index("--doc") + 1])
        print(json.dumps(create_jobs_for_doc(doc)))
        return 0

    if cmd == "claim-job":
        doc = int(argv[argv.index("--doc") + 1])
        model = argv[argv.index("--model") + 1] if "--model" in argv else "unknown"
        result = claim_next_job(doc, model)
        print(json.dumps(result))
        return 0

    if cmd == "complete-job":
        doc = int(argv[argv.index("--doc") + 1])
        idx = int(argv[argv.index("--slide") + 1])
        title = argv[argv.index("--title") + 1]
        bullets = argv[argv.index("--bullets") + 1] if "--bullets" in argv else "[]"
        notes = argv[argv.index("--notes") + 1] if "--notes" in argv else ""
        sp = int(argv[argv.index("--source-page") + 1]) if "--source-page" in argv else None
        print(json.dumps(complete_job(doc, idx, title, bullets, notes, sp)))
        return 0

    if cmd == "fail-job":
        doc = int(argv[argv.index("--doc") + 1])
        idx = int(argv[argv.index("--slide") + 1])
        error = argv[argv.index("--error") + 1] if "--error" in argv else "unknown"
        print(json.dumps(fail_job(doc, idx, error)))
        return 0

    if cmd == "override-job":
        doc = int(argv[argv.index("--doc") + 1])
        idx = int(argv[argv.index("--slide") + 1])
        title = argv[argv.index("--title") + 1]
        bullets = argv[argv.index("--bullets") + 1] if "--bullets" in argv else "[]"
        notes = argv[argv.index("--notes") + 1] if "--notes" in argv else ""
        sp = int(argv[argv.index("--source-page") + 1]) if "--source-page" in argv else None
        print(json.dumps(override_job(doc, idx, title, bullets, notes, sp)))
        return 0

    if cmd == "jobs":
        doc = int(argv[argv.index("--doc") + 1])
        print(json.dumps({"jobs": get_jobs(doc)}))
        return 0

    if cmd == "slide" and len(argv) >= 3:
        sub = argv[2]
        doc = int(argv[argv.index("--doc") + 1])
        idx = int(argv[argv.index("--slide") + 1])
        if sub == "get":
            print(json.dumps(get_slide(doc, idx)))
            return 0
        if sub == "status-set":
            st = argv[argv.index("--status") + 1]
            set_slide_status(doc, idx, st)
            print(json.dumps({"ok": True}))
            return 0

    if cmd == "status":
        doc = int(argv[argv.index("--doc") + 1])
        print(json.dumps(status(doc)))
        return 0

    print(f"Unknown command: {cmd}", file=sys.stderr)
    print(__doc__)
    return 1


# ---------------- Pipeline Runs (Idempotent Resurrection) ----------------
def create_pipeline_run(run_id, doc_id, payload_json):
    """Create a pipeline run record for idempotent tracking."""
    conn = connect()
    conn.execute(
        "INSERT INTO pipeline_runs(run_id, doc_id, status, current_step, payload_json) VALUES(?,?,?,'init',?)",
        (run_id, doc_id, "pending", payload_json),
    )
    conn.commit()
    conn.close()


def update_pipeline_step(run_id, step, status="running", result_json=None, error=None):
    """Update pipeline step. Called at each milestone.

    Status is always normalized to 'running' for in-progress steps,
    or 'done'/'failed' for terminal states.
    """
    # Normalize status to allowed CHECK values
    if status not in ("pending", "running", "done", "failed"):
        status = "running"

    conn = connect()
    if result_json:
        conn.execute(
            "UPDATE pipeline_runs SET current_step=?, status=?, result_json=?, updated_at=? WHERE run_id=?",
            (step, status, result_json, now(), run_id),
        )
    elif error:
        conn.execute(
            "UPDATE pipeline_runs SET current_step=?, status=?, error=?, updated_at=? WHERE run_id=?",
            (step, status, error, now(), run_id),
        )
    else:
        conn.execute(
            "UPDATE pipeline_runs SET current_step=?, status=?, updated_at=? WHERE run_id=?",
            (step, status, now(), run_id),
        )
    conn.commit()
    conn.close()


def get_pipeline_run(run_id):
    """Get pipeline run record."""
    conn = connect()
    row = conn.execute(
        "SELECT run_id, doc_id, status, current_step, payload_json, result_json, error, created_at, updated_at "
        "FROM pipeline_runs WHERE run_id=?", (run_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "run_id": row[0], "doc_id": row[1], "status": row[2],
        "current_step": row[3], "payload_json": row[4], "result_json": row[5],
        "error": row[6], "created_at": row[7], "updated_at": row[8],
    }


def get_stranded_runs():
    """Find pipeline runs that were interrupted (pending/running/ingesting/dispatching/compiling).

    These are 'zombie' states from killed processes. On server restart,
    the orchestrator calls this to detect and resume them.
    """
    conn = connect()
    rows = conn.execute(
        "SELECT run_id, doc_id, status, current_step, payload_json "
        "FROM pipeline_runs WHERE status NOT IN ('done','failed')"
    ).fetchall()
    conn.close()
    return [
        {"run_id": r[0], "doc_id": r[1], "status": r[2], "current_step": r[3], "payload_json": r[4]}
        for r in rows
    ]


def mark_pipeline_done(run_id, result_json):
    """Mark pipeline as done."""
    update_pipeline_step(run_id, "done", status="done", result_json=result_json)


def mark_pipeline_failed(run_id, error):
    """Mark pipeline as failed."""
    update_pipeline_step(run_id, "failed", status="failed", error=error)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
