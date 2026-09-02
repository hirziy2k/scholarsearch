"""
Phase 5: Execute PATCH requests to Mendeley API for approved corrections.
Only patches documents that have been manually approved.
Includes post-patch verification polling for eventual consistency.
"""

import time
import json
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    MENDELEY_API_BASE,
    MENDELEY_DOC_CONTENT_TYPE,
    REQUEST_DELAY_SECONDS,
    OUTPUT_DIR,
)
from db import (
    init_db,
    get_approved_documents,
    get_connection,
    log_audit,
)
from oauth import get_valid_token, refresh_access_token


# Pre-patch snapshot file (captured during Phase 2)
ROLLBACK_SNAPSHOT_PATH = os.path.join(OUTPUT_DIR, "rollback_snapshot.json")

# Verification polling constants
VERIFICATION_TIMEOUT_SECONDS = 30
VERIFICATION_POLL_INTERVAL_SECONDS = 2


def execute_with_retry(method, url, headers, json_data=None, max_retries=3):
    """
    Execute an HTTP request with automatic token refresh on 401 and 429 backoff.
    
    Args:
        method: HTTP method ("get" or "patch")
        url: Request URL
        headers: Request headers
        json_data: Optional JSON body for PATCH
        max_retries: Maximum retry attempts
        
    Returns:
        Response object
    """
    for attempt in range(max_retries):
        if method == "get":
            response = requests.get(url, headers=headers, timeout=30)
        else:
            response = requests.patch(url, headers=headers, json=json_data, timeout=30)
        
        # Success - return immediately
        if response.status_code < 400:
            return response
        
        # Handle 429 Too Many Requests with exponential backoff
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                wait_time = int(retry_after)
            else:
                wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
            
            print(f"  [429] Rate limited, waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        
        # Handle 401 Token expired - refresh and retry
        if response.status_code == 401:
            if attempt < max_retries - 1:
                print(f"  [401] Token expired, refreshing...")
                new_token = refresh_access_token()
                if new_token:
                    headers["Authorization"] = f"Bearer {new_token}"
                    print(f"  [OK] Token refreshed, retrying...")
                    time.sleep(1)
                else:
                    print(f"  [ERROR] Token refresh failed")
                    return response
            continue
        
        # Other errors - return immediately
        return response
    
    return response


def verify_patch_applied(uuid, correction_payload, access_token, timeout_seconds=VERIFICATION_TIMEOUT_SECONDS):
    """
    Verify that a PATCH was actually applied by polling GET until data matches.
    
    Handles Mendeley's eventual consistency - the 200 OK doesn't guarantee
    the read-replica has synchronized yet.
    
    Args:
        uuid: Document UUID
        correction_payload: The corrections that were applied
        access_token: OAuth access token
        timeout_seconds: Max time to wait for consistency
        
    Returns:
        Tuple of (verified: bool, actual_data: dict)
    """
    url = f"{MENDELEY_API_BASE}/documents/{uuid}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": MENDELEY_DOC_CONTENT_TYPE,
    }
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < timeout_seconds:
        attempt += 1
        response = execute_with_retry("get", url, headers)
        
        if response.status_code != 200:
            time.sleep(VERIFICATION_POLL_INTERVAL_SECONDS)
            continue
        
        remote_data = response.json()
        
        # Check if all corrected fields match
        all_match = True
        for field, expected_value in correction_payload.items():
            remote_value = remote_data.get(field)
            
            # Normalize for comparison
            if isinstance(expected_value, str):
                expected_value = expected_value.strip()
            if isinstance(remote_value, str):
                remote_value = remote_value.strip()
            
            if remote_value != expected_value:
                all_match = False
                break
        
        if all_match:
            return True, remote_data
        
        # Not yet consistent - wait and retry
        time.sleep(VERIFICATION_POLL_INTERVAL_SECONDS)
    
    # Timeout - data may not have propagated
    return False, {}


def load_pre_patch_snapshots():
    """
    Load pre-patch snapshots captured during Phase 2.
    
    Returns:
        Dictionary mapping uuids to their pre-patch state
    """
    if not os.path.exists(ROLLBACK_SNAPSHOT_PATH):
        return {}
    
    try:
        with open(ROLLBACK_SNAPSHOT_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("snapshots", {})
    except Exception as e:
        print(f"Warning: Could not load rollback snapshot: {e}")
        return {}


def patch_mendeley_document(uuid, correction_payload, access_token):
    """
    PATCH a single Mendeley document with automatic retry on 401.
    
    Args:
        uuid: Document UUID
        correction_payload: Dictionary of fields to update
        access_token: OAuth access token
        
    Returns:
        Tuple of (success: bool, response_code: int, response_body: str, token: str)
    """
    url = f"{MENDELEY_API_BASE}/documents/{uuid}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": MENDELEY_DOC_CONTENT_TYPE,
        "Accept": MENDELEY_DOC_CONTENT_TYPE,
    }
    
    request_body = json.dumps(correction_payload)
    
    response = execute_with_retry("patch", url, headers, correction_payload)
    
    log_audit(
        uuid=uuid,
        action="PATCH",
        request_url=url,
        request_body=request_body,
        response_code=response.status_code,
        response_body=response.text[:2000],
    )
    
    # Extract current token from headers for return
    current_token = headers.get("Authorization", "").replace("Bearer ", "")
    
    if response.status_code == 200:
        return True, response.status_code, response.text, current_token
    else:
        return False, response.status_code, response.text, current_token


