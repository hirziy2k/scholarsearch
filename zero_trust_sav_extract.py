#!/usr/bin/env python3
"""
Zero-Trust SAV Extraction Wrapper
- Verifies integrity hashes before processing
- Pure Python (no compiled dependencies)
- Ephemeral output (writes to temp location)
- Fails closed on any verification failure
"""

import hashlib
import json
import os
import sys
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Paths
SAV_DIR = Path(r"C:\Users\hirzi\OneDrive\Documents\Default Project\data")
MANIFEST_PATH = SAV_DIR / "SAV_INTEGRITY_MANIFEST.json"
OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="sav_extraction_"))
LOG_PATH = OUTPUT_DIR / "extraction_log.json"


def verify_manifest():
    """Load and verify integrity manifest exists."""
    if not MANIFEST_PATH.exists():
        print(f"FATAL: Integrity manifest not found at {MANIFEST_PATH}")
        print("Run generate_sav_hashes.py first to create manifest.")
        sys.exit(1)
    
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    
    print(f"Manifest loaded: {len(manifest['files'])} files registered")
    return manifest


def verify_file_integrity(filename, expected_hash):
    """Verify SHA-256 hash of a file."""
    filepath = SAV_DIR / filename
    if not filepath.exists():
        return False, f"File not found: {filepath}"
    
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    
    actual_hash = sha256.hexdigest()
    if actual_hash != expected_hash:
        return False, f"Hash mismatch: expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
    
    return True, "OK"


def extract_sav_to_csv(filename):
    """Extract SAV file to CSV using pure Python parser."""
    # Import the existing parser (if available)
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from sav_to_csv import read_header, find_data_start, decompress_row_compatible
    except ImportError:
        print("WARNING: sav_to_csv.py not found, using minimal parser")
        return minimal_extract(filename)
    
    filepath = SAV_DIR / filename
    output_csv = OUTPUT_DIR / f"{Path(filename).stem}.csv"
    
    with open(filepath, 'rb') as f:
        header = read_header(f)
        data_start = find_data_start(f)
    
    with open(filepath, 'rb') as f:
        raw = f.read()
    
    var_offset = header['var_offset']
    ncases = header['ncases']
    
    rows = []
    pos = data_start
    for row_num in range(ncases):
        row_bytes, pos = decompress_row_compatible(raw, pos, var_offset)
        if len(row_bytes) < var_offset * 8:
            print(f"  WARNING: Row {row_num} incomplete")
            break
        
        # Decode row
        row = []
        for i in range(var_offset):
            val_bytes = row_bytes[i*8:(i+1)*8]
            # Try string first
            is_string = all(32 <= b < 127 or b == 0 for b in val_bytes)
            if is_string:
                sval = val_bytes.decode('ascii', errors='replace').rstrip('\x00')
                if sval and any(c.isalpha() for c in sval):
                    row.append(sval)
                    continue
            # Numeric
            import struct
            dval = struct.unpack('d', val_bytes)[0]
            row.append(str(dval))
        
        rows.append(row)
    
    # Write CSV
    with open(output_csv, 'w', newline='') as f:
        import csv
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
    
    return output_csv


def minimal_extract(filename):
    """Minimal SAV extraction (header + raw data dump)."""
    filepath = SAV_DIR / filename
    output_txt = OUTPUT_DIR / f"{Path(filename).stem}_raw.txt"
    
    with open(filepath, 'rb') as f:
        data = f.read(1024)  # First 1KB only
    
    with open(output_txt, 'w') as f:
        f.write(f"File: {filename}\n")
        f.write(f"Size: {os.path.getsize(filepath)} bytes\n")
        f.write(f"First 1024 bytes (hex):\n")
        f.write(data.hex())
    
    return output_txt


def main():
    print("=" * 60)
    print("ZERO-TRUST SAV EXTRACTION WRAPPER")
    print("=" * 60)
    
    # Step 1: Verify manifest
    manifest = verify_manifest()
    
    # Step 2: Verify all files
    print("\nVerifying file integrity...")
    all_valid = True
    for filename, info in manifest['files'].items():
        valid, msg = verify_file_integrity(filename, info['sha256'])
        status = "PASS" if valid else "FAIL"
        print(f"  [{status}] {filename}: {msg}")
        if not valid:
            all_valid = False
    
    if not all_valid:
        print("\nFATAL: Integrity verification failed. Aborting extraction.")
        sys.exit(1)
    
    print("\nAll files verified. Proceeding with extraction...")
    
    # Step 3: Extract each file
    extraction_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(OUTPUT_DIR),
        "files": {}
    }
    
    for filename in manifest['files']:
        print(f"\nExtracting: {filename}")
        try:
            output_path = extract_sav_to_csv(filename)
            extraction_log['files'][filename] = {
                "status": "success",
                "output": str(output_path)
            }
            print(f"  -> {output_path}")
        except Exception as e:
            extraction_log['files'][filename] = {
                "status": "error",
                "error": str(e)
            }
            print(f"  ERROR: {e}")
    
    # Step 4: Write log
    with open(LOG_PATH, 'w') as f:
        json.dump(extraction_log, f, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"Extraction complete. Output: {OUTPUT_DIR}")
    print(f"Log: {LOG_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
