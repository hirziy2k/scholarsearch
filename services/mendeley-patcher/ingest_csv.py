"""
Phase 4b: Ingest reviewed CSV back into SQLite.
Reads approved flags from the CSV edited by user in Excel/Numbers.
"""

import csv
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import REVIEW_CSV_PATH
from db import init_db, get_connection, update_approved


def run(csv_path=None):
    """
    Ingest reviewed CSV and update approved flags in SQLite.
    
    Args:
        csv_path: Path to reviewed CSV (defaults to config path)
    """
    if csv_path is None:
        csv_path = REVIEW_CSV_PATH
    
    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        print("Run export_csv.py first to generate the review CSV.")
        return False
    
    init_db()
    
    approved_uuids = []
    total_rows = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            total_rows += 1
            uuid = row.get('uuid', '').strip()
            approved = row.get('approved', '0').strip()
            
            if not uuid:
                continue
            
            if approved in ('1', 'true', 'yes', 'TRUE', 'Yes'):
                approved_uuids.append(uuid)
    
    if not approved_uuids:
        print("No approved records found in CSV.")
        print("Set 'approved' column to 1 for records you want to patch.")
        return False
    
    # Update database
    print(f"Found {len(approved_uuids)} approved records out of {total_rows} total.")
    
    update_approved(approved_uuids, approved=1)
    
    # Show what will be patched
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT uuid, title_mendeley, correction_json
        FROM documents 
        WHERE uuid IN ({})
    """.format(','.join(['?'] * len(approved_uuids))), approved_uuids)
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\nApproved for patching:")
    for row in rows:
        corrections = json.loads(row['correction_json']) if row['correction_json'] else {}
        fields = list(corrections.keys()) if corrections else []
        print(f"  {row['uuid'][:12]}... - {row['title_mendeley'][:40]}...")
        if fields:
            print(f"    Fields to update: {', '.join(fields)}")
    
    print(f"\nNext step: Run python patch.py")
    
    return True


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    success = run(csv_path)
    sys.exit(0 if success else 1)
