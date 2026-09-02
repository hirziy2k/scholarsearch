"""Pre-flight PDF Sanitization Layer for the PDF-to-PPTX converter.

Validates and sanitizes PDFs before they reach PyMuPDF (fitz), protecting
against weaponized PDFs with malicious JavaScript, XFA forms, zip bombs,
and corrupted cross-reference tables.

No external dependencies — standard library only.
"""

import re
import zlib
import struct
import sys
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SanitizeResult:
    """Result of a PDF sanitization run."""
    safe: bool
    sanitized_path: str
    original_size: int
    sanitized_size: int
    threats_found: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    time_ms: float = 0.0


class PDFSanitizer:
    """Pre-flight sandbox: validate and sanitize PDFs before they reach PyMuPDF."""

    MAX_FILE_SIZE_MB = 100
    MAX_PAGE_COUNT = 500
    MAX_OBJECTS = 50000
    MAX_XREF_ENTRIES = 100000

    def sanitize(self, input_path: str, output_path: str = None) -> SanitizeResult:
        """Full sanitization pipeline. Returns sanitized file path + report."""
        start = time.monotonic()
        result = SanitizeResult(safe=True, sanitized_path="", original_size=0, sanitized_size=0)

        try:
            input_path_obj = Path(input_path)
            if not input_path_obj.exists():
                result.validation_errors.append(f"File not found: {input_path}")
                return result

            data = input_path_obj.read_bytes()
            result.original_size = len(data)

        except Exception as e:
            result.validation_errors.append(f"Failed to read file: {e}")
            return result

        threats: List[str] = []
        warnings: List[str] = []
        validation_errors: List[str] = []

        # Step 1: Validate structure
        errors = self.validate_structure(data)
        validation_errors.extend(errors)

        if not data.startswith(b"%PDF-"):
            result.validation_errors = validation_errors
            result.safe = False
            result.threats_found = threats
            result.warnings = warnings
            result.time_ms = (time.monotonic() - start) * 1000
            result.sanitized_path = input_path
            return result

        # Step 2: Strip JS
        has_js = self._has_javascript(data)
        if has_js:
            threats.append("javascript")
            data = self.strip_javascript(data)

        # Step 3: Strip XFA
        has_xfa = self._has_xfa(data)
        if has_xfa:
            threats.append("xfa_form")
            data = self.strip_xfa_forms(data)

        # Step 4: Check zip bombs
        is_zip_bomb = self.check_zip_bomb(data)
        if is_zip_bomb:
            threats.append("zip_bomb")
            warnings.append("Potential zip bomb detected; some streams flagged")

        # Step 5: Recompress oversized streams (only if threats found)
        if threats:
            try:
                data = self.recompress_streams(data)
            except Exception as e:
                warnings.append(f"Stream recompression skipped: {e}")

        # Step 6: Save sanitized file
        if output_path is None:
            output_dir = input_path_obj.parent
            output_path = str(output_dir / (input_path_obj.stem + "_sanitized.pdf"))

        try:
            Path(output_path).write_bytes(data)
            result.sanitized_path = output_path
            result.sanitized_size = len(data)
        except Exception as e:
            result.validation_errors.append(f"Failed to write sanitized file: {e}")
            result.sanitized_path = input_path
            result.sanitized_size = len(data)

        result.safe = len(threats) == 0 and len(validation_errors) == 0
        result.threats_found = threats
        result.warnings = warnings
        result.validation_errors = validation_errors
        result.time_ms = (time.monotonic() - start) * 1000

        return result

    def validate_structure(self, data: bytes) -> List[str]:
        """Validate PDF structure WITHOUT opening in a C parser.

        Checks:
        1. Magic bytes: starts with %PDF-
        2. Cross-reference table exists (look for 'startxref' and '%%EOF')
        3. No embedded JavaScript: scan for /JavaScript, /JS, JavaScript()
        4. No XFA forms: scan for /XFA, XFA=true
        5. No embedded files: scan for /EmbeddedFile, /FileAttachment
        6. No OpenAction with URI/JS: scan for /OpenAction
        7. Object count sanity check (count 'obj' markers)
        """
        errors: List[str] = []

        # 1. Magic bytes
        if not data.startswith(b"%PDF-"):
            errors.append("Invalid PDF: missing %PDF- magic bytes")

        # 2. Cross-reference and EOF markers
        if b"startxref" not in data:
            errors.append("Invalid PDF: missing startxref marker")
        if not data.rstrip().endswith(b"%%EOF") and b"%%EOF" not in data[-64:]:
            errors.append("Invalid PDF: missing %%EOF marker")

        # 3. JavaScript
        if self._has_javascript(data):
            warnings_msg = "Embedded JavaScript detected (/JavaScript or /JS)"
            errors.append(warnings_msg)

        # 4. XFA forms
        if self._has_xfa(data):
            errors.append("XFA form detected")

        # 5. Embedded files
        if b"/EmbeddedFile" in data or b"/FileAttachment" in data:
            errors.append("Embedded file detected (/EmbeddedFile or /FileAttachment)")

        # 6. OpenAction
        if self._has_suspicious_openaction(data):
            errors.append("Suspicious /OpenAction detected (may reference JS or URI)")

        # 7. Object count
        obj_count = data.count(b" obj")
        if obj_count > self.MAX_OBJECTS:
            errors.append(
                f"Object count {obj_count} exceeds limit of {self.MAX_OBJECTS}"
            )

        # Page count heuristic
        page_count = self._estimate_page_count(data)
        if page_count > self.MAX_PAGE_COUNT:
            errors.append(
                f"Estimated page count {page_count} exceeds limit of {self.MAX_PAGE_COUNT}"
            )

        # Xref entry count heuristic
        xref_count = self._estimate_xref_count(data)
        if xref_count > self.MAX_XREF_ENTRIES:
            errors.append(
                f"Estimated xref entries {xref_count} exceeds limit of {self.MAX_XREF_ENTRIES}"
            )

        return errors

    def strip_javascript(self, data: bytes) -> bytes:
        """Remove JavaScript from PDF byte stream.

        Strategy (byte-level, no C parser needed):
        - Find and remove /JavaScript or /JS dictionary entries
        - Remove /OpenAction entries that reference JavaScript
        - Remove /Launch actions
        - Preserve all other PDF structure
        """
        result = data

        # Remove /JavaScript <hex-string> or /JavaScript (literal-string)
        # Pattern: /JavaScript followed by a string object reference or literal
        result = re.sub(
            rb"/JavaScript\s*\([^)]*\)",
            rb"",
            result,
        )
        result = re.sub(
            rb"/JavaScript\s*<[^>]*>",
            rb"",
            result,
        )
        result = re.sub(
            rb"/JavaScript\s*\d+\s+\d+\s+R",
            rb"",
            result,
        )
        result = re.sub(
            rb"/JavaScript\s+true",
            rb"",
            result,
        )

        # Remove /JS <string> or /JS (string)
        result = re.sub(
            rb"/JS\s*\([^)]*\)",
            rb"",
            result,
        )
        result = re.sub(
            rb"/JS\s*<[^>]*>",
            rb"",
            result,
        )
        result = re.sub(
            rb"/JS\s*\d+\s+\d+\s+R",
            rb"",
            result,
        )

        # Remove /OpenAction that contains /JS or /JavaScript
        # This is a heuristic: find /OpenAction blocks and remove if they reference JS
        result = self._strip_openaction_js(result)

        # Remove /Launch actions
        result = re.sub(
            rb"/Type\s*/Action\s*/S\s*/Launch",
            rb"/Type /Action /S /None",
            result,
        )
        result = re.sub(
            rb"/S\s*/Launch\b",
            rb"/S /None",
            result,
        )

        return result

    def strip_xfa_forms(self, data: bytes) -> bytes:
        """Remove XFA form packets from the PDF.

        XFA forms are XML packets embedded in the PDF that can contain
        arbitrary code. They are delimited by <?xpacket ... ?> markers.
        """
        result = data

        # Remove xpacket blocks (both <?xpacket begin= and <?xpacket end=)
        pattern = rb"<\?xpacket\b[^?]*\?>.*?<\?xpacket\s+end\s*=\s*\"[^\"]*\"\s*\?>"
        result = re.sub(pattern, b"", result, flags=re.DOTALL)

        # Remove /XFA dictionary entries that reference stream objects
        result = re.sub(
            rb"/XFA\s*\d+\s+\d+\s+R",
            rb"",
            result,
        )

        # Remove inline XFA arrays
        result = re.sub(
            rb"/XFA\s*\[([^\]]*)\]",
            rb"",
            result,
        )

        # Remove /XFA true/false
        result = re.sub(
            rb"/XFA\s+(true|false)",
            rb"",
            result,
        )

        return result

    def check_zip_bomb(self, data: bytes, max_streams: int = 50) -> bool:
        """Detect potential zip-bomb-like compression ratios.

        If any FlateDecode stream has compression ratio > 100:1,
        flag it as suspicious. Recompress to check actual size.
        Limits check to first max_streams streams for performance.
        """
        # Find FlateDecode streams: look for stream ... endstream blocks
        stream_positions = []
        idx = 0
        while len(stream_positions) < max_streams:
            start = data.find(b"stream", idx)
            if start == -1:
                break
            # The stream data starts after "stream\r\n" or "stream\n"
            data_start = start + len(b"stream")
            if data_start < len(data) and data[data_start:data_start + 2] == b"\r\n":
                data_start += 2
            elif data_start < len(data) and data[data_start:data_start + 1] == b"\n":
                data_start += 1
            else:
                idx = start + 1
                continue

            end = data.find(b"endstream", data_start)
            if end == -1:
                idx = start + 1
                continue

            # Strip trailing whitespace before endstream
            stream_data = data[data_start:end].rstrip(b" \t\r\n")
            if stream_data:
                stream_positions.append((data_start, end, stream_data))
            idx = end + 1

        for _, _, stream_data in stream_positions:
            try:
                decompressed = zlib.decompress(stream_data)
                compressed_len = len(stream_data)
                decompressed_len = len(decompressed)
                if compressed_len > 0:
                    ratio = decompressed_len / compressed_len
                    if ratio > 100:
                        return True
            except zlib.error:
                # Not a valid FlateDecode stream, skip
                continue

        return False

    def recompress_streams(self, data: bytes, max_streams: int = 30) -> bytes:
        """Recompress streams that exceed safe thresholds.

        For streams with excessive uncompressed size:
        - Decompress to check actual size
        - If actual size > 50MB, skip (too large to safely process)
        - Otherwise, recompress normally
        - Limits to first max_streams streams for performance
        """
        result = bytearray(data)
        offset_adjustment = 0
        stream_regions = []

        idx = 0
        while len(stream_regions) < max_streams:
            start = result.find(b"stream", idx)
            if start == -1:
                break
            data_start = start + len(b"stream")
            if data_start < len(result) and result[data_start:data_start + 2] == b"\r\n":
                data_start += 2
            elif data_start < len(result) and result[data_start:data_start + 1] == b"\n":
                data_start += 1
            else:
                idx = start + 1
                continue

            end = result.find(b"endstream", data_start)
            if end == -1:
                idx = start + 1
                continue

            stream_data = bytes(result[data_start:end].rstrip(b" \t\r\n"))
            stream_regions.append((start, data_start, end, stream_data))
            idx = end + 1

        MAX_DECOMPRESSED = 50 * 1024 * 1024  # 50 MB

        for original_start, data_start, end, stream_data in reversed(stream_regions):
            if not stream_data:
                continue

            try:
                decompressed = zlib.decompress(stream_data)
            except zlib.error:
                continue

            if len(decompressed) > MAX_DECOMPRESSED:
                continue

            try:
                recompressed = zlib.compress(decompressed)
            except Exception:
                continue

            if len(recompressed) >= len(stream_data):
                continue

            old_total = end - original_start
            new_stream_block = b"stream\n" + recompressed + b"\nendstream"

            result[original_start:old_total + original_start] = new_stream_block

        return bytes(result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _has_javascript(self, data: bytes) -> bool:
        """Check for JavaScript markers in raw PDF bytes."""
        if re.search(rb"/JavaScript\b", data):
            return True
        # /JS must be followed by a space and a string-like value, not just
        # any occurrence of "/JS" which could be a substring of something else.
        if re.search(rb"/JS\s+[\(\[<\d]", data):
            return True
        return False

    def _has_xfa(self, data: bytes) -> bool:
        """Check for XFA form markers."""
        if re.search(rb"/XFA\b", data):
            return True
        if b"<?xpacket" in data:
            return True
        return False

    def _has_suspicious_openaction(self, data: bytes) -> bool:
        """Check for /OpenAction entries that might launch JS or URIs."""
        # Look for /OpenAction near /JS, /JavaScript, or /URI
        for match in re.finditer(rb"/OpenAction\b", data):
            window_start = match.start()
            window_end = min(match.start() + 200, len(data))
            window = data[window_start:window_end]
            if re.search(rb"/JS\b", window) or re.search(rb"/JavaScript\b", window):
                return True
            if re.search(rb"/URI\b", window):
                return True
            if re.search(rb"/S\s*/Launch", window):
                return True
        return False

    def _strip_openaction_js(self, data: bytes) -> bytes:
        """Remove /OpenAction entries that reference JavaScript."""
        result = data

        # Remove /OpenAction dictionaries that contain /JS or /JavaScript
        # Heuristic: find /OpenAction, then look for the enclosing dict
        # We try to match /OpenAction followed by a dict or indirect ref
        # and strip the whole /OpenAction ... value pair.

        # Strategy: find each /OpenAction, extract the 200 bytes after it,
        # check if it references JS, and if so remove the /OpenAction key + value.

        positions = []
        for match in re.finditer(rb"/OpenAction\b", result):
            window_end = min(match.start() + 300, len(result))
            window = result[match.start():window_end]

            has_js = (
                re.search(rb"/JS\b", window)
                or re.search(rb"/JavaScript\b", window)
                or re.search(rb"/S\s*/Launch", window)
            )
            if has_js:
                positions.append((match.start(), window_end))

        # Remove from end to preserve earlier offsets
        for start_pos, end_pos in reversed(positions):
            result = result[:start_pos] + result[end_pos:]

        return result

    def _estimate_page_count(self, data: bytes) -> int:
        """Estimate page count by counting /Type /Page (but not /Pages) entries."""
        pages = len(re.findall(rb"/Type\s*/Page\b(?!\s*?s)", data))
        return pages

    def _estimate_xref_count(self, data: bytes) -> int:
        """Estimate cross-reference entry count by counting 'obj' markers."""
        return data.count(b" obj")


def sanitize_pdf(input_path: str, output_dir: str = None) -> SanitizeResult:
    """One-call API for the orchestrator.

    1. Validate structure (byte-level, fast)
    2. Strip JS if found
    3. Strip XFA if found
    4. Check for zip bombs
    5. Save sanitized version
    6. Return result
    """
    sanitizer = PDFSanitizer()

    output_path = None
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        stem = Path(input_path).stem
        output_path = os.path.join(output_dir, f"{stem}_sanitized.pdf")

    return sanitizer.sanitize(input_path, output_path)


def _format_size(size_bytes: int) -> str:
    """Format byte count as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main() -> int:
    """CLI entry point: python pdf_sandbox.py <pdf_path>"""
    if len(sys.argv) < 2:
        print("Usage: python pdf_sandbox.py <pdf_path>")
        return 1

    pdf_path = sys.argv[1]
    print(f"Scanning: {pdf_path}")
    print("-" * 60)

    result = sanitize_pdf(pdf_path)

    print(f"Original size:   {_format_size(result.original_size)}")
    print(f"Sanitized size:  {_format_size(result.sanitized_size)}")
    print(f"Scan time:       {result.time_ms:.1f} ms")
    print()

    if result.safe:
        print("STATUS: SAFE")
    else:
        print("STATUS: UNSAFE")
    print()

    if result.threats_found:
        print("Threats found:")
        for t in result.threats_found:
            print(f"  - {t}")
    else:
        print("Threats found: none")
    print()

    if result.validation_errors:
        print("Validation errors:")
        for e in result.validation_errors:
            print(f"  - {e}")
    else:
        print("Validation errors: none")
    print()

    if result.warnings:
        print("Warnings:")
        for w in result.warnings:
            print(f"  - {w}")
    else:
        print("Warnings: none")
    print()

    print(f"Sanitized file: {result.sanitized_path}")

    return 0 if result.safe else 2


if __name__ == "__main__":
    sys.exit(main())
