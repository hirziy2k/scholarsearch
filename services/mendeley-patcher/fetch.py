"""
Phase 2: Fetch metadata from Mendeley API (via UUID) and Crossref API (via clean APA text).
Uses response caching to avoid redundant API calls.
"""

import time
import json
import re
import sys
import os
import requests
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    MENDELEY_API_BASE,
    MENDELEY_DOC_CONTENT_TYPE,
    CROSSREF_API_BASE,
    REQUEST_DELAY_SECONDS,
    OUTPUT_DIR,
)
from db import (
    init_db,
    get_documents_by_state,
    get_connection,
    get_cache,
    set_cache,
    log_audit,
)
from oauth import get_valid_token, refresh_access_token


# Pre-patch snapshot file (captured during Phase 2 for rollback)
ROLLBACK_SNAPSHOT_PATH = os.path.join(OUTPUT_DIR, "rollback_snapshot.json")


def execute_with_retry(method, url, headers, params=None, max_retries=3):
    """
    Execute an HTTP request with automatic token refresh on 401 and 429 backoff.
    
    Args:
        method: HTTP method ("get")
        url: Request URL
        headers: Request headers
        params: Optional query parameters
        max_retries: Maximum retry attempts
        
    Returns:
        Response object
    """
    for attempt in range(max_retries):
        if method == "get":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        else:
            response = requests.get(url, headers=headers, params=params, timeout=30)
        
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


def fetch_mendeley_document(uuid, access_token):
    """
    Fetch document metadata from Mendeley API with automatic retry on 401.
    
    Args:
        uuid: Mendeley document UUID
        access_token: OAuth access token
        
    Returns:
        Tuple of (data: dict, current_token: str) or (None, token)
    """
    cache_key = f"mendeley:{uuid}"
    cached = get_cache(cache_key)
    if cached:
        print(f"  [cache hit] Mendeley {uuid[:8]}...")
        return cached, access_token
    
    url = f"{MENDELEY_API_BASE}/documents/{uuid}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": MENDELEY_DOC_CONTENT_TYPE,
    }
    
    response = execute_with_retry("get", url, headers)
    
    # Extract current token from headers
    current_token = headers.get("Authorization", "").replace("Bearer ", "")
    
    log_audit(
        uuid=uuid,
        action="FETCH_MENDELEY",
        request_url=url,
        request_body="",
        response_code=response.status_code,
        response_body=response.text[:2000],
    )
    
    if response.status_code == 200:
        data = response.json()
        set_cache(cache_key, data)
        return data, current_token
    elif response.status_code == 404:
        print(f"  [404] Document not found: {uuid}")
        return None, current_token
    else:
        print(f"  [Error] {response.status_code}: {response.text[:200]}")
        return None, current_token


