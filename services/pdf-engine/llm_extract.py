#!/usr/bin/env python3
"""llm_extract.py — neural Class B frontend with inference-layer gating.

MEASURED LIMITATION (qwen2.5:1.5b, two framings): the model cannot perform
verbatim neighbor attestation — it echoes value-internal tokens (joint
schema) and confabulates neighbors (dedicated micro-task: before="Course",
after="Course" for a mid-text value). Self-proving boundaries are therefore
NOT enforced here; claiming otherwise would be fiction.

What IS enforced at this layer: verbatim existence. A proposed value absent
from the source is a hallucination and dies here. Neighbor tokens are still
requested (larger models may comply) and recorded, but only existence gates.
Fragment adjudication belongs to the spatial boundary gate downstream, which
reads true neighbors from word rects instead of model testimony.
"""

import json
import re
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

SYSTEM = (
    "You extract compliance fields from document text. Reply with EXACT JSON, "
    "no other text: {\"fields\": [{\"type\": <amount|account_id|proper_noun|date>, "
    "\"extracted_value\": \"...\", \"preceding_source_token\": \"...\", "
    "\"succeeding_source_token\": \"...\"}]}. Rules: values and neighbor tokens "
    "must be verbatim substrings of the source, copied character-for-character. "
    "preceding_source_token is the single token immediately before the value in "
    "the source (or \"\" if the value starts the text); succeeding_source_token "
    "is the single token immediately after (or \"\" if it ends the text). "
    "Never invent tokens. Extract at most 8 fields: financial amounts, account "
    "or alphanumeric IDs, organization/person names, ISO-like dates. "
    "EXAMPLE: source \"Total Amount $1,234.56 due\" with value \"$1,234.56\" "
    "requires preceding_source_token \"Amount\" and succeeding_source_token "
    "\"due\" — copy the exact adjacent words, never \"\". Empty string is "
    "allowed ONLY at true text boundaries."
)


def _ollama(prompt: str, model: str = "qwen2.5:1.5b", base_url: str = "http://localhost:11434",
            timeout: int = 180) -> str:
    body = json.dumps({"model": model, "prompt": SYSTEM + "\n\nSOURCE:\n" + prompt,
                       "stream": False,
                       "options": {"temperature": 0.0, "num_ctx": 4096,
                                   "num_predict": 256}}).encode()
    req = urllib.request.Request(base_url + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode()).get("response", "")


def _verify_triple(source: str, value: str, pre: str, suc: str) -> bool:
    """True iff value occurs ANYWHERE in source with the claimed verbatim
    neighbors (multi-occurrence values verify against any instance)."""
    if not value or len(value.strip()) < 2:
        return False
    slow = source.lower()
    vlow = value.lower()
    strip = lambda s: s.strip("\"'“”‘’.,;:()[]")
    start = 0
    while True:
        idx = slow.find(vlow, start)
        if idx < 0:
            return False
        before = source[:idx].rstrip()
        after = source[idx + len(value):].lstrip()
        pre_tok = before.split()[-1] if before.split() else ""
        suc_tok = after.split()[0] if after.split() else ""
        pre_ok = (pre == "" and pre_tok == "") or (pre and strip(pre_tok).lower() == strip(pre).lower())
        suc_ok = (suc == "" and suc_tok == "") or (suc and strip(suc_tok).lower() == strip(suc).lower())
        if pre_ok and suc_ok:
            return True
        start = idx + 1


def extract_page(source: str, model: str = "qwen2.5:1.5b",
                 max_chars: int = 2500) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Returns (verified_fields, dropped_fragments). Fragments die here."""
    raw = _ollama(source[:max_chars], model=model)
    try:
        start, end = raw.index("{"), raw.rindex("}") + 1
        fields = json.loads(raw[start:end]).get("fields", [])
    except Exception:
        return [], [{"reason": "unparseable", "raw": raw[:200]}]
    ok, dropped = [], []
    for f in fields:
        if not isinstance(f, dict) or not f.get("extracted_value"):
            dropped.append({"reason": "malformed", "field": f})
            continue
        value = str(f["extracted_value"])
        if len(value.strip()) < 2 or value.lower() not in source.lower():
            dropped.append({"reason": "hallucinated", "field": f})
            continue
        # Specificity floor: a lone digitless word ("Healing") is never a
        # compliance entity — it is a fragment by construction. Single-token
        # values must carry a digit (amounts, IDs, codes); multi-token spans
        # pass to the spatial boundary gate for completeness judgment.
        if len(value.split()) < 2 and not re.search(r"\d", value):
            dropped.append({"reason": "underspecified", "field": f})
            continue
        f["boundary_attested"] = _verify_triple(
            source, value, str(f.get("preceding_source_token", "")),
            str(f.get("succeeding_source_token", "")))
        ok.append(f)
    return ok, dropped
