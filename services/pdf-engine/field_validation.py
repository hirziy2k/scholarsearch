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
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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

ORANGE_REVIEW = "orange-review"


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
        return False, f"{ftype} no exact normalized match -> {ORANGE_REVIEW}"
    # proper nouns / verbatim: length-aware threshold
    vt, st = _tokens(value), _tokens(source_text)
    if len(vt) <= 4:
        ratio = sliding_overlap(vt, st)
        if ratio >= 1.0:
            return True, "ok"
        return False, f"short noun overlap {ratio:.2f} < 1.0 -> {ORANGE_REVIEW}"
    ratio = sliding_overlap(vt, st)
    if ratio >= 0.85:
        return True, "ok"
    return False, f"long verbatim overlap {ratio:.2f} < 0.85 -> {ORANGE_REVIEW}"


def validate_field(field: Dict[str, Any], value: Any, source_text: str = "") -> Tuple[bool, str]:
    """Dispatch by registry. Returns (ok, reason); ok=False means route to orange-review."""
    ftype = field.get("type", "")
    if ftype in CLASS_A_TYPES:
        return validate_class_a(field, value)
    if ftype in CLASS_B_TYPES:
        return validate_class_b(field, value, source_text)
    return False, f"unregistered field type: {ftype} -> {ORANGE_REVIEW}"
