"""
Parse references.bib file and store clean metadata in SQLite.
This provides the authoritative source for Crossref queries.
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, get_connection


def parse_bib_file(bib_path):
    """
    Parse a .bib file and extract reference entries.
    
    Args:
        bib_path: Path to the .bib file
        
    Returns:
        List of dictionaries with parsed reference data
    """
    if not os.path.exists(bib_path):
        print(f"Error: File not found: {bib_path}")
        return []
    
    with open(bib_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    references = []
    
    # Match each BibTeX entry
    entry_pattern = re.compile(
        r'@(\w+)\s*\{([^,]+),\s*(.*?)\n\}',
        re.DOTALL
    )
    
    for match in entry_pattern.finditer(content):
        entry_type = match.group(1).lower()
        cite_key = match.group(2).strip()
        fields_str = match.group(3)
        
        ref = {
            'cite_key': cite_key,
            'entry_type': entry_type,
        }
        
        # Parse fields
        field_pattern = re.compile(r'(\w+)\s*=\s*\{([^}]*)\}')
        for field_match in field_pattern.finditer(fields_str):
            field_name = field_match.group(1).lower()
            field_value = field_match.group(2).strip()
            ref[field_name] = field_value
        
        # Extract author list as normalized string
        if 'author' in ref:
            ref['authors_normalized'] = normalize_authors(ref['author'])
        else:
            ref['authors_normalized'] = ''
        
        # Extract year from 'year' field or 'date' field
        if 'year' in ref:
            year_match = re.search(r'(\d{4})', ref['year'])
            ref['year_normalized'] = int(year_match.group(1)) if year_match else None
        elif 'date' in ref:
            year_match = re.search(r'(\d{4})', ref['date'])
            ref['year_normalized'] = int(year_match.group(1)) if year_match else None
        else:
            ref['year_normalized'] = None
        
        # Normalize title (lowercase, strip whitespace)
        if 'title' in ref:
            ref['title_normalized'] = ref['title'].lower().strip()
        else:
            ref['title_normalized'] = ''
        
        # Extract DOI if present
        if 'doi' in ref:
            ref['doi'] = ref['doi'].strip()
        elif 'url' in ref and 'doi.org' in ref['url']:
            ref['doi'] = ref['url'].split('doi.org/')[-1]
        else:
            ref['doi'] = ''
        
        references.append(ref)
    
    return references


def normalize_authors(author_str):
    """
    Normalize author string to consistent format.
    
    Input: "Ahmad, Bin and Fatimah, Binti" or "Ahmad B and Fatimah B"
    Output: "Ahmad B, Fatimah B"
    """
    if not author_str:
        return ''
    
    # Split on ' and ' (BibTeX standard)
    authors = [a.strip() for a in author_str.split(' and ')]
    
    normalized = []
    for author in authors:
        # Handle "Last, First" format
        if ',' in author:
            parts = [p.strip() for p in author.split(',', 1)]
            last = parts[0]
            first = parts[1] if len(parts) > 1 else ''
            # Take first initial of first name
            if first:
                first_initial = first[0].upper()
                normalized.append(f"{last} {first_initial}")
            else:
                normalized.append(last)
        else:
            # Handle "First Last" format
            parts = author.strip().split()
            if len(parts) >= 2:
                last = parts[-1]
                first_initial = parts[0][0].upper()
                normalized.append(f"{last} {first_initial}")
            else:
                normalized.append(author.strip())
    
    return ', '.join(normalized)


def store_references(references):
    """
    Store parsed references in SQLite for use by fetch.py.
    
    Args:
        references: List of parsed reference dictionaries
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create table for clean references if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clean_references (
            cite_key TEXT PRIMARY KEY,
            entry_type TEXT,
            title TEXT,
            title_normalized TEXT,
            author TEXT,
            authors_normalized TEXT,
            year INTEGER,
            journal TEXT,
            volume TEXT,
            pages TEXT,
            doi TEXT,
            abstract TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    for ref in references:
        cursor.execute("""
            INSERT OR REPLACE INTO clean_references 
            (cite_key, entry_type, title, title_normalized, author, authors_normalized, 
             year, journal, volume, pages, doi, abstract)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ref.get('cite_key', ''),
            ref.get('entry_type', ''),
            ref.get('title', ''),
            ref.get('title_normalized', ''),
            ref.get('author', ''),
            ref.get('authors_normalized', ''),
            ref.get('year_normalized'),
            ref.get('journal', ref.get('booktitle', '')),
            ref.get('volume', ''),
            ref.get('pages', ''),
            ref.get('doi', ''),
            ref.get('abstract', ''),
        ))
    
    conn.commit()
    conn.close()


def run(bib_path):
    """
    Main parsing phase.
    
    Args:
        bib_path: Path to the .bib file
    """
    init_db()
    
    print(f"Parsing {bib_path}...")
    references = parse_bib_file(bib_path)
    
    if not references:
        print("No references found in .bib file.")
        return False
    
    print(f"Found {len(references)} references")
    
    # Store in database
    print("Storing references in database...")
    store_references(references)
    
    # Show summary
    print(f"\nParsed references:")
    for ref in references[:5]:  # Show first 5
        authors = ref.get('authors_normalized', 'Unknown')
        year = ref.get('year_normalized', 'n.d.')
        title = ref.get('title', 'Untitled')[:60]
        print(f"  {authors} ({year}). {title}...")
    if len(references) > 5:
        print(f"  ... and {len(references) - 5} more")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_references.py <path_to_references.bib>")
        print("Example: python parse_references.py references.bib")
        sys.exit(1)
    
    bib_path = sys.argv[1]
    success = run(bib_path)
    sys.exit(0 if success else 1)
