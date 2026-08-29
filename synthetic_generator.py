"""
Synthetic Structural Clone Generator for CI Testing.

Extracts the structural matrix that caused a PDF failure — geometry,
layout, fonts — then generates a synthetic clone with placeholder
content. Original user data is never preserved or saved.

Usage:
    python synthetic_generator.py          # generates a sample synthetic PDF
    python synthetic_generator.py --help   # show CLI options
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import struct
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field, asdict
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from reportlab.lib.pagesizes import letter, A4, legal
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.colors import Color
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# ---------------------------------------------------------------------------
# Structural Matrix
# ---------------------------------------------------------------------------

@dataclass
class StructuralMatrix:
    """Geometry-only description of a PDF's layout.

    Every field captures spatial and stylistic properties. No original
    text content is ever stored here — only bounding boxes and metrics
    that define *where* things are, not *what* they say.
    """

    page_count: int
    page_size: Tuple[float, float]  # (width, height) in PDF points
    text_blocks: List[Dict]         # [{x, y, w, h, font_size, font_name, color}]
    tables: List[Dict]              # [{rows, cols, cell_bboxes}]
    vectors: List[Dict]             # [{type, bbox, stroke_color}]
    images: List[Dict]              # [{bbox, width, height}]
    clusters: List[Dict]            # [{x, y, w, h, role, font_size}]
    failure_type: str               # "collision"|"overflow"|"corruption"|"timeout"
    failure_details: str            # human-readable description

    def to_dict(self) -> Dict:
        """Serialise to a plain dictionary (JSON-safe)."""
        d = asdict(self)
        d["page_size"] = list(d["page_size"])
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> StructuralMatrix:
        """Reconstruct from a plain dictionary."""
        data = dict(data)
        data["page_size"] = tuple(data["page_size"])
        return cls(**data)

    @property
    def page_width(self) -> float:
        return self.page_size[0]

    @property
    def page_height(self) -> float:
        return self.page_size[1]


# ---------------------------------------------------------------------------
# Structure Extractor
# ---------------------------------------------------------------------------

class StructureExtractor:
    """Extract the structural matrix from a PDF *without* preserving content.

    This runs geometric/layout extraction phases but captures only
    coordinates, dimensions, font metrics, and colour information.
    All text strings are discarded.
    """

    # Mapping of PyMuPDF font names to generic families
    _FONT_FAMILY_MAP: Dict[str, str] = {
        "helv": "Helvetica",
        "HeBo": "Helvetica-Bold",
        "TiRo": "Times-Roman",
        "TiBo": "Times-Bold",
        "Cour": "Courier",
        "CoBo": "Courier-Bold",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_from_pdf(self, pdf_path: str) -> StructuralMatrix:
        """Run PyMuPDF extraction, capturing structure only.

        For each page:
        1. Text block bounding boxes (not the text itself)
        2. Table structure (rows, cols, cell positions)
        3. Vector paths (lines, rectangles, curves)
        4. Image bounding boxes
        5. Page dimensions
        """
        if not HAS_PYMUPDF:
            raise RuntimeError(
                "PyMuPDF (fitz) is required for PDF extraction. "
                "Install with: pip install PyMuPDF"
            )

        doc = fitz.open(pdf_path)
        all_text_blocks: List[Dict] = []
        all_tables: List[Dict] = []
        all_vectors: List[Dict] = []
        all_images: List[Dict] = []
        page_size = (0.0, 0.0)

        for page in doc:
            if page.number == 0:
                rect = page.rect
                page_size = (round(rect.width, 2), round(rect.height, 2))

            # --- text blocks (geometry only) ---
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE).get("blocks", [])
            for block in blocks:
                if block.get("type") == 0:  # text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            bbox = span.get("bbox", (0, 0, 0, 0))
                            font_name_raw = span.get("font", "")
                            font_name = self._FONT_FAMILY_MAP.get(
                                font_name_raw, font_name_raw.split("-")[0]
                            )
                            color_int = span.get("color", 0)
                            r = ((color_int >> 16) & 0xFF) / 255.0
                            g = ((color_int >> 8) & 0xFF) / 255.0
                            b = (color_int & 0xFF) / 255.0
                            all_text_blocks.append({
                                "x": round(bbox[0], 2),
                                "y": round(bbox[1], 2),
                                "w": round(bbox[2] - bbox[0], 2),
                                "h": round(bbox[3] - bbox[1], 2),
                                "font_size": round(span.get("size", 12), 2),
                                "font_name": font_name,
                                "color": [round(r, 3), round(g, 3), round(b, 3)],
                            })

                elif block.get("type") == 1:  # image block
                    bbox = block.get("bbox", (0, 0, 0, 0))
                    all_images.append({
                        "bbox": list(bbox),
                        "width": round(bbox[2] - bbox[0], 2),
                        "height": round(bbox[3] - bbox[1], 2),
                    })

            # --- vectors ---
            paths = page.get_drawings()
            for path in paths:
                items = path.get("items", [])
                stroke = path.get("color")
                stroke_rgb = None
                if stroke is not None:
                    if isinstance(stroke, (list, tuple)):
                        stroke_rgb = [round(c, 3) for c in stroke[:3]]
                    else:
                        stroke_rgb = [round(stroke, 3), round(stroke, 3), round(stroke, 3)]

                rect = path.get("rect")
                bbox = list(rect) if rect else [0, 0, 0, 0]

                for item in items:
                    vtype = item[0] if item else "unknown"
                    all_vectors.append({
                        "type": vtype,
                        "bbox": bbox,
                        "stroke_color": stroke_rgb,
                    })

            # --- tables (heuristic via grid detection) ---
            detected_tables = self._detect_tables(page)
            all_tables.extend(detected_tables)

        doc.close()

        return StructuralMatrix(
            page_count=len(doc) if HAS_PYMUPDF else 0,
            page_size=page_size,
            text_blocks=all_text_blocks,
            tables=all_tables,
            vectors=all_vectors,
            images=all_images,
            clusters=[],
            failure_type="unknown",
            failure_details="Extracted from PDF file.",
        )

    def extract_from_error(
        self,
        error_log: str,
        cluster_data: Optional[List[Dict]] = None,
    ) -> StructuralMatrix:
        """Reconstruct structure from error logs and cluster data.

        When the PDF itself is unavailable, parse the error log
        and cluster dictionaries to reconstruct the geometry
        that caused the failure.
        """
        failure_type = self._classify_failure(error_log)
        page_count = 1
        page_size = (612.0, 792.0)  # US Letter default

        # Try to pull page size from log
        size_match = re.search(
            r"page[_\s]*(?:size|dimensions?)[:\s]+(\d+\.?\d*)\s*[x×,]\s*(\d+\.?\d*)",
            error_log,
            re.IGNORECASE,
        )
        if size_match:
            page_size = (float(size_match.group(1)), float(size_match.group(2)))

        page_match = re.search(r"page[_\s]*(?:count|num|number)[:\s]+(\d+)", error_log, re.IGNORECASE)
        if page_match:
            page_count = int(page_match.group(1))

        text_blocks: List[Dict] = []
        tables: List[Dict] = []
        vectors: List[Dict] = []
        images: List[Dict] = []

        # Parse block-level info from structured logs
        block_matches = re.findall(
            r"block[:\s]+.*?bbox[:\s]+\[?(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\]?",
            error_log,
            re.IGNORECASE,
        )
        for m in block_matches:
            x, y, x2, y2 = float(m[0]), float(m[1]), float(m[2]), float(m[3])
            text_blocks.append({
                "x": x, "y": y,
                "w": round(x2 - x, 2), "h": round(y2 - y, 2),
                "font_size": 12.0,
                "font_name": "Helvetica",
                "color": [0.0, 0.0, 0.0],
            })

        clusters = cluster_data or []
        if clusters:
            for cl in clusters:
                text_blocks.append({
                    "x": cl.get("x", 0),
                    "y": cl.get("y", 0),
                    "w": cl.get("w", 100),
                    "h": cl.get("h", 20),
                    "font_size": cl.get("font_size", 12),
                    "font_name": "Helvetica",
                    "color": [0.0, 0.0, 0.0],
                })

        return StructuralMatrix(
            page_count=page_count,
            page_size=page_size,
            text_blocks=text_blocks,
            tables=tables,
            vectors=vectors,
            images=images,
            clusters=clusters,
            failure_type=failure_type,
            failure_details=error_log.strip()[:500],
        )

    def extract_from_clusters(
        self,
        clusters: List[Dict],
        page_height: float,
        page_width: float,
    ) -> StructuralMatrix:
        """Build a structural matrix from cluster data alone.

        Clusters contain x, y, width, height, font_size — enough
        to reconstruct the geometric layout.
        """
        text_blocks: List[Dict] = []
        for cl in clusters:
            text_blocks.append({
                "x": cl.get("x", 0),
                "y": cl.get("y", 0),
                "w": cl.get("w", 100),
                "h": cl.get("h", 20),
                "font_size": cl.get("font_size", 12),
                "font_name": cl.get("font_name", "Helvetica"),
                "color": cl.get("color", [0.0, 0.0, 0.0]),
            })

        return StructuralMatrix(
            page_count=1,
            page_size=(page_width, page_height),
            text_blocks=text_blocks,
            tables=[],
            vectors=[],
            images=[],
            clusters=clusters,
            failure_type="unknown",
            failure_details="Reconstructed from cluster data.",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_failure(error_log: str) -> str:
        lower = error_log.lower()
        if "collision" in lower or "overlap" in lower:
            return "collision"
        if "overflow" in lower or "out of range" in lower or "exceeds" in lower:
            return "overflow"
        if "corrupt" in lower or "invalid" in lower or "malformed" in lower:
            return "corruption"
        if "timeout" in lower or "timed out" in lower:
            return "timeout"
        return "unknown"

    @staticmethod
    def _detect_tables(page) -> List[Dict]:
        """Heuristic table detection via horizontal/vertical line density."""
        if not HAS_PYMUPDF:
            return []

        drawings = page.get_drawings()
        if not drawings:
            return []

        rect = page.rect
        h_lines: List[float] = []
        v_lines: List[float] = []

        for path in drawings:
            for item in path.get("items", []):
                if item[0] == "l":  # line
                    p1, p2 = item[1], item[2]
                    if abs(p1.y - p2.y) < 1.0:  # horizontal
                        h_lines.append(round((p1.y + p2.y) / 2, 1))
                    elif abs(p1.x - p2.x) < 1.0:  # vertical
                        v_lines.append(round((p1.x + p2.x) / 2, 1))

        if len(h_lines) < 3 or len(v_lines) < 3:
            return []

        h_lines = sorted(set(h_lines))
        v_lines = sorted(set(v_lines))

        rows = len(h_lines) - 1
        cols = len(v_lines) - 1

        if rows < 1 or cols < 1:
            return []

        cell_bboxes = []
        for ri in range(len(h_lines) - 1):
            for ci in range(len(v_lines) - 1):
                cell_bboxes.append([
                    v_lines[ci], h_lines[ri],
                    v_lines[ci + 1], h_lines[ri + 1],
                ])

        return [{
            "rows": rows,
            "cols": cols,
            "cell_bboxes": cell_bboxes,
        }]


# ---------------------------------------------------------------------------
# Synthetic PDF Generator
# ---------------------------------------------------------------------------

class SyntheticPDFGenerator:
    """Generate a synthetic PDF that mimics the structural properties
    of a failing document, but contains only safe placeholder content.

    Uses reportlab if available, otherwise constructs a minimal PDF
    from raw bytes.
    """

    LOREM_WORDS = [
        "Lorem", "ipsum", "dolor", "sit", "amet", "consectetur",
        "adipiscing", "elit", "sed", "do", "eiusmod", "tempor",
        "incididunt", "ut", "labore", "et", "dolore", "magna",
        "aliqua", "Ut", "enim", "ad", "minim", "veniam",
        "quis", "nostrud", "exercitation", "ullamco", "laboris",
        "nisi", "aliquip", "ex", "ea", "commodo", "consequat",
        "Duis", "aute", "irure", "in", "reprehenderit", "voluptate",
        "velit", "esse", "cillum", "fugiat", "nulla", "pariatur",
        "Excepteur", "sint", "occaecat", "cupidatat", "non",
        "proident", "sunt", "culpa", "qui", "officia", "deserunt",
        "mollit", "anim", "id", "est", "laborum",
    ]

    # --- public API ---

    def generate(self, matrix: StructuralMatrix, output_path: str) -> str:
        """Generate a synthetic PDF from a structural matrix.

        Returns the output path.
        """
        output_path = str(output_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        if HAS_REPORTLAB:
            self._generate_reportlab(matrix, output_path)
        else:
            raw = self._build_minimal_pdf(matrix)
            with open(output_path, "wb") as f:
                f.write(raw)

        return output_path

    # --- internal: reportlab path ---

    def _generate_reportlab(self, matrix: StructuralMatrix, output_path: str) -> None:
        c = rl_canvas.Canvas(output_path, pagesize=matrix.page_size)

        for page_idx in range(matrix.page_count):
            if page_idx > 0:
                c.showPage()

            # draw vectors first (background layer)
            for vec in matrix.vectors:
                self._draw_vector(c, vec)

            # draw images as gray rectangles
            for img in matrix.images:
                bbox = img.get("bbox", [0, 0, 100, 100])
                c.setFillColorRGB(0.8, 0.8, 0.8)
                c.setStrokeColorRGB(0.6, 0.6, 0.6)
                c.rect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1], fill=1, stroke=1)

            # draw tables
            for tbl in matrix.tables:
                self._draw_table(c, tbl)

            # draw text blocks with Lorem Ipsum
            for block in matrix.text_blocks:
                self._draw_text_block(c, block)

        c.save()

    def _draw_text_block(self, c, block: Dict) -> None:
        x = block["x"]
        y_bottom = block["y"]
        w = block["w"]
        h = block["h"]
        font_size = block.get("font_size", 12)
        font_name = self._safe_reportlab_font(block.get("font_name", "Helvetica"))
        color = block.get("color", [0, 0, 0])

        c.setFillColorRGB(*color)

        # reportlab uses bottom-left origin; text block y is top-left
        y_top = y_bottom + h

        words = self._generate_lorem_block(w, h, font_size).split()
        line_height = font_size * 1.3
        max_chars_per_line = max(1, int(w / (font_size * 0.5)))

        lines = []
        current_line: List[str] = []
        current_len = 0
        for word in words:
            if current_len + len(word) + 1 > max_chars_per_line and current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_len = len(word)
            else:
                current_line.append(word)
                current_len += len(word) + 1
        if current_line:
            lines.append(" ".join(current_line))

        current_y = y_top - font_size
        for line in lines:
            if current_y < y_bottom:
                break
            c.setFont(font_name, font_size)
            c.drawString(x, current_y, line)
            current_y -= line_height

    def _draw_table(self, c, tbl: Dict) -> None:
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.5)
        c.setFillColorRGB(0.95, 0.95, 0.95)

        for bbox in tbl.get("cell_bboxes", []):
            x1, y1, x2, y2 = bbox
            c.rect(x1, y1, x2 - x1, y2 - y1, fill=0, stroke=1)

            # fill cell with tiny placeholder
            c.setFont("Helvetica", 6)
            c.setFillColorRGB(0.3, 0.3, 0.3)
            c.drawString(x1 + 2, y1 + 2, "X")
            c.setFillColorRGB(0.95, 0.95, 0.95)

    def _draw_vector(self, c, vec: Dict) -> None:
        stroke = vec.get("stroke_color")
        if stroke:
            c.setStrokeColorRGB(*stroke)
        else:
            c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.5)

        bbox = vec.get("bbox", [0, 0, 0, 0])
        vtype = vec.get("type", "re")

        if vtype == "re":
            c.rect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1], fill=0, stroke=1)
        elif vtype == "l":
            c.line(bbox[0], bbox[1], bbox[2], bbox[3])
        elif vtype == "c":
            # approximate curve with rectangle
            c.rect(bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1], fill=0, stroke=1)

    @staticmethod
    def _safe_reportlab_font(name: str) -> str:
        valid = {
            "Helvetica", "Helvetica-Bold", "Helvetica-Oblique",
            "Times-Roman", "Times-Bold", "Times-Italic",
            "Courier", "Courier-Bold", "Courier-Oblique",
        }
        if name in valid:
            return name
        base = name.split("-")[0].split("_")[0]
        mapping = {
            "Helvetica": "Helvetica",
            "Times": "Times-Roman",
            "Courier": "Courier",
            "Arial": "Helvetica",
            "Georgia": "Times-Roman",
            "CourierNew": "Courier",
        }
        return mapping.get(base, "Helvetica")

    # --- Lorem Ipsum generator ---

    def _generate_lorem_block(self, width: float, height: float, font_size: float) -> str:
        """Generate Lorem Ipsum text that approximately fits the given dimensions."""
        avg_char_width = font_size * 0.5
        max_chars_per_line = max(1, int(width / avg_char_width))
        line_height = font_size * 1.3
        max_lines = max(1, int(height / line_height))
        total_chars = max_chars_per_line * max_lines

        words: List[str] = []
        char_count = 0
        idx = 0
        while char_count < total_chars:
            word = self.LOREM_WORDS[idx % len(self.LOREM_WORDS)]
            words.append(word)
            char_count += len(word) + 1
            idx += 1

        return " ".join(words)

    # --- Minimal PDF builder (no reportlab) ---

    def _build_minimal_pdf(self, matrix: StructuralMatrix) -> bytes:
        """Build a minimal valid PDF from page specifications.

        Fallback when reportlab is unavailable.  Constructs raw PDF
        bytes with text objects at the specified positions.
        """
        buf = BytesIO()
        offsets: List[int] = []

        def _w(s: str) -> None:
            buf.write(s.encode("latin-1"))

        def _obj(obj_id: int, content: str) -> None:
            offsets.append(buf.tell())
            _w(f"{obj_id} 0 obj\n{content}\nendobj\n")

        # --- catalog & pages ---
        _obj(1, "<< /Type /Catalog /Pages 2 0 R >>")
        _obj(2, f"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

        pw, ph = matrix.page_size
        _obj(3, f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {pw:.2f} {ph:.2f}] "
             f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")

        # --- build content stream ---
        stream_lines: List[str] = []

        # draw vectors
        for vec in matrix.vectors:
            stroke = vec.get("stroke_color", [0, 0, 0])
            r, g, b = (stroke[0], stroke[1], stroke[2]) if stroke and len(stroke) >= 3 else (0, 0, 0)
            bbox = vec.get("bbox", [0, 0, 0, 0])
            stream_lines.append(f"{r:.3f} {g:.3f} {b:.3f} RG")
            stream_lines.append(f"{bbox[0]:.2f} {bbox[1]:.2f} {bbox[2]:.2f} {bbox[3]:.2f} re S")

        # draw images as gray boxes
        for img in matrix.images:
            bbox = img.get("bbox", [0, 0, 100, 100])
            stream_lines.append("0.8 0.8 0.8 rg")
            stream_lines.append(f"{bbox[0]:.2f} {bbox[1]:.2f} {bbox[2]-bbox[0]:.2f} {bbox[3]-bbox[1]:.2f} re f")

        # draw text blocks
        for block in matrix.text_blocks:
            x = block["x"]
            y_top = block["y"] + block["h"]
            font_size = block.get("font_size", 12)
            color = block.get("color", [0, 0, 0])

            lorem = self._generate_lorem_block(block["w"], block["h"], font_size)
            line_height = font_size * 1.3
            max_chars = max(1, int(block["w"] / (font_size * 0.5)))

            words = lorem.split()
            lines: List[str] = []
            cur_line: List[str] = []
            cur_len = 0
            for word in words:
                if cur_len + len(word) + 1 > max_chars and cur_line:
                    lines.append(" ".join(cur_line))
                    cur_line = [word]
                    cur_len = len(word)
                else:
                    cur_line.append(word)
                    cur_len += len(word) + 1
            if cur_line:
                lines.append(" ".join(cur_line))

            stream_lines.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg")
            stream_lines.append(f"BT /F1 {font_size:.1f} Tf")

            cy = y_top - font_size
            for line in lines:
                escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                stream_lines.append(f"{x:.2f} {cy:.2f} Td ({escaped}) Tj 0 0 Td")
                cy -= line_height

            stream_lines.append("ET")

        stream_content = "\n".join(stream_lines)
        _obj(4, f"<< /Length {len(stream_content)} >>\nstream\n{stream_content}\nendstream")

        # --- font ---
        _obj(5, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

        # --- xref & trailer ---
        xref_start = buf.tell()
        _w("xref\n")
        _w(f"0 {len(offsets) + 1}\n")
        _w("0000000000 65535 f \n")
        for off in offsets:
            _w(f"{off:010d} 00000 n \n")

        _w("trailer\n")
        _w(f"<< /Size {len(offsets) + 1} /Root 1 0 R >>\n")
        _w("startxref\n")
        _w(f"{xref_start}\n")
        _w("%%EOF\n")

        return buf.getvalue()


# ---------------------------------------------------------------------------
# Privacy-safe CI promotion
# ---------------------------------------------------------------------------

async def safe_promote_to_ci(
    feedback_entry: Any,
    output_dir: str = "curriculum",
) -> str:
    """Privacy-safe promotion to CI suite.

    1. Extract structural matrix from the failing PDF/cluster data
    2. Generate a synthetic clone (all text -> Lorem Ipsum)
    3. Save the synthetic PDF to *output_dir* with prefix ``synth_``
    4. Never save the original user data
    5. Return the path to the synthetic PDF

    Parameters
    ----------
    feedback_entry:
        An object (dict or dataclass) with attributes such as:
        - ``pdf_path``: path to the failing PDF (may be ``None``)
        - ``error_log``: error text from the CI run
        - ``cluster_data``: list of cluster dicts (optional)
        - ``failure_type``: string classification
        - ``failure_details``: human-readable description
    output_dir:
        Directory to write the synthetic PDF into.
    """
    extractor = StructureExtractor()
    generator = SyntheticPDFGenerator()

    pdf_path = getattr(feedback_entry, "pdf_path", None) or (
        feedback_entry.get("pdf_path") if isinstance(feedback_entry, dict) else None
    )
    error_log = getattr(feedback_entry, "error_log", "") or (
        feedback_entry.get("error_log", "") if isinstance(feedback_entry, dict) else ""
    )
    cluster_data = getattr(feedback_entry, "cluster_data", None) or (
        feedback_entry.get("cluster_data") if isinstance(feedback_entry, dict) else None
    )
    failure_type = getattr(feedback_entry, "failure_type", "unknown") or (
        feedback_entry.get("failure_type", "unknown") if isinstance(feedback_entry, dict) else "unknown"
    )
    failure_details = getattr(feedback_entry, "failure_details", "") or (
        feedback_entry.get("failure_details", "") if isinstance(feedback_entry, dict) else ""
    )

    # Step 1: extract structural matrix
    if pdf_path and os.path.isfile(pdf_path):
        matrix = extractor.extract_from_pdf(pdf_path)
    elif cluster_data:
        ph = 792.0
        pw = 612.0
        size_match = re.search(r"(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)", error_log)
        if size_match:
            pw, ph = float(size_match.group(1)), float(size_match.group(2))
        matrix = extractor.extract_from_clusters(cluster_data, ph, pw)
    elif error_log:
        matrix = extractor.extract_from_error(error_log, cluster_data)
    else:
        raise ValueError(
            "Cannot extract structural matrix: no pdf_path, cluster_data, "
            "or error_log provided."
        )

    matrix.failure_type = failure_type
    matrix.failure_details = failure_details

    # Step 2: generate synthetic clone
    os.makedirs(output_dir, exist_ok=True)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", failure_type)[:30]
    import time
    filename = f"synth_{safe_id}_{int(time.time() * 1000)}.pdf"
    output_path = os.path.join(output_dir, filename)

    generator.generate(matrix, output_path)

    # Also save the structural matrix as JSON for reference
    json_path = output_path.replace(".pdf", "_matrix.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(matrix.to_dict(), jf, indent=2)

    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_demo_matrix() -> StructuralMatrix:
    """Create a demo structural matrix that exercises all features."""
    return StructuralMatrix(
        page_count=2,
        page_size=(612.0, 792.0),
        text_blocks=[
            {
                "x": 72.0, "y": 680.0, "w": 468.0, "h": 36.0,
                "font_size": 24.0, "font_name": "Helvetica-Bold",
                "color": [0.1, 0.1, 0.1],
            },
            {
                "x": 72.0, "y": 640.0, "w": 468.0, "h": 20.0,
                "font_size": 14.0, "font_name": "Helvetica",
                "color": [0.2, 0.2, 0.2],
            },
            {
                "x": 72.0, "y": 560.0, "w": 220.0, "h": 72.0,
                "font_size": 11.0, "font_name": "Times-Roman",
                "color": [0.0, 0.0, 0.0],
            },
            {
                "x": 302.0, "y": 560.0, "w": 238.0, "h": 72.0,
                "font_size": 11.0, "font_name": "Times-Roman",
                "color": [0.0, 0.0, 0.0],
            },
            {
                "x": 72.0, "y": 300.0, "w": 468.0, "h": 240.0,
                "font_size": 10.0, "font_name": "Courier",
                "color": [0.0, 0.3, 0.0],
            },
        ],
        tables=[
            {
                "rows": 4,
                "cols": 3,
                "cell_bboxes": [
                    [72, 480, 228, 510],
                    [228, 480, 384, 510],
                    [384, 480, 540, 510],
                    [72, 450, 228, 480],
                    [228, 450, 384, 480],
                    [384, 450, 540, 480],
                    [72, 420, 228, 450],
                    [228, 420, 384, 450],
                    [384, 420, 540, 450],
                    [72, 390, 228, 420],
                    [228, 390, 384, 420],
                    [384, 390, 540, 420],
                ],
            }
        ],
        vectors=[
            {"type": "l", "bbox": [72, 520, 540, 520], "stroke_color": [0, 0, 0]},
            {"type": "l", "bbox": [72, 385, 540, 385], "stroke_color": [0, 0, 0]},
            {"type": "re", "bbox": [72, 100, 540, 260], "stroke_color": [0.5, 0.5, 0.5]},
        ],
        images=[
            {"bbox": [72, 100, 220, 260], "width": 148, "height": 160},
            {"bbox": [230, 100, 540, 260], "width": 310, "height": 160},
        ],
        clusters=[
            {"x": 72, "y": 680, "w": 468, "h": 36, "role": "heading", "font_size": 24},
            {"x": 72, "y": 640, "w": 468, "h": 20, "role": "subheading", "font_size": 14},
            {"x": 72, "y": 560, "w": 220, "h": 72, "role": "paragraph", "font_size": 11},
        ],
        failure_type="collision",
        failure_details="Text blocks overlap at coordinates (72, 558)-(292, 632) and (72, 640)-(540, 660)",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic structural clones of failing PDFs for CI testing."
    )
    parser.add_argument(
        "--output", "-o",
        default="synthetic_sample.pdf",
        help="Output path for the synthetic PDF (default: synthetic_sample.pdf)",
    )
    parser.add_argument(
        "--from-json", "-j",
        help="Path to a StructuralMatrix JSON file to regenerate from.",
    )
    parser.add_argument(
        "--from-error", "-e",
        help="Path to an error log file to reconstruct from.",
    )
    parser.add_argument(
        "--clusters", "-c",
        help="Path to a JSON file containing cluster data.",
    )
    parser.add_argument(
        "--failure-type", "-t",
        default="collision",
        choices=["collision", "overflow", "corruption", "timeout", "unknown"],
        help="Failure type classification.",
    )
    args = parser.parse_args()

    extractor = StructureExtractor()
    generator = SyntheticPDFGenerator()

    if args.from_json:
        with open(args.from_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        matrix = StructuralMatrix.from_dict(data)
    elif args.from_error:
        with open(args.from_error, "r", encoding="utf-8") as f:
            error_log = f.read()
        clusters = None
        if args.clusters:
            with open(args.clusters, "r", encoding="utf-8") as f:
                clusters = json.load(f)
        matrix = extractor.extract_from_error(error_log, clusters)
        matrix.failure_type = args.failure_type
    else:
        matrix = _build_demo_matrix()

    output = generator.generate(matrix, args.output)
    print(f"Synthetic PDF generated: {output}")
    print(f"  Pages: {matrix.page_count}")
    print(f"  Size: {matrix.page_size[0]}x{matrix.page_size[1]} pts")
    print(f"  Text blocks: {len(matrix.text_blocks)}")
    print(f"  Tables: {len(matrix.tables)}")
    print(f"  Vectors: {len(matrix.vectors)}")
    print(f"  Images: {len(matrix.images)}")
    print(f"  Failure: {matrix.failure_type}")

    # Also save the matrix as JSON alongside the PDF
    json_path = os.path.splitext(output)[0] + "_matrix.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(matrix.to_dict(), f, indent=2)
    print(f"  Matrix JSON: {json_path}")


if __name__ == "__main__":
    main()
