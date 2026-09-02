"""
Mendeley Patcher Orchestrator
Main entry point that runs all phases of the pipeline.
"""

import sys
import os
import atexit
import signal
import tempfile
import shutil
import glob

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, get_stats


# Track temporary directories for cleanup
_temp_dirs_to_clean = []


def _register_temp_dir(temp_dir):
    """Register a temporary directory for cleanup on exit."""
    _temp_dirs_to_clean.append(temp_dir)


def _cleanup_temp_dirs():
    """Clean up all registered temporary directories."""
    for temp_dir in _temp_dirs_to_clean:
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
    
    # Also clean up any orphaned mendeley_patcher temp dirs
    try:
        temp_base = tempfile.gettempdir()
        pattern = os.path.join(temp_base, "mendeley_patcher_*")
        for orphan in glob.glob(pattern):
            try:
                if os.path.isdir(orphan):
                    shutil.rmtree(orphan, ignore_errors=True)
            except:
                pass
    except:
        pass


def _signal_handler(signum, frame):
    """Handle termination signals for clean shutdown."""
    _cleanup_temp_dirs()
    sys.exit(0)


# Register cleanup handlers
atexit.register(_cleanup_temp_dirs)
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def print_banner():
    """Print application banner."""
    print("""
+============================================================+
|                    Mendeley Patcher                         |
|         UUID-Preserving Metadata Correction Pipeline        |
+============================================================+
    """)


def print_stats():
    """Print current database statistics."""
    stats = get_stats()
    print(f"\nDatabase Status:")
    print(f"  DISCOVERED: {stats['DISCOVERED']}")
    print(f"  FETCHED:    {stats['FETCHED']}")
    print(f"  DIFFED:     {stats['DIFFED']}")
    print(f"  APPROVED:   {stats['APPROVED']}")
    print(f"  PATCHED:    {stats['PATCHED']}")
    print(f"  Needs correction: {stats['NEEDS_CORRECTION']}")
    print(f"  Approved: {stats['APPROVED_COUNT']}")


def run_setup():
    """Run OAuth setup flow"""
    from oauth import setup_client_credentials, get_valid_token
    print("\n" + "="*60)
    print("OAUTH SETUP")
    print("="*60)
    client_id, client_secret = setup_client_credentials()
    if client_id:
        print("\nNow running authorization flow...")
        token = get_valid_token()
        return token is not None
    return False


def run_auth():
    """Run OAuth authorization flow"""
    from oauth import get_valid_token
    print("\n" + "="*60)
    print("OAUTH AUTHORIZATION")
    print("="*60)
    token = get_valid_token()
    return token is not None


def run_extract(docx_path):
    """Run Phase 1: Extract UUIDs from .docx"""
    import extract_uuids
    print("\n" + "="*60)
    print("PHASE 1: Extract UUIDs from .docx")
    print("="*60)
    return extract_uuids.run(docx_path)


def run_parse_references(bib_path):
    """Run Phase 2a: Parse references.bib"""
    import parse_references
    print("\n" + "="*60)
    print("PHASE 2a: Parse references.bib")
    print("="*60)
    return parse_references.run(bib_path)


def run_fetch(access_token=None):
    """Run Phase 2b: Fetch from APIs"""
    import fetch
    from oauth import get_valid_token
    print("\n" + "="*60)
    print("PHASE 2b: Fetch Metadata from APIs")
    print("="*60)
    
    # Get token if not provided
    if not access_token:
        access_token = get_valid_token()
        if not access_token:
            print("Error: No valid access token. Run 'setup' or 'auth' first.")
            return False
    
    return fetch.run(access_token)


def run_diff():
    """Run Phase 3: Compute diffs"""
    import diff
    print("\n" + "="*60)
    print("PHASE 3: Compute Metadata Diffs")
    print("="*60)
    return diff.run()


def run_export_html():
    """Run Phase 4a: Export to HTML dashboard"""
    import export_html
    print("\n" + "="*60)
    print("PHASE 4a: Export Review Dashboard (HTML)")
    print("="*60)
    return export_html.generate_review_dashboard()


def run_export_csv():
    """Run Phase 4a (legacy): Export to CSV"""
    import export_csv
    print("\n" + "="*60)
    print("PHASE 4a: Export Review Grid to CSV (Legacy)")
    print("="*60)
    return export_csv.run()


def run_approve(approvals_path=None):
    """Run Phase 4b: Ingest approved JSON (if file exists) or skip (approvals already in SQLite)"""
    import ingest_html
    print("\n" + "="*60)
    print("PHASE 4b: Ingest Approvals")
    print("="*60)
    
    # If no path provided, check if approvals are already in SQLite
    if approvals_path is None:
        from db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents WHERE approved = 1 AND state = 'DIFFED'")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            print(f"Found {count} approved records already in database (from web dashboard).")
            print("Skipping JSON ingest - approvals already in SQLite.")
            return True
        else:
            print("No approved records found in database.")
            print("Use the web dashboard to approve records, or provide a JSON file.")
            return False
    
    return ingest_html.run(approvals_path)


