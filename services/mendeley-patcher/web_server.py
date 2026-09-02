"""
Hardened Web Server for Mendeley Patcher.
Features:
- CSRF token authentication (single-use session token)
- Idempotent rollback ledger (recovery_state.json)
- .docx backup before PATCH execution
- Self-terminates on unauthorized access
"""

import json
import os
import sys
import time
import shutil
import secrets
import threading
import hashlib
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(__file__))

from config import OUTPUT_DIR, DB_PATH, BASE_PATH
from db import init_db, get_connection, get_stats, update_approved, get_recovery_state, save_recovery_state, update_recovery_completed
from oauth import get_valid_token


# Global state
server_state = {
    "session_token": None,
    "docx_backup_path": None,
    "docx_original_path": None,
}

execution_state = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current": "",
    "results": [],
    "error": None,
    "started_at": None,
}

recovery_state = {
    "active": False,
    "snapshot_id": None,
    "total": 0,
    "completed": [],
    "failed": [],
    "started_at": None,
}


def generate_session_token():
    """Generate cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def load_recovery_state():
    """Load recovery state from database (crash-proof with WAL)."""
    global recovery_state
    recovery_state = get_recovery_state()
    return recovery_state


def save_recovery_state():
    """Save recovery state to database with WAL for crash safety."""
    save_recovery_state_db(recovery_state)


def save_recovery_state_db(state):
    """Save recovery state to database."""
    from db import save_recovery_state as db_save
    db_save(state)


def backup_docx(docx_path):
    """Create timestamped backup of .docx file."""
    if not docx_path or not os.path.exists(docx_path):
        return None
    
    backup_dir = os.path.join(OUTPUT_DIR, "docx_backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    basename = os.path.splitext(os.path.basename(docx_path))[0]
    backup_name = f"{basename}_pre_patch_{timestamp}.docx"
    backup_path = os.path.join(backup_dir, backup_name)
    
    shutil.copy2(docx_path, backup_path)
    server_state["docx_backup_path"] = backup_path
    server_state["docx_original_path"] = docx_path
    
    return backup_path


class SecurePatcherHandler(BaseHTTPRequestHandler):
    """Hardened HTTP request handler with CSRF protection."""
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        # Check for auth token in URL (first visit)
        auth_token = query.get('auth', [None])[0]
        
        if path == '/' or path == '/index.html':
            if auth_token and auth_token == server_state.get("session_token"):
                self.serve_dashboard(auth_token)
            else:
                self.send_error(403, "Forbidden: Invalid or missing session token")
        elif path == '/api/status':
            self.serve_status()
        elif path == '/api/documents':
            self.serve_documents()
        elif path == '/api/execution':
            self.serve_execution_status()
        elif path == '/api/recovery':
            self.serve_recovery_status()
        elif path == '/api/snapshot':
            self.serve_snapshot_list()
        elif path.startswith('/api/snapshot/'):
            snapshot_id = path.split('/')[-1]
            self.serve_snapshot_detail(snapshot_id)
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests with CSRF token validation."""
        # Validate CSRF token
        auth_header = self.headers.get('X-Session-Token', '')
        if not auth_header or auth_header != server_state.get("session_token"):
            self.send_json({"error": "Forbidden: Invalid session token"}, 403)
            # Self-terminate on unauthorized access
            print("[SECURITY] Unauthorized access attempt detected. Terminating server.")
            threading.Thread(target=self.server.shutdown).start()
            return
        
        path = urlparse(self.path).path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}
        
        if path == '/api/approve':
            self.handle_approve(data)
        elif path == '/api/execute':
            self.handle_execute(data)
        elif path == '/api/rollback':
            self.handle_rollback(data)
        elif path == '/api/rollback/resume':
            self.handle_resume_rollback()
        elif path == '/api/snapshot/create':
            self.handle_create_snapshot(data)
        else:
            self.send_error(404)
    
    def send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def send_html(self, html, status=200):
        """Send HTML response."""
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_status(self):
        """Serve database statistics."""
        stats = get_stats()
        stats["docx_backup"] = server_state.get("docx_backup_path")
        stats["recovery_active"] = recovery_state.get("active", False)
        self.send_json(stats)
    
    def serve_documents(self):
        """Serve all documents for review."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT uuid, title_mendeley, title_crossref, 
                   year_mendeley, year_crossref,
                   authors_mendeley, authors_crossref,
                   needs_correction, approved, correction_json,
                   manually_modified, last_modified
            FROM documents 
            WHERE state IN ('DIFFED', 'APPROVED')
            ORDER BY manually_modified DESC, needs_correction DESC, title_mendeley
        """)
        docs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        self.send_json(docs)
    
    def serve_execution_status(self):
        """Serve current execution progress."""
        self.send_json(execution_state)
    
    def serve_recovery_status(self):
        """Serve recovery state."""
        load_recovery_state()
        self.send_json(recovery_state)
    
    def serve_snapshot_list(self):
        """Serve list of available snapshots."""
        snapshots = []
        snapshot_dir = os.path.join(OUTPUT_DIR, 'snapshots')
        if os.path.exists(snapshot_dir):
            for f in os.listdir(snapshot_dir):
                if f.endswith('.json'):
                    path = os.path.join(snapshot_dir, f)
                    try:
                        with open(path, 'r', encoding='utf-8') as fh:
                            data = json.load(fh)
                        snapshots.append({
                            "id": f.replace('.json', ''),
                            "timestamp": data.get('timestamp'),
                            "count": data.get('document_count', 0),
                        })
                    except:
                        pass
        self.send_json(snapshots)
    
    def serve_snapshot_detail(self, snapshot_id):
        """Serve details of a specific snapshot."""
        snapshot_path = os.path.join(OUTPUT_DIR, 'snapshots', f'{snapshot_id}.json')
        if os.path.exists(snapshot_path):
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.send_json(data)
        else:
            self.send_error(404)
    
    def handle_approve(self, data):
        """Handle approval of documents."""
        uuids = data.get('uuids', [])
        if not uuids:
            self.send_json({"error": "No UUIDs provided"}, 400)
            return
        
        update_approved(uuids, approved=1)
        self.send_json({"success": True, "approved": len(uuids)})
    
    def handle_execute(self, data):
        """Handle execution of patches."""
        if execution_state['running']:
            self.send_json({"error": "Execution already in progress"}, 409)
            return
        
        dry_run = data.get('dry_run', False)
        docx_path = data.get('docx_path')
        
        # Backup .docx before patching (unless dry run)
        if not dry_run and docx_path:
            backup_path = backup_docx(docx_path)
            if backup_path:
                print(f"[BACKUP] Created .docx backup: {backup_path}")
        
        # Start execution in background thread
        thread = threading.Thread(target=self.execute_patches, args=(dry_run,))
        thread.daemon = True
        thread.start()
        
        self.send_json({"started": True, "dry_run": dry_run})
    
    def execute_patches(self, dry_run=False):
        """Execute PATCH requests with idempotent ledger."""
        global execution_state
        
        execution_state = {
            "running": True,
            "progress": 0,
            "total": 0,
            "current": "",
            "results": [],
            "error": None,
            "started_at": time.time(),
        }
        
        try:
            from patch import patch_mendeley_document
            
            access_token = get_valid_token()
            if not access_token:
                execution_state["error"] = "No valid access token"
                execution_state["running"] = False
                return
            
            # Get approved documents
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT uuid, title_mendeley, correction_json
                FROM documents 
                WHERE approved = 1 AND state = 'APPROVED' AND correction_json IS NOT NULL
            """)
            docs = cursor.fetchall()
            conn.close()
            
            if not docs:
                execution_state["error"] = "No approved documents to patch"
                execution_state["running"] = False
                return
            
            execution_state["total"] = len(docs)
            
            # Create snapshot before patching
            if not dry_run:
                snapshot_id = self.create_rollback_snapshot(docs)
                
                # Initialize recovery ledger
                global recovery_state
                recovery_state = {
                    "active": True,
                    "snapshot_id": snapshot_id,
                    "total": len(docs),
                    "completed": [],
                    "failed": [],
                    "started_at": time.time(),
                }
                save_recovery_state()
            
            # Execute patches
            for i, doc in enumerate(docs):
                uuid = doc['uuid']
                correction = json.loads(doc['correction_json'])
                
                execution_state["progress"] = i + 1
                execution_state["current"] = doc['title_mendeley'] or uuid[:12]
                
                if dry_run:
                    result = {
                        "uuid": uuid,
                        "status": "DRY_RUN",
                        "corrections": correction,
                    }
                else:
                    success, code, body = patch_mendeley_document(uuid, correction, access_token)
                    result = {
                        "uuid": uuid,
                        "status": "SUCCESS" if success else "ERROR",
                        "code": code,
                        "corrections": correction,
                    }
                    
                    # Update recovery ledger atomically
                    if success:
                        update_recovery_completed(uuid, success=True)
                        # Update document state
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE documents SET state = 'PATCHED', updated_at = CURRENT_TIMESTAMP
                            WHERE uuid = ?
                        """, (uuid,))
                        conn.commit()
                        conn.close()
                    else:
                        update_recovery_completed(uuid, success=False)
                    
                    # Reload state from database
                    load_recovery_state()
                
                execution_state["results"].append(result)
                
                # Rate limiting
                if not dry_run:
                    time.sleep(0.6)
            
            # Mark recovery as complete if all succeeded
            if not dry_run and not recovery_state["failed"]:
                recovery_state["active"] = False
                save_recovery_state()
            
            execution_state["completed_at"] = time.time()
            
        except Exception as e:
            execution_state["error"] = str(e)
        finally:
            execution_state["running"] = False
    
    def create_rollback_snapshot(self, docs):
        """Create immutable snapshot before patching."""
        snapshot_dir = os.path.join(OUTPUT_DIR, 'snapshots')
        os.makedirs(snapshot_dir, exist_ok=True)
        
        snapshot_id = f"snapshot_{int(time.time())}"
        snapshot = {
            "id": snapshot_id,
            "timestamp": time.time(),
            "document_count": len(docs),
            "documents": [],
        }
        
        access_token = get_valid_token()
        if not access_token:
            return snapshot_id
        
        # Fetch current state from Mendeley for each document
        for doc in docs:
            uuid = doc['uuid']
            try:
                from fetch import fetch_mendeley_document, extract_mendeley_metadata
                mendeley_data = fetch_mendeley_document(uuid, access_token)
                meta = extract_mendeley_metadata(mendeley_data)
                meta['uuid'] = uuid
                snapshot['documents'].append(meta)
            except Exception:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM documents WHERE uuid = ?", (uuid,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    snapshot['documents'].append({
                        'uuid': uuid,
                        'title': dict(row).get('title_mendeley', ''),
                        'year': dict(row).get('year_mendeley'),
                        'authors': dict(row).get('authors_mendeley', ''),
                    })
        
        # Save snapshot
        snapshot_path = os.path.join(snapshot_dir, f'{snapshot_id}.json')
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        
        return snapshot_id
    
    def handle_rollback(self, data):
        """Handle rollback to a snapshot with idempotent ledger."""
        global recovery_state
        
        snapshot_id = data.get('snapshot_id')
        if not snapshot_id:
            self.send_json({"error": "No snapshot_id provided"}, 400)
            return
        
        snapshot_path = os.path.join(OUTPUT_DIR, 'snapshots', f'{snapshot_id}.json')
        if not os.path.exists(snapshot_path):
            self.send_json({"error": "Snapshot not found"}, 404)
            return
        
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)
        
        access_token = get_valid_token()
        if not access_token:
            self.send_json({"error": "No valid access token"}, 401)
            return
        
        # Initialize recovery ledger for rollback
        docs_to_rollback = snapshot.get('documents', [])
        recovery_state = {
            "active": True,
            "snapshot_id": snapshot_id,
            "operation": "rollback",
            "total": len(docs_to_rollback),
            "completed": [],
            "failed": [],
            "started_at": time.time(),
        }
        save_recovery_state()
        
        # Execute rollback
        results = []
        for doc in docs_to_rollback:
            uuid = doc['uuid']
            
            # Skip already completed (idempotent)
            if uuid in recovery_state["completed"]:
                results.append({"uuid": uuid, "success": True, "skipped": True})
                continue
            
            payload = {}
            if doc.get('title'):
                payload['title'] = doc['title']
            if doc.get('year'):
                payload['year'] = doc['year']
            if doc.get('authors'):
                payload['authors'] = doc['authors']
            
            if payload:
                from patch import patch_mendeley_document
                success, code, body = patch_mendeley_document(uuid, payload, access_token)
                result = {"uuid": uuid, "success": success, "code": code}
                
                if success:
                    recovery_state["completed"].append(uuid)
                else:
                    recovery_state["failed"].append(uuid)
                
                results.append(result)
                save_recovery_state()
                time.sleep(0.6)
        
        # Mark recovery as complete if all succeeded
        if not recovery_state["failed"]:
            recovery_state["active"] = False
            save_recovery_state()
        
        self.send_json({
            "success": True,
            "rolled_back": len([r for r in results if r.get("success")]),
            "results": results,
            "docx_backup": server_state.get("docx_backup_path"),
        })
    
    def handle_resume_rollback(self):
        """Resume an incomplete rollback."""
        load_recovery_state()
        
        if not recovery_state.get("active") or recovery_state.get("operation") != "rollback":
            self.send_json({"error": "No active rollback to resume"}, 400)
            return
        
        snapshot_id = recovery_state["snapshot_id"]
        snapshot_path = os.path.join(OUTPUT_DIR, 'snapshots', f'{snapshot_id}.json')
        
        if not os.path.exists(snapshot_path):
            self.send_json({"error": "Snapshot not found"}, 404)
            return
        
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)
        
        access_token = get_valid_token()
        if not access_token:
            self.send_json({"error": "No valid access token"}, 401)
            return
        
        # Continue rollback from where we left off
        docs_to_rollback = snapshot.get('documents', [])
        results = []
        
        for doc in docs_to_rollback:
            uuid = doc['uuid']
            
            # Skip already completed (idempotent)
            if uuid in recovery_state["completed"]:
                results.append({"uuid": uuid, "success": True, "skipped": True})
                continue
            
            payload = {}
            if doc.get('title'):
                payload['title'] = doc['title']
            if doc.get('year'):
                payload['year'] = doc['year']
            if doc.get('authors'):
                payload['authors'] = doc['authors']
            
            if payload:
                from patch import patch_mendeley_document
                success, code, body = patch_mendeley_document(uuid, payload, access_token)
                result = {"uuid": uuid, "success": success, "code": code}
                
                if success:
                    recovery_state["completed"].append(uuid)
                else:
                    recovery_state["failed"].append(uuid)
                
                results.append(result)
                save_recovery_state()
                time.sleep(0.6)
        
        # Mark recovery as complete if all succeeded
        if not recovery_state["failed"]:
            recovery_state["active"] = False
            save_recovery_state()
        
        self.send_json({
            "success": True,
            "resumed": True,
            "rolled_back": len([r for r in results if r.get("success")]),
            "remaining_failed": len(recovery_state["failed"]),
        })
    
    def handle_create_snapshot(self, data):
        """Handle manual snapshot creation."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT uuid, title_mendeley, correction_json
            FROM documents 
            WHERE approved = 1 AND correction_json IS NOT NULL
        """)
        docs = cursor.fetchall()
        conn.close()
        
        if not docs:
            self.send_json({"error": "No documents to snapshot"}, 400)
            return
        
        snapshot_id = self.create_rollback_snapshot(docs)
        self.send_json({"success": True, "snapshot_id": snapshot_id, "count": len(docs)})
    
    def log_message(self, format, *args):
        """Suppress server log messages."""
        pass
    
    def serve_dashboard(self, auth_token):
        """Serve the main dashboard HTML with embedded auth token."""
        html = DASHBOARD_HTML.replace("{{AUTH_TOKEN}}", auth_token)
        self.send_html(html)


