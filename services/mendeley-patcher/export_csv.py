"""
Phase 4a: Export SQLite data to CSV for manual review in Excel/Numbers.
"""

import csv
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import OUTPUT_DIR, REVIEW_CSV_PATH
from db import init_db, get_connection


def run():
    """Export diff data to CSV for review."""
    init_db()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get documents that need review
    cursor.execute("""
        SELECT 
            uuid,
            title_mendeley,
            title_crossref,
            year_mendeley,
            year_crossref,
            authors_mendeley,
            authors_crossref,
            doi,
            needs_correction,
            approved,
            correction_json
        FROM documents 
        WHERE state = 'DIFFED'
        ORDER BY needs_correction DESC, title_mendeley
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No documents in DIFFED state.")
        print("Run diff.py first.")
        return False
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Write CSV
    with open(REVIEW_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'approved',      # User sets to 1 to approve
            'uuid',
            'title_mendeley',
            'title_crossref',
            'year_mendeley',
            'year_crossref',
            'authors_mendeley',
            'authors_crossref',
            'doi',
            'needs_correction',
            'correction_json',
            'reviewer_notes',  # User can add notes
        ])
        
        for row in rows:
            writer.writerow([
                0,  # Default: not approved
                row['uuid'],
                row['title_mendeley'] or '',
                row['title_crossref'] or '',
                row['year_mendeley'] or '',
                row['year_crossref'] or '',
                row['authors_mendeley'] or '',
                row['authors_crossref'] or '',
                row['doi'] or '',
                row['needs_correction'] or 0,
                row['correction_json'] or '',
                '',  # Reviewer notes (empty for user to fill)
            ])
    
    print(f"Exported {len(rows)} documents to:")
    print(f"  {REVIEW_CSV_PATH}")
    print(f"\nNext steps:")
    print(f"  1. Open {REVIEW_CSV_PATH} in Excel or Numbers")
    print(f"  2. Review each row and set 'approved' column to 1 for corrections to apply")
    print(f"  3. Save the CSV")
    print(f"  4. Run: python ingest_csv.py")
    
    return True


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
