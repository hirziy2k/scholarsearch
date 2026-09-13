#!/usr/bin/env python3
"""
Egress-Filtered MCP Mirror Wrapper
- Intercepts network calls from MCP servers
- Validates against whitelist of allowed domains
- Blocks unauthorized outbound connections
- Logs all attempts for audit
"""

import os
import sys
import json
import socket
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Dict, List
from pathlib import Path
from contextlib import contextmanager

# Allowed domains (add as needed)
ALLOWED_DOMAINS = {
    # Academic APIs
    "api.openalex.org",
    "api.semanticscholar.org",
    "api.crossref.org",
    "api.core.ac.uk",
    "api.doaj.org",
    "api.eric.ed.gov",
    "eutils.ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "api.unpaywall.org",
    
    # MCP dependencies (PyPI)
    "pypi.org",
    "files.pythonhosted.org",
    
    # arxiv (HTTPS only)
    "export.arxiv.org",
    "arxiv.org",
}

# Blocked protocols
BLOCKED_PROTOCOLS = {"http:"}  # Only allow HTTPS

# Log file
LOG_DIR = Path(r"C:\Users\hirzi\OneDrive\Documents\Default Project\security_logs")
LOG_DIR.mkdir(exist_ok=True)
EGRESS_LOG = LOG_DIR / "egress_audit.jsonl"


def is_allowed_domain(domain: str) -> bool:
    """Check if domain is in whitelist."""
    return domain.lower() in ALLOWED_DOMAINS


def is_allowed_url(url: str) -> bool:
    """Validate URL against security policy."""
    # Must be HTTPS
    if not url.startswith("https://"):
        return False
    
    # Extract domain
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.hostname
        if not domain:
            return False
        
        # Check domain whitelist
        return is_allowed_domain(domain)
    except Exception:
        return False


def log_egress_attempt(url: str, allowed: bool, reason: str):
    """Log egress attempt for audit."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "allowed": allowed,
        "reason": reason
    }
    
    with open(EGRESS_LOG, 'a') as f:
        f.write(json.dumps(entry) + "\n")


def validate_request(url: str) -> bool:
    """
    Validate outbound request against security policy.
    Returns True if allowed, False if blocked.
    """
    # Check protocol
    if not url.startswith("https://"):
        log_egress_attempt(url, False, "BLOCKED: HTTP protocol not allowed")
        return False
    
    # Check domain
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.hostname
        
        if not domain:
            log_egress_attempt(url, False, "BLOCKED: No domain in URL")
            return False
        
        if not is_allowed_domain(domain):
            log_egress_attempt(url, False, f"BLOCKED: Domain not in whitelist: {domain}")
            return False
        
        log_egress_attempt(url, True, f"ALLOWED: Domain {domain} in whitelist")
        return True
    except Exception as e:
        log_egress_attempt(url, False, f"BLOCKED: URL parsing error: {e}")
        return False


@contextmanager
def egress_filtered():
    """
    Context manager that wraps urllib to enforce egress filtering.
    All outbound HTTP/HTTPS requests are validated against whitelist.
    """
    original_urlopen = urllib.request.urlopen
    
    def filtered_urlopen(url, *args, **kwargs):
        url_str = str(url)
        if not validate_request(url_str):
            raise urllib.error.URLError(f"BLOCKED: Egress filter denied request to {url_str}")
        return original_urlopen(url, *args, **kwargs)
    
    # Patch urllib
    urllib.request.urlopen = filtered_urlopen
    
    try:
        yield
    finally:
        # Restore original
        urllib.request.urlopen = original_urlopen


def test_egress_filter():
    """Test the egress filter with known URLs."""
    print("Testing egress filter...")
    
    test_cases = [
        ("https://api.openalex.org/works", True),
        ("http://api.openalex.org/works", False),  # HTTP blocked
        ("https://evil.com/steal", False),  # Not in whitelist
        ("https://api.semanticscholar.org/graph/v1/paper/search", True),
        ("http://export.arxiv.org/api/query", False),  # HTTP blocked
        ("https://export.arxiv.org/api/query", True),
    ]
    
    for url, expected in test_cases:
        result = is_allowed_url(url)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {url} -> {result} (expected {expected})")


if __name__ == "__main__":
    test_egress_filter()