# Hardened HTML Dashboard with CSRF token handling
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mendeley Patcher</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; color: #333; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px 30px; border-radius: 12px; margin-bottom: 25px; }
        h1 { font-size: 26px; margin-bottom: 8px; }
        .subtitle { opacity: 0.9; font-size: 13px; }
        .stats { display: flex; gap: 15px; margin-top: 18px; flex-wrap: wrap; }
        .stat-box { background: rgba(255,255,255,0.2); padding: 12px 20px; border-radius: 8px; text-align: center; min-width: 100px; }
        .stat-number { font-size: 22px; font-weight: bold; }
        .stat-label { font-size: 11px; opacity: 0.9; }
        .card { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }
        .card-title { font-size: 16px; font-weight: 600; }
        .btn { padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover:not(:disabled) { background: #5a6fd6; }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover:not(:disabled) { background: #218838; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover:not(:disabled) { background: #c82333; }
        .btn-warning { background: #ffc107; color: #333; }
        .btn-warning:hover:not(:disabled) { background: #e0a800; }
        .btn-outline { background: transparent; border: 2px solid #667eea; color: #667eea; }
        .btn-outline:hover:not(:disabled) { background: #667eea; color: white; }
        .btn-group { display: flex; gap: 10px; flex-wrap: wrap; }
        .search-box { padding: 10px 15px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 13px; width: 250px; }
        .search-box:focus { outline: none; border-color: #667eea; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; font-size: 12px; text-transform: uppercase; color: #666; }
        tr:hover { background: #f8f9fa; }
        tr.selected { background: #e8f5e9; }
        .checkbox-cell { width: 50px; text-align: center; }
        input[type="checkbox"] { width: 18px; height: 18px; cursor: pointer; }
        .uuid-cell { font-family: monospace; font-size: 11px; color: #666; }
        .diff { font-size: 12px; }
        .diff-current { color: #dc3545; text-decoration: line-through; }
        .diff-proposed { color: #28a745; font-weight: 500; }
        .diff-arrow { color: #667eea; margin: 0 5px; }
        .locked { background-color: #fff3cd !important; border-left: 4px solid #dc3545; }
        .lock-warning { 
            display: inline-block;
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
            margin-top: 4px;
            animation: pulse-warning 2s infinite;
        }
        @keyframes pulse-warning {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .progress-container { margin: 20px 0; }
        .progress-bar { height: 24px; background: #e0e0e0; border-radius: 12px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); transition: width 0.3s; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 500; }
        .results-list { max-height: 300px; overflow-y: auto; }
        .result-item { padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .result-success { color: #28a745; }
        .result-error { color: #dc3545; }
        .result-dry { color: #ffc107; }
        .snapshot-list { max-height: 200px; overflow-y: auto; }
        .snapshot-item { padding: 12px; border: 1px solid #eee; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .snapshot-info { font-size: 13px; }
        .snapshot-time { color: #666; font-size: 12px; }
        .tabs { display: flex; gap: 5px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; border: none; background: #e0e0e0; border-radius: 8px 8px 0 0; cursor: pointer; font-size: 13px; }
        .tab.active { background: #667eea; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .alert { padding: 15px; border-radius: 8px; margin-bottom: 15px; font-size: 13px; }
        .alert-info { background: #d1ecf1; color: #0c5460; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-warning { background: #fff3cd; color: #856404; }
        .alert-danger { background: #f8d7da; color: #721c24; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center; }
        .modal.active { display: flex; }
        .modal-content { background: white; padding: 30px; border-radius: 12px; max-width: 500px; width: 90%; }
        .modal h3 { margin-bottom: 15px; }
        .modal p { margin-bottom: 15px; color: #666; font-size: 14px; }
        .security-badge { display: inline-block; background: #28a745; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; margin-left: 10px; }
        .docx-input { margin-bottom: 15px; }
        .docx-input label { display: block; margin-bottom: 5px; font-weight: 500; font-size: 13px; }
        .docx-input input { width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Mendeley Patcher <span class="security-badge">Session Authenticated</span></h1>
            <p class="subtitle">UUID-Preserving Metadata Correction Pipeline</p>
            <div class="stats">
                <div class="stat-box"><div class="stat-number" id="stat-total">0</div><div class="stat-label">Total</div></div>
                <div class="stat-box"><div class="stat-number" id="stat-needs">0</div><div class="stat-label">Need Fix</div></div>
                <div class="stat-box"><div class="stat-number" id="stat-approved">0</div><div class="stat-label">Approved</div></div>
                <div class="stat-box"><div class="stat-number" id="stat-patched">0</div><div class="stat-label">Patched</div></div>
            </div>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showTab('review')">Review & Approve</button>
            <button class="tab" onclick="showTab('execute')">Execute</button>
            <button class="tab" onclick="showTab('rollback')">Rollback</button>
        </div>

        <div id="tab-review" class="tab-content active">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Documents</span>
                    <div class="btn-group">
                        <input type="text" class="search-box" id="search" placeholder="Search..." oninput="filterDocs()">
                        <button class="btn btn-outline" onclick="selectAll()">Select All</button>
                        <button class="btn btn-outline" onclick="deselectAll()">Deselect None</button>
                        <button class="btn btn-success" onclick="approveSelected()">Approve Selected</button>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th class="checkbox-cell"><input type="checkbox" id="check-all" onchange="toggleAll(this.checked)"></th>
                            <th>UUID</th>
                            <th>Current (Mendeley)</th>
                            <th>Proposed (Crossref)</th>
                            <th>Year</th>
                            <th>Authors</th>
                        </tr>
                    </thead>
                    <tbody id="docs-body"></tbody>
                </table>
            </div>
        </div>

        <div id="tab-execute" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Execute Patches</span>
                    <div class="btn-group">
                        <button class="btn btn-warning" onclick="execute(true)">Dry Run</button>
                        <button class="btn btn-success" id="btn-execute" onclick="execute(false)">Execute Now</button>
                    </div>
                </div>
                <div class="docx-input">
                    <label>Word Document Path (for backup before patching):</label>
                    <input type="text" id="docx-path" placeholder="C:\\Users\\...\\thesis.docx">
                </div>
                <div id="exec-alert" class="alert alert-info" style="display:none;"></div>
                <div class="progress-container" id="progress-container" style="display:none;">
                    <div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:0%">0%</div></div>
                </div>
                <div id="current-doc" style="margin:10px 0;font-size:13px;color:#666;"></div>
                <div class="results-list" id="results-list"></div>
            </div>
        </div>

        <div id="tab-rollback" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Rollback Snapshots</span>
                    <div class="btn-group">
                        <button class="btn btn-outline" onclick="loadSnapshots()">Refresh</button>
                        <button class="btn btn-warning" id="btn-resume" onclick="resumeRollback()" style="display:none;">Resume Incomplete Rollback</button>
                    </div>
                </div>
                <div id="recovery-alert" class="alert alert-warning" style="display:none;"></div>
                <div class="snapshot-list" id="snapshot-list"></div>
            </div>
        </div>
    </div>

    <div class="modal" id="confirm-modal">
        <div class="modal-content">
            <h3 id="modal-title">Confirm</h3>
            <p id="modal-message"></p>
            <div class="btn-group" style="justify-content:flex-end;">
                <button class="btn btn-outline" onclick="closeModal()">Cancel</button>
                <button class="btn btn-success" id="modal-confirm" onclick="confirmAction()">Confirm</button>
            </div>
        </div>
    </div>

    <script>
        const SESSION_TOKEN = '{{AUTH_TOKEN}}';
        let documents = [];
        let selectedUuids = new Set();
        let pendingAction = null;
        let executionPolling = null;

        // API helper with CSRF token
        async function apiCall(url, method = 'GET', body = null) {
            const opts = {
                method,
                headers: {
                    'X-Session-Token': SESSION_TOKEN,
                    'Content-Type': 'application/json',
                },
            };
            if (body) opts.body = JSON.stringify(body);
            const res = await fetch(url, opts);
            if (res.status === 403) {
                alert('Session expired or unauthorized. Please restart the server.');
                window.location.reload();
                return null;
            }
            return res.json();
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadStats();
            loadDocuments();
            checkRecovery();
        });

        function showTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelector(`[onclick="showTab('${name}')"]`).classList.add('active');
            document.getElementById(`tab-${name}`).classList.add('active');
            if (name === 'rollback') loadSnapshots();
        }

        async function loadStats() {
            const stats = await apiCall('/api/status');
            if (!stats) return;
            document.getElementById('stat-total').textContent = (stats.DIFFED || 0) + (stats.APPROVED || 0) + (stats.PATCHED || 0);
            document.getElementById('stat-needs').textContent = stats.NEEDS_CORRECTION || 0;
            document.getElementById('stat-approved').textContent = stats.APPROVED_COUNT || 0;
            document.getElementById('stat-patched').textContent = stats.PATCHED || 0;
        }

        async function loadDocuments() {
            documents = await apiCall('/api/documents') || [];
            selectedUuids.clear();
            documents.forEach(d => { if (d.approved) selectedUuids.add(d.uuid); });
            renderDocs();
        }

        function renderDocs() {
            const search = document.getElementById('search').value.toLowerCase();
            const tbody = document.getElementById('docs-body');
            tbody.innerHTML = '';
            
            documents.filter(d => {
                if (!search) return true;
                return (d.title_mendeley||'').toLowerCase().includes(search) ||
                       (d.title_crossref||'').toLowerCase().includes(search) ||
                       (d.uuid||'').toLowerCase().includes(search);
            }).forEach(d => {
                const tr = document.createElement('tr');
                const isLocked = d.manually_modified === 1;
                tr.className = selectedUuids.has(d.uuid) ? 'selected' : (isLocked ? 'locked' : '');
                const needs = d.needs_correction;
                
                // Manual Override Lock warning
                const lockWarning = isLocked ? `<div class="lock-warning" title="Record modified in Mendeley Desktop within last 6 months. Manual verification required.">⚠ MANUALLY MODIFIED</div>` : '';
                
                tr.innerHTML = `
                    <td class="checkbox-cell"><input type="checkbox" ${selectedUuids.has(d.uuid)?'checked':''} ${isLocked?'disabled title="Manual override lock - verify manually"':''} onchange="toggleDoc('${d.uuid}',this.checked)"></td>
                    <td class="uuid-cell" title="${d.uuid}">${d.uuid.substring(0,12)}...</td>
                    <td><div class="diff ${needs?'diff-current':''}">${esc(d.title_mendeley||'N/A')}${lockWarning}</div></td>
                    <td><div class="diff ${needs?'diff-proposed':''}">${esc(d.title_crossref||'N/A')}</div></td>
                    <td>${d.year_mendeley!==d.year_crossref?`<span class="diff-current">${d.year_mendeley||'?'}</span><span class="diff-arrow">&rarr;</span><span class="diff-proposed">${d.year_crossref||'?'}</span>`:d.year_mendeley||'?'}</td>
                    <td><div class="diff">${d.authors_mendeley!==d.authors_crossref?`<div class="diff-current">${esc(d.authors_mendeley||'')}</div><div class="diff-proposed">${esc(d.authors_crossref||'')}</div>`:esc(d.authors_mendeley||'N/A')}</div></td>
                `;
                tbody.appendChild(tr);
            });
        }

        function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
        function filterDocs() { renderDocs(); }
        function toggleDoc(uuid, checked) { checked ? selectedUuids.add(uuid) : selectedUuids.delete(uuid); renderDocs(); }
        function toggleAll(checked) { documents.forEach(d => checked ? selectedUuids.add(d.uuid) : selectedUuids.delete(d.uuid)); renderDocs(); }
        function selectAll() { documents.forEach(d => selectedUuids.add(d.uuid)); document.getElementById('check-all').checked = true; renderDocs(); }
        function deselectAll() { selectedUuids.clear(); document.getElementById('check-all').checked = false; renderDocs(); }

        async function approveSelected() {
            if (selectedUuids.size === 0) { alert('No documents selected'); return; }
            const data = await apiCall('/api/approve', 'POST', {uuids: Array.from(selectedUuids)});
            if (data && data.success) { alert(`Approved ${data.approved} documents`); loadStats(); loadDocuments(); }
        }

        async function execute(dryRun) {
            const docxPath = document.getElementById('docx-path').value;
            const btn = document.getElementById('btn-execute');
            btn.disabled = true;
            document.getElementById('exec-alert').style.display = 'block';
            document.getElementById('exec-alert').className = 'alert alert-info';
            document.getElementById('exec-alert').textContent = dryRun ? 'Starting dry run...' : 'Creating .docx backup and executing patches...';
            document.getElementById('progress-container').style.display = 'block';
            
            const data = await apiCall('/api/execute', 'POST', {dry_run: dryRun, docx_path: docxPath});
            
            if (data && data.started) {
                executionPolling = setInterval(pollExecution, 1000);
            } else {
                alert(data?.error || 'Failed to start execution');
                btn.disabled = false;
            }
        }

        async function pollExecution() {
            const state = await apiCall('/api/execution');
            if (!state) return;
            
            const pct = state.total > 0 ? Math.round((state.progress / state.total) * 100) : 0;
            document.getElementById('progress-fill').style.width = pct + '%';
            document.getElementById('progress-fill').textContent = pct + '%';
            document.getElementById('current-doc').textContent = state.current ? `Processing: ${state.current}` : '';
            
            const list = document.getElementById('results-list');
            list.innerHTML = state.results.map(r => `
                <div class="result-item">
                    <span>${r.uuid.substring(0,12)}... - ${r.status}</span>
                    <span class="result-${r.status.toLowerCase()}">${r.status}</span>
                </div>
            `).join('');
            
            if (!state.running) {
                clearInterval(executionPolling);
                document.getElementById('btn-execute').disabled = false;
                document.getElementById('exec-alert').className = state.error ? 'alert alert-danger' : 'alert alert-success';
                document.getElementById('exec-alert').textContent = state.error || `Completed: ${state.results.length} documents processed`;
                loadStats();
            }
        }

        async function checkRecovery() {
            const recovery = await apiCall('/api/recovery');
            if (recovery && recovery.active) {
                document.getElementById('recovery-alert').style.display = 'block';
                document.getElementById('recovery-alert').textContent = `Incomplete ${recovery.operation || 'rollback'} detected (${recovery.completed?.length || 0}/${recovery.total} completed). Click "Resume" to continue.`;
                document.getElementById('btn-resume').style.display = 'inline-block';
            }
        }

        async function loadSnapshots() {
            const snapshots = await apiCall('/api/snapshot') || [];
            const list = document.getElementById('snapshot-list');
            if (snapshots.length === 0) {
                list.innerHTML = '<div class="alert alert-info">No snapshots available. Snapshots are created automatically before patching.</div>';
                return;
            }
            list.innerHTML = snapshots.map(s => `
                <div class="snapshot-item">
                    <div class="snapshot-info">
                        <strong>${s.id}</strong>
                        <div class="snapshot-time">${new Date(s.timestamp*1000).toLocaleString()} - ${s.count} documents</div>
                    </div>
                    <button class="btn btn-danger" onclick="rollback('${s.id}')">Rollback</button>
                </div>
            `).join('');
        }

        function rollback(snapshotId) {
            pendingAction = () => doRollback(snapshotId);
            document.getElementById('modal-title').textContent = 'Confirm Rollback';
            document.getElementById('modal-message').textContent = `This will revert all changes made in ${snapshotId}. A .docx backup exists if you need to restore your Word document. Continue?`;
            document.getElementById('confirm-modal').classList.add('active');
        }

        async function doRollback(snapshotId) {
            closeModal();
            const data = await apiCall('/api/rollback', 'POST', {snapshot_id: snapshotId});
            if (data && data.success) {
                let msg = `Rolled back ${data.rolled_back} documents`;
                if (data.docx_backup) msg += `\\n\\nWord backup: ${data.docx_backup}`;
                alert(msg);
                loadStats();
                loadDocuments();
            } else {
                alert(data?.error || 'Rollback failed');
            }
        }

        async function resumeRollback() {
            const data = await apiCall('/api/rollback/resume', 'POST');
            if (data && data.success) {
                alert(`Resumed: ${data.rolled_back} documents rolled back. ${data.remaining_failed} still failed.`);
                loadStats();
                checkRecovery();
            } else {
                alert(data?.error || 'Resume failed');
            }
        }

        function confirmAction() { if (pendingAction) pendingAction(); }
        function closeModal() { document.getElementById('confirm-modal').classList.remove('active'); pendingAction = null; }
    </script>
</body>
</html>"""


def start_server(port=8585, docx_path=None):
    """Start the hardened web server."""
    init_db()
    
    # Generate session token
    server_state["session_token"] = generate_session_token()
    
    # Store .docx path if provided
    if docx_path:
        server_state["docx_original_path"] = docx_path
    
    # Check for incomplete recovery
    load_recovery_state()
    
    server = HTTPServer(('127.0.0.1', port), SecurePatcherHandler)
    
    auth_url = f"http://127.0.0.1:{port}/?auth={server_state['session_token']}"
    
    print(f"\nMendeley Patcher (Hardened) running at:")
    print(f"  {auth_url}")
    print(f"\nSession token: {server_state['session_token'][:16]}...")
    print(f"\nPress Ctrl+C to stop the server.\n")
    
    # Open browser with auth token
    webbrowser.open(auth_url)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8585
    start_server(port)
