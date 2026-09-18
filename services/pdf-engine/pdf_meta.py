#!/usr/bin/env python3
"""pdf_meta.py — PyMuPDF adapter for validation metadata (spans/fonts/words).

Builds the (spans, fonts, words) triple consumed by field_validation in
strict_meta mode, including the ToUnicode-poison probe: any bfchar/bfrange
entry mapping ASCII letter codes (A-Z, a-z) to space/null flags the font.

Requires PyMuPDF. field_validation.py itself stays stdlib-only.
"""

import re
from typing import Any, Dict, List, Tuple

_BFCHAR = re.compile(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")
_BFRANGE = re.compile(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")


def _code_is_letter(code: str) -> bool:
    try:
        v = int(code[-2:], 16)  # last byte of code
    except ValueError:
        return False
    return (0x41 <= v <= 0x5A) or (0x61 <= v <= 0x7A)


def _dst_is_blank(dst: str) -> bool:
    try:
        return int(dst, 16) in (0x20, 0x00, 0xA0)
    except ValueError:
        return False


def tounicode_poisoned(stream: bytes) -> bool:
    """True if the CMap maps any ASCII letter code to blank."""
    try:
        text = stream.decode("latin-1")
    except Exception:
        return False
    for src, dst in _BFCHAR.findall(text):
        if _code_is_letter(src) and _dst_is_blank(dst):
            return True
    for lo, hi, dst in _BFRANGE.findall(text):
        if _dst_is_blank(dst):
            try:
                if any(_code_is_letter(f"{v:02X}") for v in
                       range(int(lo[-2:], 16), min(int(hi[-2:], 16), int(lo[-2:], 16)) + 8)):
                    return True
            except ValueError:
                continue
    return False


def _tounicode_stream(doc: Any, xref: int) -> bytes:
    """Resolve /ToUnicode N 0 R from the font dict, then read stream xref N."""
    try:
        m = re.search(r"/ToUnicode\s+(\d+)\s+0\s+R", doc.xref_object(xref))
        if not m:
            return b""
        return doc.xref_stream(int(m.group(1))) or b""
    except Exception:
        return b""


def build_meta(page: Any, doc: Any) -> Tuple[List[Dict[str, Any]], Dict[Any, Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (spans, fonts, words) for one page."""
    fonts: Dict[Any, Dict[str, Any]] = {}
    name_to_xref: Dict[str, Any] = {}
    for f in page.get_fonts(full=True):
        xref, _ext, ftype, base, name, encoding = f[0], f[1], f[2], f[3], f[4], f[5]
        stream = _tounicode_stream(doc, xref) if xref else b""
        is_identity = (encoding == "Identity-H") or (ftype == "Type0")
        fonts[xref] = {
            "encoding": encoding or "",
            "is_identity_h": is_identity,
            "tounicode_ok": not is_identity or (bool(stream) and not tounicode_poisoned(stream)),
            "tounicode_letter_to_space": bool(stream) and tounicode_poisoned(stream),
        }
        # Bind by resource name AND basefont program identity: PyMuPDF span
        # dicts report the program family ('Helvetica') while get_fonts keys
        # the resource ('helv'). Both are the same font program — binding by
        # either is deterministic, not a trust decision.
        name_to_xref[name] = xref
        if base:
            name_to_xref.setdefault(base, xref)
            name_to_xref.setdefault(base.split("+")[-1], xref)  # subset prefix ABCDEF+Font
    spans: List[Dict[str, Any]] = []
    page_poison = any(v.get("tounicode_letter_to_space") for v in fonts.values())
    try:
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for sp in line.get("spans", []):
                    if sp.get("text", "").strip():
                        xref = name_to_xref.get(sp.get("font", ""))
                        if xref is None and len(fonts) == 1:
                            xref = next(iter(fonts))
                        spans.append({"size": round(sp.get("size", 0.0), 1),
                                      "color": sp.get("color", 0),
                                      "font_xref": xref,
                                      "font_traced": sp.get("font", "") in name_to_xref,
                                      "bbox": tuple(sp.get("bbox", (0, 0, 0, 0))),
                                      "page_poison": page_poison})
    except Exception:
        pass
    words: List[Dict[str, Any]] = []
    try:
        for w in page.get_text("words"):
            words.append({"x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3],
                          "text": w[4], "block": w[5], "line": w[6], "wno": w[7]})
    except Exception:
        pass
    return spans, fonts, words


def continuation_ink(page: Any, run_bbox: Tuple[float, float, float, float],
                     reach_pt: float, ink_ratio_floor: float = 0.02,
                     dpi: int = 150) -> bool:
    """Pixel continuation probe: is there ink immediately right of the run?

    Breaks the clip tautology (clip derived from untrusted run bbox) by
    inspecting the strip the model claims is empty. reach_pt comes from the
    native line's median word gap (bounded); ink above floor => the pixels
    contain more than the extraction -> truncated. Background-white assumed
    (bg-colored ink is rejected upstream). Stdlib + PyMuPDF + Pillow.
    """
    from PIL import Image
    import io
    x0, y0, x1, y1 = run_bbox
    clip = (x1, y0, x1 + reach_pt, y1)
    if clip[2] <= clip[0] or clip[3] <= clip[1]:
        return False
    pix = page.get_pixmap(clip=clip, dpi=dpi, colorspace="GRAY")
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    px = list(img.getdata())
    if not px:
        return False
    ink = sum(1 for v in px if v < 128)
    return (ink / len(px)) > ink_ratio_floor


def ocr_field(page: Any, bbox: Tuple[float, float, float, float],
              dpi: int = 300, pad_pt: float = 4.0) -> Tuple[str, List[Dict[str, Any]]]:
    """Isotope tracing: render ONLY the field bbox, OCR it, return (text, words).

    Bypasses a deceitful text layer entirely — verdicts downstream rest on
    pixels. Words carry PDF-coordinate rects rebuilt from image_to_data.
    Raises RuntimeError('OCR_UNAVAILABLE') when Tesseract is missing.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise RuntimeError("OCR_UNAVAILABLE") from e
    x0, y0, x1, y1 = bbox
    clip = (x0 - pad_pt, y0 - pad_pt, x1 + pad_pt, y1 + pad_pt)
    zoom = dpi / 72.0
    pix = page.get_pixmap(clip=clip, dpi=dpi, colorspace="GRAY")
    import io
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img, config="--psm 7")
    words: List[Dict[str, Any]] = []
    try:
        data = pytesseract.image_to_data(img, config="--psm 7", output_type=pytesseract.Output.DICT)
        n = len(data.get("text", []))
        for i in range(n):
            t = (data["text"][i] or "").strip()
            if not t:
                continue
            l, t_, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            words.append({"x0": clip[0] + l / zoom, "y0": clip[1] + t_ / zoom,
                          "x1": clip[0] + (l + w) / zoom, "y1": clip[1] + (t_ + h) / zoom,
                          "text": t, "block": 0, "line": data["line_num"][i], "wno": i})
    except Exception:
        pass
    return text.strip(), words
