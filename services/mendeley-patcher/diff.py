"""
Phase 3: Normalized comparison engine.
Compares Mendeley metadata against Crossref authoritative data.
Also incorporates clean references from references.bib when available.
Includes Manual Override Lock detection for recently modified records.
"""

import json
import re
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, get_documents_by_state, get_connection

# Manual Override Lock: records modified within this period are flagged
MANUAL_OVERRIDE_LOCK_MONTHS = 6


def normalize_title(title):
    """Normalize title for comparison (lowercase, strip punctuation)."""
    if not title:
        return ""
    # Lowercase
    title = title.lower()
    # Remove common punctuation
    title = re.sub(r'[^\w\s]', '', title)
    # Normalize whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def normalize_authors_for_diff(authors_str):
    """Normalize author string for comparison."""
    if not authors_str:
        return set()
    # Split on commas, clean whitespace
    authors = set()
    for a in authors_str.split(','):
        a = a.strip().lower()
        if a:
            authors.add(a)
    return authors


def extract_year(year_val):
    """Extract 4-digit year from various formats."""
    if not year_val:
        return None
    if isinstance(year_val, int):
        return year_val
    match = re.search(r'(\d{4})', str(year_val))
    return int(match.group(1)) if match else None


def check_manual_override_lock(mendeley_data):
    """
    Check if a record was manually modified in Mendeley Desktop recently.
    
    Parses the `modified` timestamp from the Mendeley API response.
    If modified within the last 6 months, flags as potentially manually edited.
    
    Args:
        mendeley_data: Raw Mendeley API response dictionary
        
    Returns:
        Tuple of (is_locked: bool, last_modified: str or None)
    """
    if not mendeley_data:
        return False, None
    
    # Check for modified timestamp in various formats
    modified_str = mendeley_data.get("modified") or mendeley_data.get("last_modified")
    
    if not modified_str:
        return False, None
    
    try:
        # Parse ISO format timestamp
        if 'T' in modified_str:
            modified_dt = datetime.fromisoformat(modified_str.replace('Z', '+00:00'))
        else:
            modified_dt = datetime.strptime(modified_str, "%Y-%m-%d")
        
        # Check if within lock period
        lock_threshold = datetime.now().replace(tzinfo=modified_dt.tzinfo) - timedelta(days=MANUAL_OVERRIDE_LOCK_MONTHS * 30)
        
        is_locked = modified_dt > lock_threshold
        return is_locked, modified_str
        
    except (ValueError, TypeError):
        return False, None


def compute_diff(doc, mendeley_api_data=None):
    """
    Compute the diff between Mendeley and Crossref/Clean metadata.
    
    Args:
        doc: Dictionary with document data from SQLite
        mendeley_api_data: Optional raw Mendeley API response for manual override detection
        
    Returns:
        Dictionary with diff results and correction payload
    """
    diff = {
        "uuid": doc["uuid"],
        "needs_correction": False,
        "corrections": [],
        "correction_payload": {},
        "manual_override_lock": False,
        "last_modified": None,
    }
    
    # CRITICAL: Check for Manual Override Lock
    if mendeley_api_data:
        is_locked, last_modified = check_manual_override_lock(mendeley_api_data)
        diff["manual_override_lock"] = is_locked
        diff["last_modified"] = last_modified
    
    # Get metadata from all sources
    mendeley = {
        "title": doc.get("title_mendeley", ""),
        "year": extract_year(doc.get("year_mendeley")),
        "authors": doc.get("authors_mendeley", ""),
    }
    
    crossref = {
        "title": doc.get("title_crossref", ""),
        "year": extract_year(doc.get("year_crossref")),
        "authors": doc.get("authors_crossref", ""),
    }
    
    # Check for clean reference in database
    clean_ref = get_clean_reference(doc.get("doi", ""))
    clean = {}
    if clean_ref:
        clean = {
            "title": clean_ref.get("title", ""),
            "year": extract_year(clean_ref.get("year")),
            "authors": clean_ref.get("authors_normalized", ""),
        }
    
    # Prefer clean reference over Crossref when available
    authoritative = clean if clean else crossref
    
    # --- Title comparison ---
    mendeley_title_norm = normalize_title(mendeley["title"])
    authoritative_title_norm = normalize_title(authoritative.get("title", ""))
    
    if mendeley_title_norm != authoritative_title_norm and authoritative.get("title"):
        # Check if it's a significant difference (not just minor formatting)
        if not titles_are_equivalent(mendeley["title"], authoritative.get("title", "")):
            diff["needs_correction"] = True
            diff["corrections"].append({
                "field": "title",
                "current": mendeley["title"],
                "proposed": authoritative["title"],
                "source": "clean" if clean else "crossref",
            })
            diff["correction_payload"]["title"] = authoritative["title"]
    
    # --- Year comparison ---
    if mendeley["year"] != authoritative.get("year") and authoritative.get("year"):
        diff["needs_correction"] = True
        diff["corrections"].append({
            "field": "year",
            "current": mendeley["year"],
            "proposed": authoritative["year"],
            "source": "clean" if clean else "crossref",
        })
        diff["correction_payload"]["year"] = authoritative["year"]
    
    # --- Authors comparison ---
    mendeley_authors = normalize_authors_for_diff(mendeley["authors"])
    authoritative_authors = normalize_authors_for_diff(authoritative.get("authors", ""))
    
    if mendeley_authors != authoritative_authors and authoritative_authors:
        diff["needs_correction"] = True
        diff["corrections"].append({
            "field": "authors",
            "current": mendeley["authors"],
            "proposed": authoritative["authors"],
            "source": "clean" if clean else "crossref",
        })
        diff["correction_payload"]["authors"] = format_authors_for_api(authoritative["authors"])
    
    return diff


