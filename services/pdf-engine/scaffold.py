#!/usr/bin/env python3
"""scaffold.py — deterministic candidate chunking (pre-neural boundaries).

The 1.5B SLM cannot slice dense admin text (measured: confabulated neighbors,
fragment values). So it never slices: this stdlib regex pipeline chunks the
source into bounded candidate entities FIRST; Qwen only classifies, formats,
and confirms against the schema. Blind surgeon -> rigid classifier.

Chunkers: amounts (RM/$/decimal), dates (numeric + Malay/English months +
ordinals), IDs (digit-bearing uppercase codes, accounts), noun phrases
(capitalized runs with Malay connectors: dan/bin/binti/de/di/ke/&).
Each chunk carries its character span for downstream bbox localization.
Stdlib only.
"""

import re
from typing import Any, Dict, List

MALAY_MONTHS = ("jan|feb|mac|apr|mei|jun|jul|ogos|sep|okt|nov|dis")
EN_MONTHS = ("january|february|march|april|may|june|july|august|september|"
             "october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec")

AMOUNT_RE = re.compile(
    r"(?:RM|MYR|\$|USD)?\s?\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\b\d+\.\d{2}\b")
DATE_RE = re.compile(
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MALAY_MONTHS}|{EN_MONTHS})\s+\d{{2,4}}\b"
    rf"|\b\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}\b"
    rf"|\b(?:{EN_MONTHS}|{MALAY_MONTHS})\s+\d{{4}}\b", re.I)
ID_RE = re.compile(
    r"\b[A-Z0-9]+(?:[-/][A-Z0-9]+)+\b|\b(?=[A-Z0-9]*\d)[A-Z]{2,}[0-9][A-Z0-9-]*\b"
    r"|\b\d{6,}\b")
CONNECTORS = {"dan", "bin", "binti", "de", "di", "ke", "dalam", "dari", "&", "the", "of", "and", "for"}
NOUN_RUN_RE = re.compile(
    r"\b[A-Z][a-zA-Z']*(?:(?:\s+(?:[A-Z][a-zA-Z']*|dan|bin|binti|de|di|ke|dalam|dari|the|of|and|for|&))+)\b")


def _spans(pattern: re.Pattern, text: str, ftype: str) -> List[Dict[str, Any]]:
    out = []
    for m in pattern.finditer(text):
        v = m.group(0).strip(" .,;:")
        if len(v) >= 2:
            out.append({"text": v, "type": ftype, "span": (m.start(), m.end())})
    return out


def chunk(text: str) -> List[Dict[str, Any]]:
    """Bounded candidates in source order. Overlapping claims resolved by
    priority: ID > amount > date > noun phrase (codes beat currency)."""
    cands = (_spans(ID_RE, text, "account_id")
             + _spans(AMOUNT_RE, text, "amount")
             + _spans(DATE_RE, text, "date")
             + _spans(NOUN_RUN_RE, text, "proper_noun"))
    cands.sort(key=lambda c: (c["span"][0], -(c["span"][1] - c["span"][0])))
    kept, taken = [], []
    order = {"account_id": 0, "amount": 1, "date": 2, "proper_noun": 3}
    for c in sorted(cands, key=lambda c: (order[c["type"]], c["span"][0])):
        s, e = c["span"]
        if any(s < te and ts < e for ts, te in taken):
            continue
        taken.append((s, e))
        kept.append(c)
    return sorted(kept, key=lambda c: c["span"][0])
