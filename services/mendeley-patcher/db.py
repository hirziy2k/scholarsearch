"""
SQLite database layer for Mendeley Patcher.
Handles schema creation and state machine transitions.
"""

import sqlite3
import json
from datetime import datetime
from config import DB_PATH


# State machine transitions
STATES = ["DISCOVERED", "FETCHED", "DIFFED", "APPROVED", "PATCHED"]

VALID_TRANSITIONS = {
    "DISCOVERED": ["FETCHED"],
    "FETCHED": ["DIFFED"],
    "DIFFED": ["APPROVED"],
    "APPROVED": ["PATCHED"],
    "PATCHED": [],
}


def get_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            uuid TEXT PRIMARY KEY,
            state TEXT DEFAULT 'DISCOVERED' CHECK(state IN ('DISCOVERED','FETCHED','DIFFED','APPROVED','PATCHED')),
            title_mendeley TEXT,
            title_crossref TEXT,
            year_mendeley INTEGER,
            year_crossref INTEGER,
            authors_mendeley TEXT,
            authors_crossref TEXT,
            abstract_mendeley TEXT,
            abstract_crossref TEXT,
            doi TEXT,
            source_title TEXT,
            needs_correction INTEGER DEFAULT 0,
            approved INTEGER DEFAULT 0,
            correction_json TEXT,
            manually_modified INTEGER DEFAULT 0,
            last_modified TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            response_json TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT,
            action TEXT,
            request_url TEXT,
            request_body TEXT,
            response_code INTEGER,
            response_body TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS recovery_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            active INTEGER DEFAULT 0,
            snapshot_id TEXT,
            total INTEGER DEFAULT 0,
            completed TEXT DEFAULT '[]',
            failed TEXT DEFAULT '[]',
            started_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_documents_state ON documents(state);
        CREATE INDEX IF NOT EXISTS idx_documents_approved ON documents(approved);
        CREATE INDEX IF NOT EXISTS idx_audit_log_uuid ON audit_log(uuid);
    """)

    # Migration: add missing columns to existing tables
    cursor.execute("PRAGMA table_info(documents)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    migrations = [
        ("manually_modified", "ALTER TABLE documents ADD COLUMN manually_modified INTEGER DEFAULT 0"),
        ("last_modified", "ALTER TABLE documents ADD COLUMN last_modified TIMESTAMP"),
    ]

    for col_name, sql in migrations:
        if col_name not in existing_columns:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError:
                pass  # Column already exists

    # Create recovery_state table if missing (for upgrades)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recovery_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            active INTEGER DEFAULT 0,
            snapshot_id TEXT,
            total INTEGER DEFAULT 0,
            completed TEXT DEFAULT '[]',
            failed TEXT DEFAULT '[]',
            started_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def upsert_document(uuid, state="DISCOVERED", **kwargs):
    """Insert or update a document record."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if exists
    cursor.execute("SELECT uuid, state FROM documents WHERE uuid = ?", (uuid,))
    existing = cursor.fetchone()

    if existing:
        # Validate state transition
        current_state = existing["state"]
        if state != current_state:
            if state not in VALID_TRANSITIONS.get(current_state, []):
                conn.close()
                raise ValueError(
                    f"Invalid state transition: {current_state} -> {state}"
                )
        # Update
        set_clauses = ["state = ?", "updated_at = ?"]
        values = [state, datetime.utcnow().isoformat()]
        for key, value in kwargs.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)
        values.append(uuid)
        cursor.execute(
            f"UPDATE documents SET {', '.join(set_clauses)} WHERE uuid = ?",
            values,
        )
    else:
        # Insert
        columns = ["uuid", "state", "created_at", "updated_at"]
        placeholders = ["?", "?", "?", "?"]
        values = [uuid, state, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()]
        for key, value in kwargs.items():
            columns.append(key)
            placeholders.append("?")
            values.append(value)
        cursor.execute(
            f"INSERT INTO documents ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
            values,
        )

    conn.commit()
    conn.close()