def fetch_crossref_by_title(title, authors=None):
    """
    Search Crossref API by title to get authoritative metadata.
    
    Args:
        title: Document title to search
        authors: Optional author string for query refinement
        
    Returns:
        Dictionary with Crossref metadata or None
    """
    if not title:
        return None
    
    # Build query
    query = f'ti:"{title}"'
    cache_key = f"crossref:{title.lower()[:100]}"
    cached = get_cache(cache_key)
    if cached:
        print(f"  [cache hit] Crossref title match")
        return cached
    
    url = f"{CROSSREF_API_BASE}/works"
    params = {
        "query.title": title,
        "rows": 3,
        "select": "DOI,title,author,container-title,volume,page,published-print,abstract",
    }
    
    headers = {
        "User-Agent": "MendeleyPatcher/1.0 (mailto:noraz@university.edu)",
        "Accept": "application/json",
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("message", {}).get("items", [])
        
        if items:
            # Take the first (most relevant) result
            best_match = items[0]
            set_cache(cache_key, best_match)
            return best_match
        else:
            return None
    else:
        print(f"  [Crossref] {response.status_code}")
        return None


def fetch_crossref_by_doi(doi):
    """
    Fetch Crossref metadata by DOI.
    
    Args:
        doi: Document DOI
        
    Returns:
        Dictionary with Crossref metadata or None
    """
    if not doi:
        return None
    
    # Normalize DOI
    doi = doi.strip()
    if doi.startswith("http"):
        doi = doi.split("doi.org/")[-1]
    
    cache_key = f"crossref_doi:{doi}"
    cached = get_cache(cache_key)
    if cached:
        print(f"  [cache hit] Crossref DOI match")
        return cached
    
    url = f"{CROSSREF_API_BASE}/works/{quote(doi, safe='')}"
    
    headers = {
        "User-Agent": "MendeleyPatcher/1.0 (mailto:noraz@university.edu)",
        "Accept": "application/json",
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        item = data.get("message", {})
        set_cache(cache_key, item)
        return item
    else:
        print(f"  [Crossref DOI] {response.status_code}")
        return None


def extract_crossref_metadata(crossref_data):
    """
    Extract normalized metadata from Crossref response.
    
    Args:
        crossref_data: Raw Crossref API response
        
    Returns:
        Dictionary with normalized metadata
    """
    if not crossref_data:
        return {}
    
    # Extract title
    titles = crossref_data.get("title", [])
    title = titles[0] if titles else ""
    
    # Extract authors
    authors_list = crossref_data.get("author", [])
    authors = []
    for a in authors_list:
        given = a.get("given", "")
        family = a.get("family", "")
        if given and family:
            authors.append(f"{family} {given[0]}")
        elif family:
            authors.append(family)
    authors_str = ", ".join(authors)
    
    # Extract year
    year = None
    pub_date = crossref_data.get("published-print", {})
    date_parts = pub_date.get("date-parts", [[]])
    if date_parts and date_parts[0]:
        year = date_parts[0][0]
    
    # Extract journal
    container = crossref_data.get("container-title", [])
    journal = container[0] if container else ""
    
    # Extract volume and pages
    volume = crossref_data.get("volume", "")
    page = crossref_data.get("page", "")
    
    # Extract DOI
    doi = crossref_data.get("DOI", "")
    
    return {
        "title": title,
        "authors": authors_str,
        "year": year,
        "journal": journal,
        "volume": volume,
        "pages": page,
        "doi": doi,
    }


def extract_mendeley_metadata(mendeley_data):
    """
    Extract normalized metadata from Mendeley response.
    
    Args:
        mendeley_data: Raw Mendeley API response
        
    Returns:
        Dictionary with normalized metadata
    """
    if not mendeley_data:
        return {}
    
    # Extract title
    title = mendeley_data.get("title", "")
    
    # Extract authors
    authors_list = mendeley_data.get("authors", [])
    authors = []
    for a in authors_list:
        first = a.get("first_name", "")
        last = a.get("last_name", "")
        if first and last:
            authors.append(f"{last} {first[0]}")
        elif last:
            authors.append(last)
    authors_str = ", ".join(authors)
    
    # Extract year
    year = mendeley_data.get("year")
    
    # Extract journal
    journal = mendeley_data.get("source", "")
    
    # Extract volume and pages
    volume = mendeley_data.get("volume", "")
    pages = mendeley_data.get("pages", "")
    
    # Extract DOI
    identifiers = mendeley_data.get("identifiers", {})
    doi = identifiers.get("doi", "")
    
    return {
        "title": title,
        "authors": authors_str,
        "year": year,
        "journal": journal,
        "volume": volume,
        "pages": pages,
        "doi": doi,
    }


def run(access_token=None):
    """
    Main fetch phase.
    
    Captures pre-patch snapshots during fetch for rollback safety.
    
    Args:
        access_token: Mendeley OAuth access token (optional, will refresh if needed)
    """
    init_db()
    
    # Get token if not provided
    if not access_token:
        access_token = get_valid_token()
        if not access_token:
            print("Cannot proceed without Mendeley access token.")
            print("Run 'setup' or 'auth' command first.")
            return False
    
    # Get documents in DISCOVERED state
    documents = get_documents_by_state("DISCOVERED")
    
    if not documents:
        print("No documents in DISCOVERED state.")
        print("Run extract_uuids.py first.")
        return False
    
    print(f"Fetching metadata for {len(documents)} documents...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # CRITICAL: Initialize rollback snapshot structure
    snapshots = {}
    
    for i, doc in enumerate(documents, 1):
        uuid = doc["uuid"]
        print(f"\n[{i}/{len(documents)}] Processing {uuid[:12]}...")
        
        # Fetch from Mendeley with retry
        print(f"  Fetching from Mendeley...")
        mendeley_data, access_token = fetch_mendeley_document(uuid, access_token)
        
        # CRITICAL: Save raw Mendeley JSON to snapshot IMMEDIATELY after fetch
        if mendeley_data:
            snapshots[uuid] = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "document": mendeley_data,
            }
        
        mendeley_meta = extract_mendeley_metadata(mendeley_data)
        
        # Try to find on Crossref using Mendeley title (for initial mapping)
        crossref_data = None
        if mendeley_meta.get("doi"):
            print(f"  Fetching from Crossref (DOI: {mendeley_meta['doi'][:30]}...)")
            crossref_data = fetch_crossref_by_doi(mendeley_meta["doi"])
        
        if not crossref_data and mendeley_meta.get("title"):
            print(f"  Fetching from Crossref (title search)...")
            crossref_data = fetch_crossref_by_title(
                mendeley_meta["title"],
                mendeley_meta.get("authors"),
            )
        
        crossref_meta = extract_crossref_metadata(crossref_data)
        
        # Update database
        cursor.execute("""
            UPDATE documents SET
                state = 'FETCHED',
                title_mendeley = ?,
                title_crossref = ?,
                year_mendeley = ?,
                year_crossref = ?,
                authors_mendeley = ?,
                authors_crossref = ?,
                doi = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE uuid = ?
        """, (
            mendeley_meta.get("title", ""),
            crossref_meta.get("title", ""),
            mendeley_meta.get("year"),
            crossref_meta.get("year"),
            mendeley_meta.get("authors", ""),
            crossref_meta.get("authors", ""),
            mendeley_meta.get("doi", "") or crossref_meta.get("doi", ""),
            uuid,
        ))
        
        print(f"  Mendeley: {mendeley_meta.get('title', 'N/A')[:50]}...")
        print(f"  Crossref: {crossref_meta.get('title', 'N/A')[:50]}...")
        
        # Rate limiting
        time.sleep(REQUEST_DELAY_SECONDS)
    
    conn.commit()
    conn.close()
    
    # CRITICAL: Save rollback snapshot at end of Phase 2
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(ROLLBACK_SNAPSHOT_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total": len(documents),
            "captured": len(snapshots),
            "failed": len(documents) - len(snapshots),
            "snapshots": snapshots,
        }, f, indent=2)
    
    print(f"\nFetch phase complete. {len(documents)} documents updated to FETCHED state.")
    print(f"Pre-patch snapshot saved to: {ROLLBACK_SNAPSHOT_PATH}")
    return True


if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else None
    success = run(token)
    sys.exit(0 if success else 1)
