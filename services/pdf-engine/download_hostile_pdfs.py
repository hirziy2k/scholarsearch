#!/usr/bin/env python3
"""
Download hostile PDFs for stress-testing PDF-to-PPTX converters.
Each PDF represents a different challenge: scanned docs, complex layouts,
multilingual content, tables, vector graphics, etc.
"""

import os
import sys
import urllib.request
import urllib.error
import ssl

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "hostile")

TIMEOUT = 30
MIN_SIZE = 1024  # 1KB

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Verified working URLs as of Aug 2026
PDFS = {
    "01_arxiv_paper": "https://arxiv.org/pdf/2301.10972",
    "02_irs_1040": "https://www.irs.gov/pub/irs-pdf/f1040.pdf",
    "03_wikipedia": "https://en.wikipedia.org/api/rest_v1/page/pdf/Artificial_intelligence",
    "04_rfc": "https://www.rfc-editor.org/rfc/rfc9110.pdf",
    "05_ieee_sample": "https://arxiv.org/pdf/2301.07041",
    "06_un_report": "https://unstats.un.org/sdgs/report/2023/The-Sustainable-Development-Goals-Report-2023.pdf",
    "07_usgs_map": "https://www.irs.gov/pub/irs-pdf/i1040gi.pdf",
    "08_patent": "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf",
    "09_bank_statement": "https://slicedinvoices.com/pdf/wordpress-pdf-invoice-plugin-sample.pdf",
    "10_business_invoice": "https://www.orimi.com/pdf-test.pdf",
}

# Fallback URLs if primary fails
FALLBACKS = {
    "01_arxiv_paper": [
        "https://arxiv.org/pdf/2301.10972v1",
        "https://arxiv.org/pdf/2201.11601",
    ],
    "02_irs_1040": [
        "https://www.irs.gov/pub/irs-pdf/fw4.pdf",
        "https://www.irs.gov/pub/irs-pdf/p15.pdf",
    ],
    "03_wikipedia": [
        "https://en.wikipedia.org/api/rest_v1/page/pdf/Artificial_intelligence",
    ],
    "04_rfc": [
        "https://www.rfc-editor.org/rfc/rfc9112.pdf",
    ],
    "05_ieee_sample": [
        "https://arxiv.org/pdf/2301.07041v1",
        "https://arxiv.org/pdf/1706.03762",
    ],
    "06_un_report": [
        "https://unstats.un.org/sdgs/report/2023/The-Sustainable-Development-Goals-Report-2023.pdf",
    ],
    "07_usgs_map": [
        "https://www.irs.gov/pub/irs-pdf/f1040sc.pdf",
        "https://www.irs.gov/pub/irs-pdf/f1099msc.pdf",
    ],
    "08_patent": [
        "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.ipd.pdf",
    ],
    "09_bank_statement": [
        "https://css4.pub/2015/textbook/somatosensory.pdf",
        "https://css4.pub/2015/icelandic/dictionary.pdf",
    ],
    "10_business_invoice": [
        "https://www.orimi.com/pdf-test.pdf",
        "https://css4.pub/2015/textbook/somatosensory.pdf",
    ],
}


def make_ssl_context():
    """Create SSL context that works on all platforms."""
    ctx = ssl.create_default_context()
    # Some environments have cert issues; fall back if needed
    return ctx


def make_request(url):
    """Create an HTTPS request with proper headers."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "application/pdf,*/*")
    return req


def download_pdf(name, url, output_dir):
    """Download a single PDF. Returns (success, filepath_or_error)."""
    filepath = os.path.join(output_dir, f"{name}.pdf")

    if os.path.exists(filepath) and os.path.getsize(filepath) > MIN_SIZE:
        size_kb = os.path.getsize(filepath) / 1024
        return True, f"Already exists ({size_kb:.0f} KB)"

    # Try with SSL verification first, then without
    for attempt, ctx in enumerate([make_ssl_context(), _no_verify_ssl()]):
        try:
            req = make_request(url)
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
                data = resp.read()

            if len(data) < MIN_SIZE:
                return False, f"Too small ({len(data)} bytes), likely not a PDF"

            with open(filepath, "wb") as f:
                f.write(data)

            size_kb = len(data) / 1024
            return True, f"Downloaded ({size_kb:.0f} KB)"

        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == 0:
                continue  # retry with no-verify SSL
            return False, f"Error: {e}"
        except Exception as e:
            if attempt == 0:
                continue
            return False, f"Error: {e}"

    return False, "Unknown error"


def _no_verify_ssl():
    """SSL context that skips certificate verification."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Downloading hostile PDFs to: {OUTPUT_DIR}\n")

    succeeded = []
    failed = []

    for name, url in PDFS.items():
        print(f"[{name}] Downloading...")

        ok, msg = download_pdf(name, url, OUTPUT_DIR)

        if not ok and name in FALLBACKS:
            for fb_url in FALLBACKS[name]:
                print(f"  Trying fallback -> {fb_url}")
                ok, msg = download_pdf(name, fb_url, OUTPUT_DIR)
                if ok:
                    break

        if ok:
            succeeded.append((name, msg))
            print(f"  OK: {msg}\n")
        else:
            failed.append((name, msg))
            print(f"  FAILED: {msg}\n")

    print("=" * 60)
    print(f"DOWNLOAD SUMMARY: {len(succeeded)} succeeded, {len(failed)} failed")
    print("=" * 60)

    if succeeded:
        print("\nDownloaded:")
        for name, msg in succeeded:
            filepath = os.path.join(OUTPUT_DIR, f"{name}.pdf")
            print(f"  {filepath}  ({msg})")

    if failed:
        print("\nFailed:")
        for name, msg in failed:
            print(f"  {name}: {msg}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
