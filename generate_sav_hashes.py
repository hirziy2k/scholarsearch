#!/usr/bin/env python3
"""Generate SHA-256 integrity hashes for all SAV files."""

import hashlib
import json
import os
from datetime import datetime, timezone

SAV_DIR = r"C:\Users\hirzi\OneDrive\Documents\Default Project\data"
OUTPUT_FILE = r"C:\Users\hirzi\OneDrive\Documents\Default Project\data\SAV_INTEGRITY_MANIFEST.json"


def hash_file(filepath):
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def main():
    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "purpose": "Integrity verification for untrusted SAV binary files",
        "files": {}
    }
    
    for filename in sorted(os.listdir(SAV_DIR)):
        if filename.lower().endswith('.sav'):
            filepath = os.path.join(SAV_DIR, filename)
            file_hash = hash_file(filepath)
            file_size = os.path.getsize(filepath)
            
            manifest["files"][filename] = {
                "sha256": file_hash,
                "size_bytes": file_size,
                "verified": False,
                "verified_date": None
            }
            print(f"  {filename}: {file_hash[:16]}... ({file_size:,} bytes)")
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nManifest written to: {OUTPUT_FILE}")
    print(f"Total files: {len(manifest['files'])}")


if __name__ == "__main__":
    main()
