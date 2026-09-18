#!/usr/bin/env python3
"""field_validation.py — Class A/B compliance field registry (V1 Data Guillotine).

Class A (structural): dates, booleans, enums, OCR-reconstructed paragraphs,
    summaries. Strict JSON-schema typing + enum enforcement. Zero source-text matching.
Class B (verbatim): financial amounts, account numbers, proper nouns,
    alphanumeric IDs. Token-overlap against sliding source window + deterministic
    normalization. Failures route to orange-review (human HITL), never auto-accept.

Thresholds (signed off, length-aware — no universal 0.85):
  amounts & alphanumeric IDs : 1.0 exact after normalization (no fuzzy numbers)
  short proper nouns (<=4 tokens): 1.0 exact, case-normalized
  long verbatim (>4 tokens)  : token-overlap >= 0.85 sliding window

Stdlib only.
"""

import re
import unicodedata
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# First line of defense: pre-prompt injection redaction (LLM-input copy only;
# original preserved in provenance store).
# ---------------------------------------------------------------------------

INJECTION_PATTERNS = [
    re.compile(r"\b(ignore|disregard)\s+(all\s+)?(previous|prior|above)\s+instructions?\b", re.I),
    re.compile(r"\bsystem\s*prompt\b", re.I),
    re.compile(r"\badmin\s*password\b", re.I),
    re.compile(r"\breveal\s+(credentials|keys|password|secrets?)\b", re.I),
    re.compile(r"\bexfiltrate\b", re.I),
    re.compile(r"\bsend\s+to\s+https?://\S+", re.I),
]

REDACTED = "[REDACTED-INSTRUCTION]"


def redact_for_prompt(text: str) -> Tuple[str, int]:
    """Return (redacted_copy, hit_count). Never mutates the stored original."""
    hits = 0
    out = text
    for pat in INJECTION_PATTERNS:
        out, n = pat.subn(REDACTED, out)
        hits += n
    return out, hits


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CLASS_A_TYPES = {"date", "boolean", "enum", "ocr_paragraph", "summary"}
CLASS_B_TYPES = {"amount", "account_id", "alphanumeric_id", "proper_noun", "verbatim"}

ORANGE_REVIEW = "orange-review"  # legacy label; zero-review pipeline uses REJECT:* codes

# Zero-review reject codes (fail-closed, machine-readable, no human queue).
REJECT_METADATA_MISSING = "REJECT:METADATA_MISSING"
REJECT_TEXT_ATTR = "REJECT:SUSPECT_TEXT_ATTR"
REJECT_FONT_ENCODING = "REJECT:SUSPECT_FONT_ENCODING"
REJECT_TRUNCATION = "REJECT:TRUNCATION_BOUNDARY"
REJECT_HOSTILE_UNICODE = "REJECT:HOSTILE_UNICODE"
REJECT_OCR_UNAVAILABLE = "REJECT:OCR_UNAVAILABLE"

MIN_FONT_PT = 6.0
STANDARD_ENCODINGS = {"WinAnsiEncoding", "MacRomanEncoding", "StandardEncoding"}
WORD_RE = re.compile(r"[A-Za-z0-9]+")
ADJACENCY_LINE_FACTOR = 1.5  # neighbor within 1.5x line height counts as adjacent


def quarantine_value(value: str) -> Tuple[bool, str]:
    """Homoglyph & PUA quarantine — the value grades itself, not the CMap.

    NFKC-normalize; any length/character shift or Private-Use (Co) codepoint
    means the string is structurally hostile (homoglyph swap, PUA smuggling,
    ligature games). Class B only. Fail-closed.
    """
    if not isinstance(value, str):
        return False, f"{REJECT_HOSTILE_UNICODE}: non-string"
    norm = unicodedata.normalize("NFKC", value)
    if norm != value:
        return False, f"{REJECT_HOSTILE_UNICODE}: NFKC shift {value!r} -> {norm!r}"
    for ch in value:
        if unicodedata.category(ch) == "Co":
            return False, f"{REJECT_HOSTILE_UNICODE}: private-use U+{ord(ch):04X}"
        # Script mixing: NFKC-stable homoglyphs (Cyrillic/Greek lookalikes).
        # Class B expects Latin letterforms — any non-Latin letter is hostile.
        if unicodedata.category(ch).startswith("L"):
            script = unicodedata.name(ch, "").split(" ")[0]
            if script not in ("LATIN",):
                return False, f"{REJECT_HOSTILE_UNICODE}: non-Latin {script} U+{ord(ch):04X}"
    return True, "ok"