def titles_are_equivalent(title1, title2):
    """
    Check if two titles are substantively equivalent.
    Handles minor differences like capitalization, punctuation.
    """
    if not title1 or not title2:
        return False
    
    # Normalize both
    t1 = normalize_title(title1)
    t2 = normalize_title(title2)
    
    # Exact match after normalization
    if t1 == t2:
        return True
    
    # One is substring of the other (handles truncated titles)
    if t1 in t2 or t2 in t1:
        return True
    
    # Check word overlap (fuzzy match)
    words1 = set(t1.split())
    words2 = set(t2.split())
    if not words1 or not words2:
        return False
    
    overlap = len(words1 & words2) / max(len(words1), len(words2))
    return overlap > 0.85  # 85% word overlap


def get_clean_reference(doi):
    """Get clean reference from database by DOI."""
    if not doi:
        return None
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM clean_references WHERE doi = ? OR doi LIKE ?",
        (doi, f"%{doi}%"),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def format_authors_for_api(authors_str):
    """Format authors string for Mendeley API PATCH payload."""
    if not authors_str:
        return []
    
    authors = []
    for author in authors_str.split(','):
        author = author.strip()
        if not author:
            continue
        
        # Handle "Last First" format
        parts = author.split()
        if len(parts) >= 2:
            last = parts[-1]
            first = ' '.join(parts[:-1])
            authors.append({
                "first_name": first,
                "last_name": last,
            })
        elif len(parts) == 1:
            authors.append({
                "first_name": "",
                "last_name": parts[0],
            })
    
    return authors


def run():
    """Main diff phase."""
    init_db()
    
    # Get documents in FETCHED state
    documents = get_documents_by_state("FETCHED")
    
    if not documents:
        print("No documents in FETCHED state.")
        print("Run fetch.py first.")
        return False
    
    print(f"Computing diffs for {len(documents)} documents...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    corrections_count = 0
    locked_count = 0
    
    for i, doc in enumerate(documents, 1):
        uuid = doc["uuid"]
        print(f"\n[{i}/{len(documents)}] Analyzing {uuid[:12]}...")
        
        # Try to get Mendeley API data for manual override detection
        mendeley_api_data = None
        try:
            # Check if we have cached Mendeley data
            cursor.execute(
                "SELECT response_json FROM api_cache WHERE cache_key = ?",
                (f"mendeley:{uuid}",)
            )
            row = cursor.fetchone()
            if row:
                mendeley_api_data = json.loads(row["response_json"])
        except:
            pass
        
        diff = compute_diff(doc, mendeley_api_data)
        
        if diff["manual_override_lock"]:
            locked_count += 1
            print(f"  ⚠ MANUAL OVERRIDE LOCK: Record modified within last 6 months")
            print(f"    Last modified: {diff['last_modified']}")
            print(f"    Manual verification required before approval")
        
        if diff["needs_correction"]:
            corrections_count += 1
            print(f"  CORRECTIONS NEEDED:")
            for c in diff["corrections"]:
                print(f"    {c['field']}: '{c['current']}' -> '{c['proposed']}'")
        else:
            print(f"  No corrections needed")
        
        # Update database with manual_override_lock flag
        cursor.execute("""
            UPDATE documents SET
                state = 'DIFFED',
                needs_correction = ?,
                correction_json = ?,
                manually_modified = ?,
                last_modified = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE uuid = ?
        """, (
            1 if diff["needs_correction"] else 0,
            json.dumps(diff["correction_payload"]) if diff["needs_correction"] else None,
            1 if diff["manual_override_lock"] else 0,
            diff["last_modified"],
            uuid,
        ))
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"Diff phase complete:")
    print(f"  Total documents: {len(documents)}")
    print(f"  Need corrections: {corrections_count}")
    print(f"  Manual override locked: {locked_count}")
    print(f"  No corrections: {len(documents) - corrections_count}")
    if locked_count > 0:
        print(f"\n  ⚠ {locked_count} record(s) require manual verification")
        print(f"    These records were recently modified in Mendeley Desktop")
        print(f"    Review carefully before approving corrections")
    print(f"{'='*60}")
    
    return True


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
