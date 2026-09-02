import random
import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from pathlib import Path

JITTER_RANGE = 0.03  # ±3% spatial jitter

_PUBLIC_FONTS = {
    "helvetica": "SystemSansSerif",
    "arial": "SystemSansSerif",
    "verdana": "SystemSansSerif",
    "tahoma": "SystemSansSerif",
    "calibri": "SystemSansSerif",
    "segoe": "SystemSansSerif",
    "futura": "SystemSansSerif",
    "candara": "SystemSansSerif",
    "droid": "SystemSansSerif",
    "opensans": "SystemSansSerif",
    "open sans": "SystemSansSerif",
    "times": "SystemSerif",
    "garamond": "SystemSerif",
    "georgia": "SystemSerif",
    "palatino": "SystemSerif",
    "baskerville": "SystemSerif",
    "bookman": "SystemSerif",
    "courier": "SystemMono",
    "consolas": "SystemMono",
    "menlo": "SystemMono",
    "monaco": "SystemMono",
    "liberation mono": "SystemMono",
}

_METADATA_RE = re.compile(
    r"(/(Author|Creator|Producer|Title|Subject|Keywords)"
    r"|/ModDate|/CreationDate)"
    r"\s*\([^)]*\)"
)
_URI_RE = re.compile(r"[a-z][a-z0-9+.-]*://[^\s)\]}'\"]+")