def get_documents_by_state(state):
    """Get all documents in a specific state."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE state = ?", (state,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_documents_by_uuids(uuids):
    """Get documents by list of UUIDs."""
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(uuids))
    cursor.execute(f"SELECT * FROM documents WHERE uuid IN ({placeholders})", uuids)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_documents():
    """Get all documents."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents ORDER BY state, title_mendeley")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_approved_documents():
    """Get all approved documents ready for patching."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM documents WHERE approved = 1 AND state = 'DIFFED'"
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_cache(cache_key):
    """Get cached API response."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT response_json FROM api_cache WHERE cache_key = ?", (cache_key,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row["response_json"])
    return None


def set_cache(cache_key, response_data):
    """Cache an API response."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO api_cache (cache_key, response_json, fetched_at) VALUES (?, ?, ?)",
        (cache_key, json.dumps(response_data), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def log_audit(uuid, action, request_url, request_body, response_code, response_body):
    """Log an API request/response for audit trail."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_log (uuid, action, request_url, request_body, response_code, response_body) VALUES (?, ?, ?, ?, ?, ?)",
        (uuid, action, request_url, request_body, response_code, response_body),
    )
    conn.commit()
    conn.close()


def update_approved(uuids, approved=1):
    """Set approved flag for a list of UUIDs."""
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(uuids))
    cursor.execute(
        f"UPDATE documents SET approved = ?, state = 'APPROVED', updated_at = ? WHERE uuid IN ({placeholders})",
        [approved, datetime.utcnow().isoformat()] + uuids,
    )
    conn.commit()
    conn.close()


def get_stats():
    """Get summary statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}
    for state in STATES:
        cursor.execute("SELECT COUNT(*) as cnt FROM documents WHERE state = ?", (state,))
        stats[state] = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM documents WHERE needs_correction = 1")
    stats["NEEDS_CORRECTION"] = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM documents WHERE approved = 1")
    stats["APPROVED_COUNT"] = cursor.fetchone()["cnt"]
    conn.close()
    return stats


def get_recovery_state():
    """Get recovery state from database (crash-proof with WAL)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recovery_state WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "active": bool(row["active"]),
            "snapshot_id": row["snapshot_id"],
            "total": row["total"],
            "completed": json.loads(row["completed"]) if row["completed"] else [],
            "failed": json.loads(row["failed"]) if row["failed"] else [],
            "started_at": row["started_at"],
        }
    return {
        "active": False,
        "snapshot_id": None,
        "total": 0,
        "completed": [],
        "failed": [],
        "started_at": None,
    }


def save_recovery_state(state):
    """Save recovery state to database with WAL for crash safety."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Use WAL mode with synchronous=FULL for maximum durability
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    
    cursor.execute("""
        INSERT OR REPLACE INTO recovery_state 
        (id, active, snapshot_id, total, completed, failed, started_at, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
    """, (
        1 if state.get("active") else 0,
        state.get("snapshot_id"),
        state.get("total", 0),
        json.dumps(state.get("completed", [])),
        json.dumps(state.get("failed", [])),
        state.get("started_at"),
        datetime.utcnow().isoformat(),
    ))
    
    conn.commit()
    conn.close()


def update_recovery_completed(uuid, success=True):
    """Atomically update recovery state - add uuid to completed or failed list."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Use WAL mode with synchronous=FULL
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    
    cursor.execute("SELECT completed, failed FROM recovery_state WHERE id = 1")
    row = cursor.fetchone()
    
    if row:
        completed = json.loads(row["completed"]) if row["completed"] else []
        failed = json.loads(row["failed"]) if row["failed"] else []
        
        if success:
            if uuid not in completed:
                completed.append(uuid)
        else:
            if uuid not in failed:
                failed.append(uuid)
        
        cursor.execute("""
            UPDATE recovery_state 
            SET completed = ?, failed = ?, updated_at = ?
            WHERE id = 1
        """, (json.dumps(completed), json.dumps(failed), datetime.utcnow().isoformat()))
    
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