def run(access_token=None, dry_run=False):
    """
    Main patch phase.
    
    Args:
        access_token: Mendeley OAuth access token (optional)
        dry_run: If True, show what would be patched without executing
    """
    init_db()
    
    # Get token if not provided
    if not access_token:
        access_token = get_valid_token()
        if not access_token:
            print("Cannot proceed without Mendeley access token.")
            print("Run 'setup' or 'auth' command first.")
            return False
    
    # Get approved documents
    documents = get_approved_documents()
    
    if not documents:
        print("No approved documents ready for patching.")
        return False
    
    print(f"{'DRY RUN - ' if dry_run else ''}Patching {len(documents)} documents...")
    
    # CRITICAL: Load pre-patch snapshots from Phase 2 (not captured at execution time)
    snapshots = load_pre_patch_snapshots()
    
    if not dry_run and not snapshots:
        print("\nABORT: No pre-patch snapshots found.")
        print("Rollback snapshot must be captured during Phase 2 (fetch).")
        print("Re-run the full pipeline to capture snapshots.")
        return False
    
    # Verify we have snapshots for all documents
    if not dry_run:
        missing_snapshots = [doc["uuid"] for doc in documents if doc["uuid"] not in snapshots]
        if missing_snapshots:
            print(f"\nABORT: Cannot proceed - missing snapshots for {len(missing_snapshots)} documents:")
            for uuid in missing_snapshots:
                print(f"  - {uuid}")
            print("\nThis prevents safe rollback. Re-run the full pipeline.")
            return False
    
    # Initialize counters
    success_count = 0
    error_count = 0
    unverified_count = 0
    
    for i, doc in enumerate(documents, 1):
        uuid = doc["uuid"]
        correction_json = doc.get("correction_json")
        
        if not correction_json:
            print(f"[{i}/{len(documents)}] {uuid[:12]}... - No corrections, skipping")
            continue
        
        correction_payload = json.loads(correction_json)
        
        print(f"\n[{i}/{len(documents)}] {uuid[:12]}...")
        print(f"  Title: {doc.get('title_mendeley', 'N/A')[:50]}...")
        print(f"  Corrections: {list(correction_payload.keys())}")
        
        if dry_run:
            print(f"  [DRY RUN] Would patch: {json.dumps(correction_payload, indent=2)}")
            success_count += 1
            log_audit(
                uuid=uuid,
                action="PATCH_DRY_RUN",
                request_url=f"{MENDELEY_API_BASE}/documents/{uuid}",
                request_body=json.dumps(correction_payload),
                response_code=0,
                response_body="DRY RUN"
            )
        else:
            # Execute PATCH with automatic retry on 401
            success, code, body, access_token = patch_mendeley_document(
                uuid, correction_payload, access_token
            )
            
            if success:
                print(f"  [SUCCESS] PATCH accepted (HTTP 200)")
                
                # CRITICAL: Verify eventual consistency
                print(f"  [VERIFY] Polling for eventual consistency...", end=" ")
                verified, remote_data = verify_patch_applied(
                    uuid, correction_payload, access_token
                )
                
                if verified:
                    print(f"[CONFIRMED]")
                    success_count += 1
                    log_audit(
                        uuid=uuid,
                        action="PATCH_VERIFIED",
                        request_url=f"{MENDELEY_API_BASE}/documents/{uuid}",
                        request_body=json.dumps(correction_payload),
                        response_code=code,
                        response_body="VERIFIED"
                    )
                else:
                    print(f"[UNVERIFIED - may still propagate]")
                    unverified_count += 1
                    log_audit(
                        uuid=uuid,
                        action="PATCH_UNVERIFIED",
                        request_url=f"{MENDELEY_API_BASE}/documents/{uuid}",
                        request_body=json.dumps(correction_payload),
                        response_code=code,
                        response_body="UNVERIFIED - Data not confirmed after timeout"
                    )
                
                # Update state to PATCHED
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE documents SET 
                        state = 'PATCHED',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE uuid = ?
                """, (uuid,))
                conn.commit()
                conn.close()
            else:
                print(f"  [ERROR] {code}: {body[:200]}")
                error_count += 1
                log_audit(
                    uuid=uuid,
                    action="PATCH_ERROR",
                    request_url=f"{MENDELEY_API_BASE}/documents/{uuid}",
                    request_body=json.dumps(correction_payload),
                    response_code=code,
                    response_body=body[:500]
                )
            
            # Rate limiting
            time.sleep(REQUEST_DELAY_SECONDS)
    
    print(f"\n{'='*60}")
    print(f"Patch phase complete:")
    print(f"  Total: {len(documents)}")
    print(f"  Verified: {success_count}")
    print(f"  Unverified: {unverified_count}")
    print(f"  Errors: {error_count}")
    print(f"  All telemetry logged to SQLite audit_log table")
    print(f"{'='*60}")
    
    if unverified_count > 0:
        print(f"\n⚠ {unverified_count} document(s) were PATCHED but not confirmed.")
        print(f"  Wait 30-60 seconds before opening Word to allow full propagation.")
    
    if not dry_run and (success_count > 0 or unverified_count > 0):
        print(f"\nNext steps:")
        print(f"  1. Wait 60 seconds for full propagation")
        print(f"  2. Open Microsoft Word")
        print(f"  3. Open Mendeley Cite side panel")
        print(f"  4. Click 'Update From Library' or 'Refresh'")
        print(f"  5. Verify citations are updated")
    
    return error_count == 0


if __name__ == "__main__":
    token = None
    dry_run = False
    
    for arg in sys.argv[1:]:
        if arg == "--dry-run":
            dry_run = True
        else:
            token = arg
    
    success = run(token, dry_run=dry_run)
    sys.exit(0 if success else 1)
