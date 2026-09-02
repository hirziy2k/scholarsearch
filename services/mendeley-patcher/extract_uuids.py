"""
Phase 1: Extract Mendeley UUIDs from .docx files.
Treats .docx as a ZIP archive and scrapes UUIDs from word/document.xml.
Supports both Mendeley Desktop (legacy) and Mendeley Cite (current) formats.
"""

import zipfile
import re
import sys
import os
import shutil
import tempfile
import time
import base64
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, upsert_document, get_stats


def _register_temp_cleanup(temp_dir):
    """Register temp directory for cleanup on abnormal termination."""
    try:
        import atexit
        import signal
        
        def cleanup():
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
        
        atexit.register(cleanup)
        
        def signal_handler(signum, frame):
            cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    except:
        pass


# Mendeley UUID pattern (standard UUID v4 format)
UUID_PATTERN = re.compile(r'"id"\s*:\s*"([a-f0-9\-]{36})"')

# Alternative patterns for different Mendeley versions
ALT_PATTERNS = [
    re.compile(r'mendeley[_-]id\s*[:=]\s*"([a-f0-9\-]{36})"'),
    re.compile(r'document[_-]id\s*[:=]\s*"([a-f0-9\-]{36})"'),
    re.compile(r'guid\s*[:=]\s*"([a-f0-9\-]{36})"'),
]

# Mendeley Cite pattern (w:tag attribute with base64-encoded JSON)
# Matches MENDELEY_CITATION_v1_, MENDELEY_CITATION_v2_, MENDELEY_CITATION_v3_, etc.
MENDELEY_CITE_PATTERN = re.compile(r'w:tag\s*w:val\s*=\s*"MENDELEY_CITATION_v\d+_([^"]+)"')


def _decode_mendeley_cite_tag(tag_value):
    """
    Decode base64-encoded citation data from Mendeley Cite w:tag attribute.
    
    Args:
        tag_value: Base64-encoded string after MENDELEY_CITATION_v*_ 
                   (may include version prefix like v3_)
        
    Returns:
        Set of UUID strings found in the decoded data
    """
    uuids = set()
    
    try:
        # Strip versioning prefix if present (e.g., 'v3_' or 'v1_')
        b64_str = re.sub(r'^v\d+_', '', tag_value)
        
        # Add padding if needed
        padding = 4 - len(b64_str) % 4
        if padding != 4:
            b64_str += '=' * padding
        
        # Decode base64
        decoded = base64.b64decode(b64_str).decode('utf-8')
        
        # Try to parse as JSON
        try:
            data = json.loads(decoded)
        except json.JSONDecodeError:
            # If not valid JSON, try to extract UUIDs directly from text
            for match in UUID_PATTERN.finditer(decoded):
                uuids.add(match.group(1))
            return uuids
        
        # Extract citationID (starts with MENDELEY_CITATION_)
        if 'citationID' in data:
            citation_id = data['citationID']
            # Extract UUID from citationID (format: MENDELEY_CITATION_{uuid})
            if citation_id.startswith('MENDELEY_CITATION_'):
                uuid_part = citation_id.replace('MENDELEY_CITATION_', '')
                if len(uuid_part) == 36 and re.match(r'^[a-f0-9\-]{36}$', uuid_part):
                    uuids.add(uuid_part)
        
        # Extract UUIDs from citationItems
        if 'citationItems' in data:
            for item in data['citationItems']:
                if 'id' in item:
                    item_id = item['id']
                    if len(item_id) == 36 and re.match(r'^[a-f0-9\-]{36}$', item_id):
                        uuids.add(item_id)
                
                # Also check itemData.id
                if 'itemData' in item and 'id' in item['itemData']:
                    item_data_id = item['itemData']['id']
                    if len(item_data_id) == 36 and re.match(r'^[a-f0-9\-]{36}$', item_data_id):
                        uuids.add(item_data_id)
        
        # Extract from manualOverride.citeprocText if present
        if 'manualOverride' in data:
            override = data['manualOverride']
            if 'citeprocText' in override:
                # Try to find UUIDs in the text
                for match in UUID_PATTERN.finditer(override['citeprocText']):
                    uuids.add(match.group(1))
        
    except Exception as e:
        print(f"  Warning: Failed to decode Mendeley Cite tag: {e}")
    
    return uuids