def _bbox_intersects(a: Tuple[float, float, float, float],
                     b: Tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def field_span_verdict(field_bbox: Optional[Tuple[float, float, float, float]],
                       spans: List[Dict[str, Any]],
                       fonts: Dict[Any, Dict[str, Any]],
                       background: int = 0xFFFFFF) -> Tuple[str, str]:
    """Localize the tripwire to the field's spatial bbox. Returns
    ('clean'|'fallback', reason). Non-intersecting spans are ignored entirely —
    a poisoned footer can never kill a clean entity (no page-level taint)."""
    hits = [sp for sp in spans
            if field_bbox is None or _bbox_intersects(field_bbox, sp.get("bbox", (0, 0, 0, 0)))]
    for sp in hits:
        if sp.get("size", MIN_FONT_PT) < MIN_FONT_PT:
            return "fallback", f"{REJECT_TEXT_ATTR}: size {sp.get('size')}pt"
        if sp.get("color", 0) == background and background == 0xFFFFFF:
            return "fallback", f"{REJECT_TEXT_ATTR}: background-colored ink"
        if not sp.get("font_traced", False):
            return "fallback", f"{REJECT_FONT_ENCODING}: untraceable font at field"
        finfo = fonts.get(sp.get("font_xref"), {})
        if finfo.get("tounicode_letter_to_space"):
            return "fallback", f"{REJECT_FONT_ENCODING}: ToUnicode letter->blank"
        if finfo.get("is_identity_h") and not finfo.get("tounicode_ok"):
            return "fallback", f"{REJECT_FONT_ENCODING}: unverified Identity-H"
        enc = finfo.get("encoding", "")
        if enc and enc not in STANDARD_ENCODINGS:
            return "fallback", f"{REJECT_FONT_ENCODING}: {enc}"
    return "clean", "ok"


def check_spatial_boundary(value: str, words: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Bidirectional boundary over reading-order word adjacency (no pixel ratios).

    Finds the value's token run in word order; if the immediately adjacent word
    (same block by word number, else nearest rect within line-height factor) is
    alphanumeric, the extraction is truncated -> fail-closed.
    """
    vt = _tokens(value)
    if not vt:
        return False, f"{REJECT_TRUNCATION}: empty value"
    seq = [w for w in words]
    n = len(vt)
    best = -1
    for i in range(len(seq) - n + 1):
        if [t for t in _tokens(" ".join(w["text"] for w in seq[i:i + n]))] == vt:
            best = i
            break
    if best < 0:
        # no contiguous run (fuzzy-accepted long text): boundary check n/a
        return True, "ok"
    run = seq[best:best + n]
    first, last = run[0], run[-1]
    neighbors: List[Dict[str, Any]] = []
    # Rule 1: same (block, line) word-number adjacency — catches same-line drops.
    same_line = [w for w in seq if w.get("block") == first.get("block")
                 and w.get("line") == first.get("line")]
    ordered = sorted(same_line, key=lambda w: w.get("wno", 0))
    idx = [i for i, w in enumerate(ordered)
           if (w["x0"], w["y0"]) == (first["x0"], first["y0"])]
    if idx:
        p = idx[0]
        if p > 0:
            neighbors.append(ordered[p - 1])
        last_idx = [i for i, w in enumerate(ordered)
                    if (w["x0"], w["y0"]) == (last["x0"], last["y0"])]
        if last_idx and last_idx[0] + 1 < len(ordered):
            neighbors.append(ordered[last_idx[0] + 1])
    # Rule 2: same visual line, split across blocks (column gutter split only).
    # Requires baseline gap < 0.5x line height AND small horizontal gap —
    # next-line words are NEVER neighbors (wrap handling belongs to extraction).
    lh = max(1.0, last["y1"] - last["y0"])
    for w in seq:
        if w in run or w.get("line") == last.get("line") and w.get("block") == last.get("block"):
            continue
        dy = abs((w["y1"] + w["y0"]) / 2 - (last["y1"] + last["y0"]) / 2)
        gap = w["x0"] - last["x1"]  # qualifier to the right of the run
        gap_left = first["x0"] - w["x1"]  # qualifier to the left
        if dy < 0.5 * lh and (0 <= gap < 3 * lh or 0 <= gap_left < 3 * lh):
            neighbors.append(w)
    for nb in neighbors:
        if WORD_RE.search(nb["text"]):
            return False, f"{REJECT_TRUNCATION}: adjacent token {nb['text']!r}"
    return True, "ok"


def _tokens(s: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9]+", s.lower())


def normalize_amount(s: str) -> str:
    """Strip currency symbols, commas, whitespace. Keeps digits, '.', '-'."""
    return re.sub(r"[^0-9.\-]", "", s)


def sliding_overlap(value_tokens: List[str], source_tokens: List[str]) -> float:
    """Max token-overlap of value against any contiguous source window of equal length."""
    n = len(value_tokens)
    if n == 0:
        return 1.0
    if len(source_tokens) < n:
        hit = sum(1 for t in value_tokens if t in set(source_tokens))
        return hit / n
    best = 0.0
    for i in range(len(source_tokens) - n + 1):
        window = set(source_tokens[i:i + n])
        hit = sum(1 for t in value_tokens if t in window)
        ratio = hit / n
        if ratio > best:
            best = ratio
            if best >= 1.0:
                break
    return best


def validate_class_a(field: Dict[str, Any], value: Any) -> Tuple[bool, str]:
    """Schema typing only. No source-text matching by design."""
    ftype = field["type"]
    if ftype == "date":
        if not isinstance(value, str):
            return False, "date must be string"
        try:
            datetime.fromisoformat(value)
            return True, "ok"
        except ValueError:
            return False, f"date not ISO-8601: {value!r}"
    if ftype == "boolean":
        return (True, "ok") if isinstance(value, bool) else (False, "boolean must be true/false")
    if ftype == "enum":
        allowed = field.get("allowed", [])
        return (True, "ok") if value in allowed else (False, f"enum {value!r} not in {allowed}")
    if ftype in ("ocr_paragraph", "summary"):
        if not isinstance(value, str) or not value.strip():
            return False, f"{ftype} must be non-empty string"
        if "max_len" in field and len(value) > field["max_len"]:
            return False, f"{ftype} exceeds max_len {field['max_len']}"
        return True, "ok"
    return False, f"unknown Class A type: {ftype}"


def validate_class_b(field: Dict[str, Any], value: Any, source_text: str) -> Tuple[bool, str]:
    """Verbatim fidelity. Amounts/IDs exact; short nouns exact; long text fuzzy 0.85."""
    ftype = field["type"]
    if not isinstance(value, str) or not value.strip():
        return False, f"{ftype} must be non-empty string"
    if ftype in ("amount", "account_id", "alphanumeric_id"):
        norm_val = normalize_amount(value)
        # exact match required somewhere in source (punctuation-insensitive)
        norm_src = normalize_amount(source_text)
        if norm_val and norm_val in norm_src:
            return True, "ok"
        return False, f"{ftype} no exact normalized match -> REJECT:EXACT_MISMATCH"
    # proper nouns / verbatim: length-aware threshold
    vt, st = _tokens(value), _tokens(source_text)
    if len(vt) <= 4:
        ratio = sliding_overlap(vt, st)
        if ratio >= 1.0:
            return True, "ok"
        return False, f"short noun overlap {ratio:.2f} < 1.0 -> REJECT:EXACT_MISMATCH"
    ratio = sliding_overlap(vt, st)
    if ratio >= 0.85:
        return True, "ok"
    return False, f"long verbatim overlap {ratio:.2f} < 0.85 -> REJECT:FUZZY_MISMATCH"


def _locate_run(value: str, words: List[Dict[str, Any]]) -> Optional[Tuple[float, float, float, float]]:
    """Union bbox of the value's contiguous word run, or None if no run."""
    vt = _tokens(value)
    n = len(vt)
    if not n or not words:
        return None
    for i in range(len(words) - n + 1):
        run_text = " ".join(w["text"] for w in words[i:i + n])
        if _tokens(run_text) == vt:
            run = words[i:i + n]
            return (min(w["x0"] for w in run), min(w["y0"] for w in run),
                    max(w["x1"] for w in run), max(w["y1"] for w in run))
    return None


def _locate_best_window(value: str, words: List[Dict[str, Any]]
                        ) -> Optional[Tuple[float, float, float, float]]:
    """Union bbox of the best-overlap sliding window (for fuzzy-accepted values
    with no exact run). Never returns None when words exist."""
    vt = _tokens(value)
    n = len(vt)
    if not n or not words:
        return None
    if len(words) <= n:
        run = words
    else:
        best_i, best_hit = 0, -1
        vset = set(vt)
        for i in range(len(words) - n + 1):
            hit = sum(1 for w in words[i:i + n] if w["text"].lower() in vset)
            if hit > best_hit:
                best_hit, best_i = hit, i
        run = words[best_i:best_i + n]
    return (min(w["x0"] for w in run), min(w["y0"] for w in run),
            max(w["x1"] for w in run), max(w["y1"] for w in run))


def _line_reach(words: List[Dict[str, Any]],
                run_bbox: Tuple[float, float, float, float]) -> float:
    """Bounded search radius: median same-band word gap, clamped to [0.5, 1.0]x height."""
    x0, y0, x1, y1 = run_bbox
    lh = max(1.0, y1 - y0)
    band = sorted([w for w in words
                   if abs((w["y1"] + w["y0"]) / 2 - (y1 + y0) / 2) < 0.5 * lh],
                  key=lambda w: w["x0"])
    gaps = [b["x0"] - a["x1"] for a, b in zip(band, band[1:]) if b["x0"] > a["x1"]]
    med = sorted(gaps)[len(gaps) // 2] if gaps else 0.5 * lh
    return max(0.5 * lh, min(med * 2.0, 1.0 * lh))


def _expand_to_line(bbox: Tuple[float, float, float, float],
                    words: List[Dict[str, Any]]) -> Tuple[float, float, float, float]:
    """Anti-tautology expansion: the OCR clip must include what the model may
    have dropped. Extends the run bbox to full line extents of co-linear words
    (same block+line as the run's vertical band), so clipped pixels contain
    any adjacent qualifier glyphs the extraction omitted."""
    x0, y0, x1, y1 = bbox
    lh = max(1.0, y1 - y0)
    line = [w for w in words if abs((w["y1"] + w["y0"]) / 2 - (y1 + y0) / 2) < 0.5 * lh]
    if line:
        x0 = min(x0, min(w["x0"] for w in line))
        x1 = max(x1, max(w["x1"] for w in line))
        y0 = min(y0, min(w["y0"] for w in line))
        y1 = max(y1, max(w["y1"] for w in line))
    return (x0, y0, x1, y1)


def validate_field(field: Dict[str, Any], value: Any, source_text: str = "",
                 spans: Optional[List[Dict[str, Any]]] = None,
                 fonts: Optional[Dict[Any, Dict[str, Any]]] = None,
                 words: Optional[List[Dict[str, Any]]] = None,
                 strict_meta: bool = False,
                 ocr_fn: Optional[Callable[[Tuple[float, float, float, float]],
                                           Tuple[str, List[Dict[str, Any]]]]] = None,
                 ink_fn: Optional[Callable[[Tuple[float, float, float, float], float], bool]] = None
                 ) -> Tuple[bool, str]:
    """Dispatch by registry. Class B order: quarantine -> match -> localize ->
    field tripwire -> (clean: boundary | tainted: ink-probe + OCR re-verdict).

    ocr_fn(bbox) -> (ocr_text, ocr_words) is the isotope tracer (pdf_meta.
    ocr_field in production, stub in tests). ink_fn(run_bbox, reach_pt) -> bool
    is the pixel continuation probe (pdf_meta.continuation_ink): ink past the
    run's right edge means the pixels hold more than the extraction, and no
    OCR clip derived from the run can be trusted to refute it. No ocr_fn +
    tainted field = REJECT:OCR_UNAVAILABLE. ok=False is always fail-closed.
    """
    ftype = field.get("type", "")
    if ftype in CLASS_A_TYPES:
        return validate_class_a(field, value)
    if ftype in CLASS_B_TYPES:
        if not isinstance(value, str):
            return False, f"{ftype} must be string"
        ok, reason = quarantine_value(value)
        if not ok:
            return False, reason
        meta = (spans is not None and fonts is not None and words is not None)
        if strict_meta and not meta:
            return False, REJECT_METADATA_MISSING
        ok, reason = validate_class_b(field, value, source_text)
        if not ok:
            return False, reason
        if not meta:
            return True, "ok"
        bbox = _locate_run(value, words) or _locate_best_window(value, words)
        if ftype in ("amount",):
            # amounts skip spatial boundary (numeric runs adjoin currency/units
            # on the same line by design); tripwire still applies below
            pass
        verdict, why = field_span_verdict(bbox, spans, fonts)
        if verdict == "clean":
            if ftype in ("proper_noun", "verbatim", "account_id", "alphanumeric_id"):
                return check_spatial_boundary(value, words)
            return True, "ok"
        # tainted field bbox -> pixels, not the lying layer. First the ink
        # probe on the NATIVE run bbox (unexpanded: the model claims nothing
        # follows the run, so any ink there refutes it without trusting OCR).
        run = _locate_run(value, words)
        if ink_fn is not None and run is not None:
            try:
                if ink_fn(run, _line_reach(words, run)):
                    return False, f"{REJECT_TRUNCATION}: pixel continuation past run"
            except Exception:
                pass
        if ocr_fn is None:
            return False, REJECT_OCR_UNAVAILABLE
        try:
            clip = _expand_to_line(bbox, words) if bbox else (0, 0, 0, 0)
            ocr_text, ocr_words = ocr_fn(clip)
        except Exception as e:
            return False, f"{REJECT_OCR_UNAVAILABLE}: {e}"
        ok, reason = quarantine_value(ocr_text)
        if not ok:
            return False, reason
        ok, reason = validate_class_b(field, value, ocr_text)
        if not ok:
            return False, reason + " [via OCR]"
        if ftype in ("proper_noun", "verbatim", "account_id", "alphanumeric_id"):
            ok, reason = check_spatial_boundary(value, ocr_words)
            return (ok, reason + " [via OCR]") if not ok else (True, "ok [via OCR]")
        return True, "ok [via OCR]"
    return False, f"unregistered field type: {ftype} -> {REJECT_METADATA_MISSING}"