class VectorFuzzer:
    """Apply randomized spatial jitter and sanitize metadata from synthetic CI clones.

    When a user PDF fails and is promoted to CI, its exact geometry
    must be destroyed to prevent inference of the original data.
    """

    def __init__(self, seed: int = None):
        """Seed for reproducible fuzzing (same input → same output)."""
        self._seed = seed
        self._rng = random.Random(seed)

    def _jitter(self, value: float, bounds_min: float, bounds_max: float) -> float:
        low = -JITTER_RANGE
        high = JITTER_RANGE
        if bounds_max <= bounds_min:
            return bounds_min
        magnitude = (bounds_max - bounds_min) * 1e-4
        low -= magnitude
        high += magnitude
        factor = self._rng.uniform(low, high) + 1.0
        return max(bounds_min, min(bounds_max, value * factor))

    def fuzz_coordinates(self, x: float, y: float, width: float, height: float,
                          page_width: float, page_height: float) -> Tuple[float, float, float, float]:
        """Apply ±3% jitter to all coordinates.

        Never allows coordinates to go negative or exceed page bounds.
        Returns (fuzzed_x, fuzzed_y, fuzzed_w, fuzzed_h).
        """
        fw = width * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))
        fh = height * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))
        fx = self._jitter(x, 0.0, max(0.0, page_width - fw))
        fy = self._jitter(y, 0.0, max(0.0, page_height - fh))
        return round(fx, 6), round(fy, 6), round(fw, 6), round(fh, 6)

    def fuzz_font_name(self, font_name: str) -> str:
        """Genericize font names.

        Custom fonts → "CustomFont"
        Public fonts → "SystemSansSerif" or "SystemSerif" or "SystemMono"

        Prevents font fingerprinting.
        """
        if not font_name:
            return "SystemSansSerif"
        lower = font_name.lower().strip()

        for public, replacement in _PUBLIC_FONTS.items():
            if public in lower:
                return replacement

        return "CustomFont"

    def strip_metadata(self, pdf_bytes: bytes) -> bytes:
        """Strip all identifiable metadata from PDF bytes.

        Removes:
        - /Author, /Creator, /Producer, /Title, /Subject, /Keywords
        - /ModDate, /CreationDate
        - Any embedded URI strings
        - XMP metadata blocks

        Replaces with generic values.
        """
        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode("utf-8", errors="replace")
        text = pdf_bytes.decode("latin-1", errors="replace")

        text = _METADATA_RE.sub(lambda m: m.group(1) + " (fuzzed)", text)

        text = re.sub(r"<x:xmpmeta.*?</x:xmpmeta>", "", text, flags=re.DOTALL)

        text = _URI_RE.sub("generic://example.com/fuzzed", text)

        return text.encode("latin-1", errors="replace")

    def fuzz_structural_matrix(self, matrix: Dict) -> Dict:
        """Apply full fuzzing to a StructuralMatrix dict.

        1. Jitter all text_block coordinates (±3%)
        2. Jitter all table cell coordinates
        3. Jitter all vector paths
        4. Genericize all font names
        5. Remove any URI strings
        6. Remove author/creator metadata
        7. Generate deterministic hash for reproducibility
        """
        fuzzed = dict(matrix)
        fuzzed = self._deep_sanitize_strings(fuzzed)

        pages = fuzzed.get("pages")
        if pages is None and isinstance(fuzzed.get("page"), dict):
            pages = fuzzed["page"]
        if pages is None and isinstance(fuzzed.get("page"), list):
            pages = fuzzed["page"]

        page_h = float(fuzzed.get("page_height", 842))
        page_w = float(fuzzed.get("page_width", 595))

        if isinstance(pages, dict):
            looks_like_single_page = any(
                key in pages for key in ("text_blocks", "text", "tables",
                                         "table_cells", "vectors")
            )
            if looks_like_single_page:
                self._fuzz_page(pages, page_w, page_h, 1)
            else:
                for pageno, page in pages.items():
                    if isinstance(page, dict):
                        self._fuzz_page(page, page_w, page_h, pageno)
        elif isinstance(pages, list):
            for i, page in enumerate(pages):
                if isinstance(page, dict):
                    self._fuzz_page(page, page_w, page_h, i + 1)

        author = fuzzed.get("author", fuzzed.get("creator"))
        fuzzed.pop("author", None)
        fuzzed.pop("creator", None)
        fuzzed.pop("producer", None)
        fuzzed["author"] = "fuzzed"

        fuzzed["fuzz"] = {
            "seed": self._seed,
            "jitter_range": JITTER_RANGE,
            "author_original": author or "unknown",
            "hash": self._deterministic_hash(fuzzed),
        }
        return fuzzed

    @staticmethod
    def _deterministic_hash(data: Dict) -> str:
        serialized = _json_dumps_sorted(data)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _fuzz_page(self, page: Dict, page_w: float, page_h: float, pageno) -> None:
        if not isinstance(page, dict):
            return

        for block in page.get("text_blocks", page.get("text", [])) or []:
            if isinstance(block, dict):
                self._jitter_block(block, page_w, page_h)
                if "font" in block:
                    block["font"] = self.fuzz_font_name(block["font"])
                if "font_name" in block:
                    block["font_name"] = self.fuzz_font_name(block["font_name"])

        for table in page.get("tables", []) or []:
            if isinstance(table, dict):
                rows = table.get("rows", []) or []
                for row in rows:
                    if not isinstance(row, list):
                        continue
                    for cell in row:
                        if isinstance(cell, dict):
                            self._jitter_block(cell, page_w, page_h)
                            if "font" in cell:
                                cell["font"] = self.fuzz_font_name(cell["font"])
            elif isinstance(table, list):
                for cell in table:
                    if isinstance(cell, dict):
                        self._jitter_block(cell, page_w, page_h)
                        if "font" in cell:
                            cell["font"] = self.fuzz_font_name(cell["font"])

        for cell in page.get("table_cells", []) or []:
            if isinstance(cell, dict):
                self._jitter_block(cell, page_w, page_h)

        for vector in page.get("vectors", []) or []:
            if isinstance(vector, dict):
                self._fuzz_vector_path(vector, page_w, page_h)

    def _jitter_block(self, block: Dict, page_w: float, page_h: float) -> None:
        has_coords = any(k in block for k in ("x", "y", "width", "height", "w", "h"))
        if not has_coords:
            if "bbox" in block:
                bbox = block["bbox"]
                if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                    x0, y0, x1, y1 = (float(v) for v in bbox)
                    fx0, fy0, w, h = self._box_coords(x0, y0, x1 - x0, y1 - y0, page_w, page_h)
                    block["bbox"] = [round(fx0, 6), round(fy0, 6), round(fx0 + w, 6), round(fy0 + h, 6)]
            return

        x = float(block.get("x", block.get("left", 0)))
        y = float(block.get("y", block.get("top", 0)))
        w = float(block.get("width", block.get("w", 0)))
        h = float(block.get("height", block.get("h", 0)))

        fx, fy, fw, fh = self._box_coords(x, y, w, h, page_w, page_h)

        for key in ("x", "left"):
            if key in block:
                block[key] = fx
        for key in ("y", "top"):
            if key in block:
                block[key] = fy
        for key in ("width", "w"):
            if key in block:
                block[key] = fw
        for key in ("height", "h"):
            if key in block:
                block[key] = fh

    def _box_coords(self, x, y, w, h, page_w, page_h):
        fw = max(0.0, w * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE)))
        fh = max(0.0, h * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE)))
        max_x = max(0.0, page_w - fw)
        max_y = max(0.0, page_h - fh)
        fx = min(max(0.0, x * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))), max_x)
        fy = min(max(0.0, y * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))), max_y)
        return round(fx, 6), round(fy, 6), round(fw, 6), round(fh, 6)

    def _fuzz_vector_path(self, vector: Dict, page_w: float, page_h: float) -> None:
        if "path" in vector and isinstance(vector["path"], (list, tuple)):
            vector["path"] = [
                self._jitter_point(pt, page_w, page_h)
                for pt in vector["path"]
            ]
        for key in ("x", "y", "width", "height"):
            if key in vector:
                self._jitter_numeric(vector, key, page_w, page_h)
        if "points" in vector and isinstance(vector["points"], (list, tuple)):
            vector["points"] = [
                self._jitter_point(pt, page_w, page_h)
                for pt in vector["points"]
            ]
        if "bbox" in vector:
            self._jitter_block(vector, page_w, page_h)

    def _jitter_point(self, pt, page_w, page_h):
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            x, y = float(pt[0]), float(pt[1])
            fx = min(max(0.0, x * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))), page_w)
            fy = min(max(0.0, y * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))), page_h)
            result = list(pt)
            result[0] = round(fx, 6)
            result[1] = round(fy, 6)
            return tuple(result) if isinstance(pt, tuple) else result
        return pt

    def _jitter_numeric(self, d, key, page_w, page_h):
        try:
            val = float(d[key])
        except (TypeError, ValueError):
            return
        if key in ("x",):
            d[key] = round(min(max(0.0, val * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))), page_w), 6)
        elif key in ("y",):
            d[key] = round(min(max(0.0, val * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))), page_h), 6)
        elif key in ("width",):
            d[key] = round(max(0.0, val * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))), 6)
        elif key in ("height",):
            d[key] = round(max(0.0, val * (1.0 + self._rng.uniform(-JITTER_RANGE, JITTER_RANGE))), 6)

    def _deep_sanitize_strings(self, obj):
        if isinstance(obj, dict):
            return {k: self._deep_sanitize_strings(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._deep_sanitize_strings(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(self._deep_sanitize_strings(v) for v in obj)
        if isinstance(obj, str):
            return _URI_RE.sub("generic://example.com/fuzzed", obj)
        return obj

    def fuzz_geometry(self, blocks: List[Dict], page_w: float, page_h: float) -> List[Dict]:
        """Jitter a list of geometry blocks (text blocks, table cells, vectors)."""
        result = []
        for block in blocks or []:
            if not isinstance(block, dict):
                result.append(block)
                continue
            clone = dict(block)
            self._jitter_block(clone, page_w, page_h)
            self._fuzz_vector_path(clone, page_w, page_h)
            if "font" in clone:
                clone["font"] = self.fuzz_font_name(clone["font"])
            if "font_name" in clone:
                clone["font_name"] = self.fuzz_font_name(clone["font_name"])
            result.append(clone)
        return result

    def verify_no_leakage(self, original: Dict, fuzzed: Dict) -> dict:
        """Verify the fuzzed version is sufficiently different.

        Checks:
        1. No coordinate is identical to the original
        2. No font name matches original
        3. No URI strings remain
        4. Entropy of fuzzed data is sufficiently high

        Returns: {"safe": bool, "issues": [...]}
        """
        issues = []

        original_ids = set()
        self._collect_hashes(original, original_ids)

        fuzzed_original_coords = []
        self._collect_coords(original, fuzzed_original_coords)
        fuzzed_coords = []
        self._collect_coords(fuzzed, fuzzed_coords)

        original_set = {round(c, 3) for c in fuzzed_original_coords}
        for c in fuzzed_coords:
            if round(c, 3) in original_set:
                issues.append(f"Coordinate {c} identical to original")

        original_fonts = set()
        self._collect_fonts(original, original_fonts)
        fuzzed_fonts = set()
        self._collect_fonts(fuzzed, fuzzed_fonts)
        overlap = original_fonts & fuzzed_fonts
        for f in overlap:
            if _is_identifiable_font(f):
                issues.append(f"Font {f} matches original and is identifiable")

        leak_uris = []
        self._collect_uris(fuzzed, leak_uris, identify=True)
        for uri in leak_uris:
            issues.append(f"URI leaked: {uri}")

        sample = _json_bytes(fuzzed)
        entropy = _shannon_entropy(sample)
        if entropy < 1.0:
            issues.append(f"Entropy too low: {entropy:.3f}")

        return {
            "safe": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def _collect_coords(obj, out):
        if isinstance(obj, dict):
            for key, val in obj.items():
                if key in ("x", "y", "width", "height"):
                    if isinstance(val, (int, float)):
                        out.append(float(val))
                elif key == "bbox" and isinstance(val, (list, tuple)):
                    out.extend(float(v) for v in val)
                elif key == "path" and isinstance(val, (list, tuple)):
                    for pt in val:
                        if isinstance(pt, (list, tuple)):
                            out.extend(float(p) for p in pt[:2])
                else:
                    VectorFuzzer._collect_coords(val, out)
        elif isinstance(obj, list):
            for v in obj:
                VectorFuzzer._collect_coords(v, out)

    @staticmethod
    def _collect_fonts(obj, out):
        if isinstance(obj, dict):
            for key, val in obj.items():
                if key in ("font", "font_name") and isinstance(val, str):
                    out.add(val)
                elif isinstance(val, (dict, list)):
                    VectorFuzzer._collect_fonts(val, out)
        elif isinstance(obj, list):
            for v in obj:
                VectorFuzzer._collect_fonts(v, out)

    @staticmethod
    def _collect_uris(obj, out, identify=False):
        generic = "generic://example.com/fuzzed"
        if isinstance(obj, str):
            for match in _URI_RE.findall(obj):
                if identify and match == generic:
                    continue
                out.append(match)
        elif isinstance(obj, dict):
            for v in obj.values():
                VectorFuzzer._collect_uris(v, out, identify)
        elif isinstance(obj, list):
            for v in obj:
                VectorFuzzer._collect_uris(v, out, identify)

    @staticmethod
    def _collect_hashes(obj, out):
        if isinstance(obj, dict):
            for key, val in obj.items():
                if isinstance(val, (dict, list)):
                    VectorFuzzer._collect_hashes(val, out)
        elif isinstance(obj, list):
            for v in obj:
                VectorFuzzer._collect_hashes(v, out)


class MetadataAnnihilator:
    """Strip all identifiable metadata from files and dicts."""

    DANGEROUS_KEYS = {"author", "creator", "producer", "title", "subject", "keywords",
                      "moddate", "creationdate", "base", "metadata", "uri"}

    def sanitize_dict(self, data: Dict) -> Dict:
        """Recursively remove dangerous keys from a dict."""
        return self._sanitize(data)

    def _sanitize(self, obj):
        if isinstance(obj, dict):
            return {
                str(k).lower(): self._sanitize(v)
                for k, v in obj.items()
                if str(k).lower() not in self.DANGEROUS_KEYS
            }
        if isinstance(obj, list):
            return [self._sanitize(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(self._sanitize(v) for v in obj)
        if isinstance(obj, str):
            return _URI_RE.sub("generic://example.com/fuzzed", obj)
        return obj

    def sanitize_pdf_bytes(self, data: bytes) -> bytes:
        """Remove /Author, /Creator, /Title, XMP blocks from raw PDF bytes."""
        return VectorFuzzer().strip_metadata(data)

    def hash_for_audit(self, data: Dict) -> str:
        """Generate SHA-256 hash of fuzzed data for CI audit trail."""
        return VectorFuzzer._deterministic_hash(data)


async def safe_promote_to_ci_v2(feedback_entry, output_dir: str = "curriculum") -> str:
    """Enhanced safe promotion with vector fuzzing.

    1. Extract structural matrix
    2. Apply VectorFuzzer (±3% jitter, font genericization)
    3. Apply MetadataAnnihilator (strip URIs, author tags)
    4. Generate synthetic PDF from fuzzed matrix
    5. Save fuzzed matrix as JSON audit trail
    6. Return path to synthetic PDF
    """
    matrix = feedback_entry
    if isinstance(matrix, dict) and "matrix" in matrix:
        matrix = matrix["matrix"]

    fuzzer = VectorFuzzer(seed=int(time_ns() % (2 ** 31)))
    annihilator = MetadataAnnihilator()

    fuzzed_matrix = fuzzer.fuzz_structural_matrix(dict(matrix))
    fuzzed_matrix = annihilator.sanitize_dict(fuzzed_matrix)

    audit = {
        "hash": annihilator.hash_for_audit(fuzzed_matrix),
        "length": len(_json_bytes(fuzzed_matrix)),
    }

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    audit_path = output / f"audit_{audit['hash'][:12]}.json"
    audit_path.write_text(_json_dumps(fuzzed_matrix), encoding="utf-8")

    synthetic_pdf = output / f"synthetic_{audit['hash'][:12]}.pdf"
    pdf_bytes = _matrix_to_pdf_bytes(fuzzed_matrix)
    synthetic_pdf.write_bytes(pdf_bytes)

    return str(synthetic_pdf)


def _is_identifiable_font(font: str) -> bool:
    return font not in {"SystemSansSerif", "SystemSerif", "SystemMono", "CustomFont"}


def _json_dumps_sorted(data: Dict) -> str:
    import json

    def sort_key(pair):
        key, val = pair
        if isinstance(val, dict):
            return (key, sorted(val.items(), key=lambda kv: str(kv[0])))
        if isinstance(val, list):
            return (key, sorted(val, key=_json_sortable))
        return (key, val)

    return json.dumps(data, sort_keys=True, default=str)


def _json_sortable(val):
    if isinstance(val, dict):
        return json.dumps(val, sort_keys=True, default=str)
    if isinstance(val, list):
        return json.dumps(val, default=str)
    return str(val)


def _json_bytes(data) -> bytes:
    return _json_dumps_sorted(data).encode("utf-8")


def _json_dumps(data) -> str:
    import json
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def _shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    from collections import Counter
    counter = Counter(data)
    length = len(data)
    entropy = -sum((count / length) * __import__("math").log2(count / length)
                   for count in counter.values())
    return entropy


def _matrix_to_pdf_bytes(matrix: Dict) -> bytes:
    import io
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        return b"%PDF-1.4\nfuzzed synthetic placeholder (reportlab unavailable)"

    buf = io.BytesIO()
    page_w = float(matrix.get("page_width", 595))
    page_h = float(matrix.get("page_height", 842))
    default_style = matrix.get("style", {})

    if "pages" in matrix and isinstance(matrix["pages"], list):
        total = max(len(matrix["pages"]), 1)
    elif isinstance(matrix.get("page"), dict):
        total = 1
    else:
        total = 1

    first = True
    for i in range(total):
        page = None
        if isinstance(matrix.get("pages"), list) and i < len(matrix["pages"]):
            page = matrix["pages"][i]
        elif i == 0 and isinstance(matrix.get("page"), dict):
            page = matrix["page"]

        if first:
            c = canvas.Canvas(buf, pagesize=(page_w, page_h))
            first = False
        else:
            c.showPage()
            c = canvas.Canvas(buf, pagesize=(page_w, page_h))

        page = page or {}
        for block in page.get("text_blocks", page.get("text", [])) or []:
            if not isinstance(block, dict):
                continue
            x = float(block.get("x", block.get("left", 0)))
            y = float(block.get("y", block.get("top", 0)))
            w = float(block.get("width", block.get("w", 0)))
            font = "Helvetica"
            if block.get("font") == "SystemMono":
                font = "Courier"
            elif block.get("font") == "SystemSerif":
                font = "Times-Roman"
            c.setFont(font, 10)
            c.drawString(x, page_h - y, str(block.get("text", "fuzzed"))[: int(w) if w else 50])

    try:
        c.save()
    except Exception:
        return b"%PDF-1.4\nfuzzed synthetic error"
    return buf.getvalue()


def time_ns():
    import time
    return time.time_ns()


if __name__ == "__main__":
    import asyncio

    sample = {
        "page_width": 595,
        "page_height": 842,
        "author": "Jane Doe",
        "creator": "PDFKit",
        "page": {
            "text_blocks": [
                {"x": 150.0, "y": 220.0, "width": 320, "height": 48, "font": "Times", "text": "hello https://example.com/secret"},
            ],
            "tables": [
                [{"x": 120.0, "y": 340.0, "width": 180, "height": 62}],
            ],
            "vectors": [
                {"path": [[110.0, 480.0], [230.0, 540.0]], "bbox": [98.0, 470.0, 244.0, 556.0]},
            ],
        },
    }

    fz = VectorFuzzer(seed=42)
    out = fz.fuzz_structural_matrix(sample)
    an = MetadataAnnihilator()
    out = an.sanitize_dict(out)
    print("fuzzed:", _json_dumps(out)[:400])
    print("verification:", fz.verify_no_leakage(sample, out))

    async def demo():
        path = await safe_promote_to_ci_v2(sample, output_dir="curriculum")
        print("written:", path)

    asyncio.run(demo())