def extract_uuids_from_docx(docx_path):
    """
    Extract Mendeley UUIDs from a .docx file.
    
    Copies the file to a temporary location first to avoid OneDrive/Word locks.
    
    Args:
        docx_path: Path to the .docx file
        
    Returns:
        Set of UUID strings found in the document
    """
    print(f"Unpacking {docx_path} in memory...")
    
    uuids = set()
    
    # Copy to temp location to avoid OneDrive/Word file locks
    temp_dir = tempfile.mkdtemp(prefix="mendeley_patcher_")
    temp_docx = os.path.join(temp_dir, os.path.basename(docx_path))
    
    # Register for cleanup on abnormal termination
    _register_temp_cleanup(temp_dir)
    
    try:
        shutil.copy2(docx_path, temp_docx)
        print(f"Copied to temporary location: {temp_docx}")
        
        # Small delay to ensure file handle is released
        time.sleep(0.5)
        
        with zipfile.ZipFile(temp_docx, 'r') as docx_zip:
            # Try to read the main document body
            xml_files = [f for f in docx_zip.namelist() if 'document.xml' in f.lower()]
            
            if not xml_files:
                print("Warning: No document.xml found in .docx archive")
                return uuids
            
            for xml_file in xml_files:
                print(f"Scanning: {xml_file}")
                xml_content = docx_zip.read(xml_file).decode('utf-8')
                
                # Try primary pattern (Mendeley Desktop format)
                matches = UUID_PATTERN.findall(xml_content)
                for match in matches:
                    uuids.add(match)
                
                # Try alternative patterns (Mendeley Desktop format)
                for pattern in ALT_PATTERNS:
                    matches = pattern.findall(xml_content)
                    for match in matches:
                        uuids.add(match)
                
                # Try Mendeley Cite pattern (new format with base64-encoded JSON)
                cite_matches = MENDELEY_CITE_PATTERN.findall(xml_content)
                for match in cite_matches:
                    decoded_uuids = _decode_mendeley_cite_tag(match)
                    uuids.update(decoded_uuids)
            
            # Also check custom XML parts (Mendeley sometimes stores data here)
            custom_xml_files = [f for f in docx_zip.namelist() if 'customXml' in f]
            for xml_file in custom_xml_files:
                try:
                    xml_content = docx_zip.read(xml_file).decode('utf-8')
                    for pattern in [UUID_PATTERN] + ALT_PATTERNS:
                        matches = pattern.findall(xml_content)
                        for match in matches:
                            uuids.add(match)
                except Exception:
                    continue
            
            # Check webextension1.xml (Mendeley Cite stores metadata here)
            webextension_files = [f for f in docx_zip.namelist() if 'webextension' in f.lower()]
            for xml_file in webextension_files:
                try:
                    print(f"Scanning web extension: {xml_file}")
                    xml_content = docx_zip.read(xml_file).decode('utf-8')
                    for pattern in [UUID_PATTERN] + ALT_PATTERNS:
                        matches = pattern.findall(xml_content)
                        for match in matches:
                            uuids.add(match)
                except Exception:
                    continue
                    
    except zipfile.BadZipFile:
        print(f"Error: {docx_path} is not a valid ZIP/archived file")
        return uuids
    except PermissionError as e:
        print(f"Error: Permission denied reading {docx_path}")
        print("Make sure Microsoft Word is closed and OneDrive is not syncing the file.")
        return uuids
    except Exception as e:
        print(f"Error reading {docx_path}: {e}")
        return uuids
    finally:
        # Clean up temp directory
        try:
            if os.path.exists(temp_docx):
                os.remove(temp_docx)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except:
            pass
    
    print(f"Extracted {len(uuids)} unique Mendeley UUIDs")
    return uuids


def run(docx_path):
    """
    Main extraction phase.
    
    Args:
        docx_path: Path to the .docx file
    """
    if not os.path.exists(docx_path):
        print(f"Error: File not found: {docx_path}")
        return False
    
    # Initialize database
    init_db()
    
    # Extract UUIDs
    uuids = extract_uuids_from_docx(docx_path)
    
    if not uuids:
        print("No Mendeley UUIDs found in document.")
        print("Possible reasons:")
        print("  - Document has no Mendeley citations")
        print("  - Citations were inserted using a different method")
        print("  - UUID pattern has changed in newer Mendeley versions")
        print()
        print("Note: This tool supports both Mendeley Desktop and Mendeley Cite formats.")
        print("If you're using Mendeley Cite, make sure the document has been saved")
        print("after inserting citations.")
        return False
    
    # Insert into database
    print(f"\nInserting {len(uuids)} UUIDs into database...")
    for uuid in uuids:
        try:
            upsert_document(uuid, state="DISCOVERED")
            print(f"  + {uuid}")
        except Exception as e:
            print(f"  ! Error inserting {uuid}: {e}")
    
    # Show stats
    stats = get_stats()
    print(f"\nDatabase status:")
    print(f"  DISCOVERED: {stats['DISCOVERED']}")
    print(f"  FETCHED: {stats['FETCHED']}")
    print(f"  DIFFED: {stats['DIFFED']}")
    print(f"  APPROVED: {stats['APPROVED']}")
    print(f"  PATCHED: {stats['PATCHED']}")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_uuids.py <path_to_docx>")
        print("Example: python extract_uuids.py thesis.docx")
        sys.exit(1)
    
    docx_path = sys.argv[1]
    success = run(docx_path)
    sys.exit(0 if success else 1)