def run_patch(access_token=None, dry_run=False):
    """Run Phase 5: Execute PATCH requests"""
    import patch
    from oauth import get_valid_token
    print("\n" + "="*60)
    print("PHASE 5: Patch Mendeley API")
    print("="*60)
    
    # Get token if not provided
    if not access_token:
        access_token = get_valid_token()
        if not access_token:
            print("Error: No valid access token. Run 'setup' or 'auth' first.")
            return False
    
    return patch.run(access_token, dry_run=dry_run)


def run_full_pipeline(docx_path, bib_path, access_token=None):
    """
    Run the complete pipeline from extraction to web server.
    
    After extraction and diffing, launches the web server for review and execution.
    """
    from oauth import get_valid_token
    
    init_db()
    
    # Ensure we have a valid token
    if not access_token:
        access_token = get_valid_token()
        if not access_token:
            print("Error: No valid access token. Run 'setup' or 'auth' first.")
            return False
    
    # Phase 1: Extract UUIDs
    if not run_extract(docx_path):
        return False
    
    # Phase 2a: Parse references (if provided)
    if bib_path and os.path.exists(bib_path):
        if not run_parse_references(bib_path):
            print("Warning: Failed to parse references.bib, continuing with API-only mode")
    
    # Phase 2b: Fetch from APIs
    if not run_fetch(access_token):
        return False
    
    # Phase 3: Compute diffs
    if not run_diff():
        return False
    
    # Show stats
    print_stats()
    
    # Launch web server for review and execution
    print("\n" + "="*60)
    print("PIPELINE COMPLETE - LAUNCHING WEB INTERFACE")
    print("="*60)
    print("""
The extraction and diff phases are complete.

Launching web interface for:
  - Reviewing and approving corrections
  - Executing patches with real-time progress
  - Creating snapshots and rolling back if needed

The browser will open automatically. Press Ctrl+C in this terminal to stop.
    """)
    
    from web_server import start_server
    start_server(docx_path=docx_path)
    
    return True


def run_serve(port=None, docx_path=None):
    """Launch the web server for review and execution."""
    from web_server import start_server
    
    init_db()
    
    print("\n" + "="*60)
    print("LAUNCHING WEB INTERFACE")
    print("="*60)
    print("""
Open your browser to review documents, approve corrections, and execute patches.
Press Ctrl+C in this terminal to stop the server.
    """)
    
    start_server(port or 8585, docx_path=docx_path)
    return True


def print_usage():
    """Print usage instructions."""
    print("""
Usage:
  mendeley-patcher setup                           Configure OAuth credentials
  mendeley-patcher auth                            Run authorization flow
  
  mendeley-patcher serve [port]                    Launch web interface
  mendeley-patcher full <docx_path> [bib_path]     Run pipeline + web interface
  
  mendeley-patcher extract <docx_path>             Phase 1: Extract UUIDs
  mendeley-patcher parse <bib_path>                Phase 2a: Parse references
  mendeley-patcher fetch                           Phase 2b: Fetch APIs
  mendeley-patcher diff                            Phase 3: Compare metadata
  
  mendeley-patcher status                          Show statistics
  mendeley-patcher clear                           Clear stored credentials

Examples:
  mendeley-patcher setup
  mendeley-patcher full thesis.docx references.bib
  mendeley-patcher serve
    """)


if __name__ == "__main__":
    print_banner()
    
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        success = run_setup()
        
    elif command == "auth":
        success = run_auth()
        
    elif command == "serve":
        port = 8585
        docx_path = None
        for arg in sys.argv[2:]:
            if arg.isdigit():
                port = int(arg)
            else:
                docx_path = arg
        success = run_serve(port, docx_path)
        
    elif command == "full":
        if len(sys.argv) < 3:
            print("Usage: mendeley-patcher full <docx_path> [bib_path]")
            sys.exit(1)
        docx_path = sys.argv[2]
        bib_path = sys.argv[3] if len(sys.argv) > 3 else None
        success = run_full_pipeline(docx_path, bib_path)
        
    elif command == "extract":
        if len(sys.argv) < 3:
            print("Usage: mendeley-patcher extract <docx_path>")
            sys.exit(1)
        success = run_extract(sys.argv[2])
        
    elif command == "parse":
        if len(sys.argv) < 3:
            print("Usage: mendeley-patcher parse <bib_path>")
            sys.exit(1)
        success = run_parse_references(sys.argv[2])
        
    elif command == "fetch":
        success = run_fetch()
        
    elif command == "diff":
        success = run_diff()
        
    elif command == "status":
        init_db()
        print_stats()
        success = True
        
    elif command == "clear":
        from oauth import clear_all_credentials
        clear_all_credentials()
        success = True
        
    else:
        print(f"Unknown command: {command}")
        print_usage()
        success = False
    
    sys.exit(0 if success else 1)
