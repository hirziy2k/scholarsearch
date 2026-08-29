"""Font metric emulation and fallback for PDF-to-PPTX conversion.

Handles the case where a PDF uses a font (e.g. HelveticaNeue-Light) that the
end-user's machine lacks. PowerPoint silently substitutes a different font
(e.g. Arial), whose glyph widths differ, breaking carefully calculated text
bounding boxes. This module detects font availability, selects the best
fallback, and recalculates widths so layout survives the substitution.
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Built-in font metrics (values normalised to em-square, source: PDF spec
# and measurement of standard PostScript metrics).
# Keys are lowercase canonical font names.
# ---------------------------------------------------------------------------

FONT_METRICS: Dict[str, Dict[str, float]] = {
    "helvetica":       {"ascent": 0.718, "descent": -0.207, "avg_width": 0.537, "space_width": 0.278},
    "helvetica-bold":  {"ascent": 0.718, "descent": -0.207, "avg_width": 0.583, "space_width": 0.278},
    "arial":           {"ascent": 0.718, "descent": -0.207, "avg_width": 0.537, "space_width": 0.278},
    "times-roman":     {"ascent": 0.683, "descent": -0.217, "avg_width": 0.452, "space_width": 0.250},
    "times-new-roman": {"ascent": 0.683, "descent": -0.217, "avg_width": 0.452, "space_width": 0.250},
    "courier":         {"ascent": 0.629, "descent": -0.371, "avg_width": 0.600, "space_width": 0.600},
    "courier-new":     {"ascent": 0.629, "descent": -0.371, "avg_width": 0.600, "space_width": 0.600},
    "calibri":         {"ascent": 0.750, "descent": -0.250, "avg_width": 0.500, "space_width": 0.270},
    "georgia":         {"ascent": 0.693, "descent": -0.207, "avg_width": 0.481, "space_width": 0.250},
    "verdana":         {"ascent": 0.773, "descent": -0.227, "avg_width": 0.537, "space_width": 0.290},
}

# Fonts that ship with every Windows / macOS / Linux install and are
# "safe" PPTX targets (PowerPoint will never silently substitute them).
_SYSTEM_SAFE: Set[str] = {
    "arial",
    "times new roman",
    "courier new",
    "calibri",
    "georgia",
    "verdana",
    "times",
}

# Canonical fallback map: prefix pattern -> replacement family name
_FALLBACK_MAP: List[Tuple[str, str]] = [
    ("helvetica", "arial"),
    ("times",     "times new roman"),
    ("courier",   "courier new"),
    ("futura",    "century gothic"),
    ("garamond",  "cambria"),
    ("calibri",   "calibri"),
    ("georgia",   "georgia"),
    ("verdana",   "verdana"),
]

_DEFAULT_FALLBACK = "arial"


# ---------------------------------------------------------------------------
# Font detection
# ---------------------------------------------------------------------------

class FontDetector:
    """Detect which fonts are available on the host system."""

    WINDOWS_FONT_DIR = "C:/Windows/Fonts"
    MACOS_FONT_DIR = "/Library/Fonts"
    LINUX_FONT_DIR = "/usr/share/fonts"

    def __init__(self) -> None:
        self._available: Optional[Set[str]] = None
        self._xml_names: Optional[Dict[str, str]] = None  # filename -> family

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _normalize(name: str) -> str:
        """Lower-case, strip whitespace, collapse spaces."""
        return re.sub(r"\s+", " ", name.strip().lower())

    def _platform_font_dirs(self) -> List[Path]:
        """Return candidate font directories for the current platform."""
        dirs: List[Path] = []
        if sys.platform == "win32":
            win = os.environ.get("WINDIR", "C:\\Windows")
            dirs.append(Path(win) / "Fonts")
        elif sys.platform == "darwin":
            dirs.extend([Path("/Library/Fonts"), Path.home() / "Library" / "Fonts"])
        else:
            dirs.extend([
                Path("/usr/share/fonts"),
                Path.home() / ".local" / "share" / "fonts",
            ])
        return [d for d in dirs if d.is_dir()]

    def _read_ttc_family(self, ttc_path: Path) -> Set[str]:
        """Best-effort parse of a TrueType Collection (.ttc) to extract
        family names from the name table.  Falls back to filename-based
        guessing on parse failure."""
        families: Set[str] = set()
        try:
            tree = ET.parse(ttc_path)  # nosec – XML is benign here
            for elem in tree.iter():
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag in ("familyName", "FontFamily"):
                    if elem.text:
                        families.add(self._normalize(elem.text))
        except Exception:
            pass
        if not families:
            families.add(self._normalize(ttc_path.stem))
        return families

    def _read_otf_family(self, otf_path: Path) -> Set[str]:
        """Best-effort parse of an OpenType/TrueType font XML metadata."""
        families: Set[str] = set()
        try:
            tree = ET.parse(otf_path)  # nosec
            for elem in tree.iter():
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag in ("familyName", "FontFamily"):
                    if elem.text:
                        families.add(self._normalize(elem.text))
        except Exception:
            pass
        if not families:
            families.add(self._normalize(otf_path.stem))
        return families

    def _scan_font_dirs(self) -> Set[str]:
        """Scan system font directories and return lowercase family names."""
        families: Set[str] = set()
        extensions = {".ttf", ".otf", ".ttc", ".fnt", ".fon"}
        for d in self._platform_font_dirs():
            for entry in d.rglob("*"):
                if entry.is_file() and entry.suffix.lower() in extensions:
                    stem = self._normalize(entry.stem)
                    families.add(stem)
                    if entry.suffix.lower() == ".ttc":
                        families |= self._read_ttc_family(entry)
                    elif entry.suffix.lower() in (".otf",):
                        families |= self._read_otf_family(entry)
        return families

    # -- public API ----------------------------------------------------------

    def get_available_fonts(self) -> Set[str]:
        """Return lowercase font family names available on this system.

        Results are cached after the first (potentially expensive) scan.
        """
        if self._available is None:
            self._available = self._scan_font_dirs()
        return self._available

    def is_font_available(self, font_name: str) -> bool:
        """Check if *font_name* (or a close variant) exists on this system."""
        normalized = self._normalize(font_name)
        available = self.get_available_fonts()

        # Exact match
        if normalized in available:
            return True

        # Check with common separators collapsed (e.g. "Helvetica Neue" vs
        # "HelveticaNeue")
        compact = normalized.replace(" ", "")
        if compact in {f.replace(" ", "") for f in available}:
            return True

        # Check if any available font starts with the query (handles
        # weight/suffix variants like "arialbold" for "arial")
        for af in available:
            af_compact = af.replace(" ", "")
            if af_compact.startswith(compact) or compact.startswith(af_compact):
                return True
        return False

    def find_fallback(self, font_name: str) -> str:
        """Find the best cross-platform fallback for a missing font.

        Returns the replacement font family name (title-cased for display,
        but metric lookups should use the lowercase canonical form).
        """
        normalized = self._normalize(font_name)

        # Direct match against the fallback map
        for prefix, replacement in _FALLBACK_MAP:
            if normalized.startswith(prefix):
                return replacement

        # If nothing matched, return default
        return _DEFAULT_FALLBACK


# ---------------------------------------------------------------------------
# Font metric emulator
# ---------------------------------------------------------------------------

class FontMetricEmulator:
    """Recalculate text bounding boxes when font substitution occurs."""

    def __init__(self, font_detector: FontDetector) -> None:
        self.detector = font_detector
        self._metrics_cache: Dict[str, Dict[str, float]] = {}

    def _get_metrics(self, font_name: str) -> Dict[str, float]:
        """Return metrics for *font_name*, checking cache first."""
        key = self.detector._normalize(font_name)
        if key in self._metrics_cache:
            return self._metrics_cache[key]

        metrics = FONT_METRICS.get(key)
        if metrics is None:
            # Fallback: derive rough metrics from the fallback font
            fallback = self.detector.find_fallback(font_name)
            metrics = FONT_METRICS.get(fallback, FONT_METRICS["arial"])
        self._metrics_cache[key] = metrics
        return metrics

    def recalculate_width(
        self,
        text: str,
        original_font: str,
        original_width: float,
        original_font_size: float,
    ) -> float:
        """Given text measured with *original_font* at *original_width*,
        calculate the width with the fallback font.

        Uses the ratio ``fallback_avg_width / original_avg_width * original_width``.
        """
        orig_metrics = self._get_metrics(original_font)
        fallback_name = self.detector.find_fallback(original_font)
        fb_metrics = self._get_metrics(fallback_name)

        orig_avg = orig_metrics["avg_width"] * original_font_size
        if orig_avg == 0:
            return original_width

        fb_avg = fb_metrics["avg_width"] * original_font_size
        ratio = fb_avg / orig_avg
        return original_width * ratio

    def recalculate_bbox(
        self,
        bbox: Tuple[float, float, float, float],
        original_font: str,
        original_font_size: float,
    ) -> Tuple[float, float, float, float]:
        """Recalculate a ``(left, top, width, height)`` bounding box for
        font substitution.

        Only the *width* component is adjusted; position and height are
        preserved (height is governed by font-size, not glyph metrics).
        """
        left, top, width, height = bbox
        new_width = self.recalculate_width(
            text="",  # not used for ratio calculation
            original_font=original_font,
            original_width=width,
            original_font_size=original_font_size,
        )
        return (left, top, new_width, height)

    def should_embed_or_substitute(self, font_name: str) -> str:
        """Decision: ``'embed'``, ``'substitute'``, or ``'safe'``.

        * ``'safe'``     – font ships on all major platforms.
        * ``'embed'``    – font is on *this* machine but non-standard; embed
                          it in the PPTX to guarantee fidelity.
        * ``'substitute'`` – font is missing; a metric-matched fallback will
                            be used.
        """
        normalized = self.detector._normalize(font_name)

        if normalized in _SYSTEM_SAFE:
            return "safe"

        if self.detector.is_font_available(font_name):
            return "embed"

        return "substitute"


# ---------------------------------------------------------------------------
# Integration helper
# ---------------------------------------------------------------------------

def apply_font_fallback(
    clusters: List[dict],
    font_detector: FontDetector,
    emulator: FontMetricEmulator,
) -> List[dict]:
    """Process a list of text *clusters* and apply font fallback.

    Each cluster is a dict with at least these keys:
        - ``font_name``  : str  – original PDF font name
        - ``width``      : float – measured width in PDF units
        - ``font_size``  : float – font size (points)

    For each cluster the function:
    1. Checks if the font is available on the system.
    2. If not, selects the best fallback font.
    3. Recalculates the width using font-metrics ratio.
    4. Updates the cluster dict and adds a ``font_fallback_applied`` flag.

    Returns the modified list (mutated in place).
    """
    for cluster in clusters:
        font_name = cluster.get("font_name", "")
        original_width = cluster.get("width", 0.0)
        font_size = cluster.get("font_size", 12.0)

        if not font_name:
            cluster["font_fallback_applied"] = False
            continue

        status = emulator.should_embed_or_substitute(font_name)

        if status == "safe":
            cluster["font_fallback_applied"] = False
            cluster["fallback_font"] = font_name
            continue

        if status == "embed":
            cluster["font_fallback_applied"] = False
            cluster["fallback_font"] = font_name
            cluster["embed_requested"] = True
            continue

        # status == "substitute"
        fallback = font_detector.find_fallback(font_name)
        new_width = emulator.recalculate_width(
            text="",
            original_font=font_name,
            original_width=original_width,
            original_font_size=font_size,
        )
        cluster["font_name"] = fallback
        cluster["width"] = new_width
        cluster["font_fallback_applied"] = True
        cluster["original_font"] = font_name
        cluster["fallback_font"] = fallback

    return clusters


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------

def _demo() -> None:
    """Run detection, fallback, and recalculation as a quick smoke test."""
    print("=" * 60)
    print("Font Emulator – standalone test")
    print("=" * 60)

    detector = FontDetector()
    emulator = FontMetricEmulator(detector)

    # 1. Font detection
    available = detector.get_available_fonts()
    print(f"\n[1] Scanned {len(available)} font entries on this system.")

    test_fonts = [
        "HelveticaNeue-Light",
        "Helvetica",
        "Arial",
        "Times New Roman",
        "Courier New",
        "Calibri",
        "Futura",
        "Garamond",
        "SomeUnknownFont",
    ]

    print("\n[2] Availability check:")
    for name in test_fonts:
        avail = detector.is_font_available(name)
        print(f"    {name:30s} -> {'available' if avail else 'MISSING'}")

    # 2. Fallback selection
    print("\n[3] Fallback mapping:")
    for name in test_fonts:
        fb = detector.find_fallback(name)
        print(f"    {name:30s} -> {fb}")

    # 3. Width recalculation
    print("\n[4] Width recalculation (example):")
    original_font = "HelveticaNeue-Light"
    original_width = 100.0
    font_size = 12.0
    new_width = emulator.recalculate_width(
        text="Hello World",
        original_font=original_font,
        original_width=original_width,
        original_font_size=font_size,
    )
    print(f"    Original: {original_font} @ {original_width:.2f}pt wide")
    print(f"    Fallback: {detector.find_fallback(original_font)} @ {new_width:.2f}pt wide")
    print(f"    Delta   : {new_width - original_width:+.2f}pt")

    # 4. Bounding-box recalculation
    bbox = (72.0, 100.0, 200.0, 14.0)
    new_bbox = emulator.recalculate_bbox(bbox, original_font, font_size)
    print(f"\n[5] BBox recalculation:")
    print(f"    Original : {bbox}")
    print(f"    Adjusted : {new_bbox}")

    # 5. Embed / substitute decision
    print("\n[6] Embed-or-substitute decisions:")
    for name in test_fonts:
        decision = emulator.should_embed_or_substitute(name)
        print(f"    {name:30s} -> {decision}")

    # 6. Cluster integration
    print("\n[7] Cluster integration test:")
    clusters = [
        {"font_name": "HelveticaNeue-Light", "width": 120.0, "font_size": 11.0},
        {"font_name": "Arial",               "width": 120.0, "font_size": 11.0},
        {"font_name": "Futura-Medium",       "width": 105.0, "font_size": 10.0},
        {"font_name": "TimesNewRoman",        "width": 90.0,  "font_size": 12.0},
        {"font_name": "",                     "width": 0.0,   "font_size": 10.0},
    ]
    result = apply_font_fallback(clusters, detector, emulator)
    for i, c in enumerate(result):
        applied = c.get("font_fallback_applied", False)
        fb = c.get("fallback_font", c.get("font_name", "?"))
        w = c.get("width", 0.0)
        print(f"    cluster[{i}]: font={c.get('font_name'):20s}  "
              f"width={w:8.2f}  fallback_applied={applied}  "
              f"fallback_font={fb}")

    print("\n" + "=" * 60)
    print("All tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
