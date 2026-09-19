#!/usr/bin/env python3
"""pdf_meta.py — PyMuPDF adapter for validation metadata (spans/fonts/words).

Builds the (spans, fonts, words) triple consumed by field_validation in
strict_meta mode, including the ToUnicode-poison probe: any bfchar/bfrange
entry mapping ASCII letter codes (A-Z, a-z) to space/null flags the font.

Requires PyMuPDF. field_validation.py itself stays stdlib-only.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

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


def find_columns(words: List[Dict[str, Any]], page_width: float, page_height: float,
                 min_gutter_pt: float = 18.0) -> List[Tuple[float, float]]:
    """Vertical column gutters from word-rect topology (layout-bounded probing).

    A gutter is an x-interval >= min_gutter_pt wide that stays empty across
    >=85% of sampled content-height rows. Returns sorted (x0, x1) column
    bands; single column when no gutter qualifies. Pure geometry, no text.
    """
    if not words or page_width <= 0:
        return [(0.0, float(page_width or 0))]
    edges = {0.0, float(page_width)}
    for w in words:
        edges.add(w["x0"])
        edges.add(w["x1"])
    xs = sorted(edges)
    y0 = min(w["y0"] for w in words)
    y1 = max(w["y1"] for w in words)
    rows = max(1, int((y1 - y0) // 4))
    gutters: List[Tuple[float, float]] = []
    for a, b in zip(xs, xs[1:]):
        if b - a < min_gutter_pt:
            continue
        mid = (a + b) / 2
        hits = sum(1 for r in range(rows + 1)
                   if any(w["x0"] <= mid <= w["x1"] and w["y0"] <= (y0 + r * 4) <= w["y1"]
                          for w in words))
        if hits / (rows + 1) < 0.15:
            gutters.append((a, b))
    cols: List[Tuple[float, float]] = []
    cur = 0.0
    for a, b in sorted(gutters):
        if a > cur:
            cols.append((cur, a))
        cur = max(cur, b)
    if cur < page_width:
        cols.append((cur, float(page_width)))
    return cols or [(0.0, float(page_width))]


def column_limit(columns: List[Tuple[float, float]],
                 run_bbox: Tuple[float, float, float, float]) -> Optional[float]:
    """Right edge of the run's column (by bbox center), or None if outside."""
    cx = (run_bbox[0] + run_bbox[2]) / 2
    for a, b in columns:
        if a <= cx <= b:
            return b
    return None


def probe_end(words: List[Dict[str, Any]], columns: List[Tuple[float, float]],
              run_bbox: Tuple[float, float, float, float], reach_pt: float) -> float:
    """Right edge of the claimed-empty gap: min(run + reach, next listed word
    start, column edge). Known content bounds the probe — only pixels the
    layer claims are empty get inspected, so dense neighbors never DoS."""
    x0, y0, x1, y1 = run_bbox
    lh = max(1.0, y1 - y0)
    end = x1 + reach_pt
    for w in words:
        if w["x0"] > x1 + 0.5 and abs((w["y1"] + w["y0"]) / 2 - (y1 + y0) / 2) < 3 * lh:
            end = min(end, w["x0"])
    lim = column_limit(columns, run_bbox)
    # Gutter clamp needs a REAL gutter: if the column edge sits on the run's
    # own edge (<1pt), the "gutter" is mere absence of listed words — exactly
    # what is suspect in poison cases — so the bound is ignored and the full
    # reach is probed. A genuine inter-column gutter stays clamped.
    if lim is not None and lim - x1 >= 1.0:
        end = min(end, lim)
    return max(x1, end)


def ink_mask(img, sat_thresh: int = 40, lum_thresh: int = 150) -> Any:
    """Artifact & chromatic filter -> binary ink mask (Pillow '1' image).

    Keeps achromatic dark pixels (black/dark-gray body text); drops chromatic
    ink (blue/red company chops, stamps) by saturation and salt-and-pepper
    scanner noise by 3x3 morphological opening (erosion then dilation), which
    erases isolated specks while preserving glyph strokes. Forbidden to probe
    raw pixels on scanned stock — all ink ratios derive from this mask.
    """
    from PIL import Image, ImageFilter
    rgb = img.convert("RGB")
    px = list(rgb.getdata())
    m = Image.new("1", rgb.size)
    md = m.load()
    W, H = rgb.size
    for i, (r, g, b) in enumerate(px):
        sat = max(r, g, b) - min(r, g, b)
        lum = (r + g + b) // 3
        md[i % W, i // W] = 255 if (sat < sat_thresh and lum < lum_thresh) else 0
    return m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))


def mask_ratio(mask: Any) -> float:
    dd = list(mask.getdata())
    return (sum(1 for v in dd if v) / len(dd)) if dd else 0.0


def background_stats(img: Any) -> Dict[str, float]:
    """Page background luminance mean/variance over non-ink, achromatic pixels.

    Establishes the paper noise floor (grain, shadow, JPEG artifacts) that a
    synthetic void will violate by its perfection.
    """
    rgb = img.convert("RGB")
    vals = []
    for r, g, b in rgb.getdata():
        if max(r, g, b) - min(r, g, b) < 40 and (r + g + b) // 3 > 150:
            vals.append((r + g + b) // 3)
    if not vals:
        return {"mean": 255.0, "var": 0.0, "n": 0}
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return {"mean": mean, "var": var, "n": len(vals)}


def void_check(page: Any, bbox: Tuple[float, float, float, float],
               page_bg: Optional[Dict[str, float]] = None, dpi: int = 150,
               var_floor: float = 0.5, white_floor: float = 250.0,
               void_fraction: float = 0.20,
                words: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, Dict[str, float]]:
    """Zero-variance anomaly: whiteout looks like paper but has no noise.

    Trigger — void ERASING a word: a connected void component that (a) reaches
    the word rect's interior central-third band, (b) covers >=400px^2 at 150dpi
    (bigger than any glyph counter at body sizes; smaller than any word
    erasure), and (c) touches >=2 rect edges (erasure spans; counters touch
    none). Inter-word gaps fail (a); counters fail (b)+(c); line padding fails
    (a). Measured path here: fringe-touch fired 500x on production gaps,
    fraction bars proved uncalibratable, 50%-blanket missed a true positive
    by 1%. No words = no verdict.
    """
    from PIL import Image
    import io
    pix = page.get_pixmap(clip=bbox, dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    W, H = img.size
    if W == 0 or H == 0 or not words:
        return False, {"void_cells": 0, "void_on_claim": False}
    vals = list(img.getdata())
    side = max(8, H // 2)
    nx = max(1, W // side)
    zoom = dpi / 72.0
    bx0, by0 = bbox[0], bbox[1]
    grid: Dict[tuple, bool] = {}
    for cx in range(nx):
        for cy in range(2):
            x0, y0 = cx * side, cy * (H // 2)
            cell = [vals[(y0 + dy) * W + (x0 + dx)]
                    for dy in range(min(H // 2, H - y0))
                    for dx in range(min(side, W - x0))]
            if not cell:
                continue
            mean = sum(cell) / len(cell)
            var = sum((v - mean) ** 2 for v in cell) / len(cell)
            grid[(cx, cy)] = bool(var < var_floor and mean >= white_floor)
    seen = set()
    for start, is_void in grid.items():
        if not is_void or start in seen:
            continue
        stack, comp = [start], []
        while stack:
            node = stack.pop()
            if node in seen or not grid.get(node, False):
                continue
            seen.add(node)
            comp.append(node)
            x, y = node
            stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
        xs = [c[0] for c in comp]
        ys = [c[1] for c in comp]
        c = (bx0 + min(xs) * side / zoom, by0 + min(ys) * (H // 2) / zoom,
             bx0 + (max(xs) + 1) * side / zoom,
             by0 + (max(ys) + 1) * (H // 2) / zoom)
        area_px = len(comp) * side * (H // 2)
        if area_px < 400:
            continue
        for w in words:
            ix0, ix1 = w["x0"] + (w["x1"] - w["x0"]) / 3, w["x0"] + 2 * (w["x1"] - w["x0"]) / 3
            if not (c[2] > ix0 and c[0] < ix1 and c[3] > w["y0"] and c[1] < w["y1"]):
                continue
            edges = sum((c[0] <= w["x0"] + 1, c[2] >= w["x1"] - 1,
                         c[1] <= w["y0"] + 1, c[3] >= w["y1"] - 1))
            if edges >= 2:
                return True, {"void_cells": len(comp), "void_on_claim": True}
    return False, {"void_cells": 0, "void_on_claim": False}


def continuation_ink(page: Any, run_bbox: Tuple[float, float, float, float],
                     reach_pt: float, ink_ratio_floor: float = 0.02,
                     dpi: int = 300, x_limit: Optional[float] = None,
                     x_end: Optional[float] = None) -> bool:
    """Probe at 300dpi: glyph strokes (~7px) survive the 3x3 opening while
    single-pixel dust dies — at 150dpi thin strokes erode away entirely,
    blinding the probe (measured regression). Strips are tiny; cost is trivial."""
    """Pixel continuation probe: is there BODY-TEXT ink right of the run?

    The strip passes through ink_mask() first — chromatic chop/stamp ink and
    salt-and-pepper scanner noise never reach the ratio. reach_pt comes from
    the native line's median word gap (bounded); filtered ink above floor =>
    the pixels contain more than the extraction -> truncated.
    """
    from PIL import Image
    import io
    x0, y0, x1, y1 = run_bbox
    if x_end is not None:
        x1 = min(x1 + reach_pt, x_end)
        clip = (run_bbox[2], y0, x1, y1)
    else:
        if x_limit is not None:
            # Gutter bound: ink in a structurally separate column is a neighbor
            # field, not a continuation — the probe stops at the column edge.
            x1 = min(x1, x_limit)
        clip = (x1, y0, x1 + reach_pt, y1)
        if x_limit is not None:
            clip = (clip[0], clip[1], min(clip[2], x_limit), clip[3])
    if clip[2] <= clip[0] or clip[3] <= clip[1]:
        return False
    pix = page.get_pixmap(clip=clip, dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return mask_ratio(ink_mask(img)) > ink_ratio_floor


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


def is_scanned(page: Any, words: List[Dict[str, Any]]) -> bool:
    """Heuristic: image-backed page with (near-)no native text layer."""
    try:
        return len(words) < 5 and len(page.get_images()) > 0
    except Exception:
        return False


def ssim_gray(a_vals: List[int], b_vals: List[int]) -> float:
    """Whole-patch simplified SSIM over two equal-length gray sequences."""
    n = len(a_vals)
    if n == 0 or len(b_vals) != n:
        return 0.0
    ma = sum(a_vals) / n
    mb = sum(b_vals) / n
    va = sum((v - ma) ** 2 for v in a_vals) / n
    vb = sum((v - mb) ** 2 for v in b_vals) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a_vals, b_vals)) / n
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    den = (ma * ma + mb * mb + c1) * (va + vb + c2)
    if den == 0:
        return 1.0 if va == 0 and vb == 0 else 0.0
    return ((2 * ma * mb + c1) * (2 * cov + c2)) / den


def check_alignment(page: Any, words: List[Dict[str, Any]], dpi: int = 150,
                    drift_px: float = 5.0, ssim_floor: float = 0.75
                    ) -> Tuple[bool, Dict[str, Any]]:
    """Spatial Confidence Anchor: prove layer↔raster registration with two
    independent engines before trusting any bbox on this page.

    Native digital pages skip (fast path). Scanned pages: longest alphanumeric
    word becomes the anchor; Tesseract re-discovers it on a full-page render;
    verdict requires center drift <= 5px AND clip SSIM >= floor. Failure means
    the coordinate map is unproven -> whole page degrades to focal-raster
    fallback. Raises RuntimeError('OCR_UNAVAILABLE') without Tesseract.
    """
    if not is_scanned(page, words):
        return True, {"mode": "native", "drift_px": 0.0, "ssim": 1.0}
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise RuntimeError("OCR_UNAVAILABLE") from e
    import io
    cands = [w for w in words if re.fullmatch(r"[A-Za-z0-9]{4,}", w["text"] or "")]
    anchor = max(cands, key=lambda w: len(w["text"])) if cands else None
    if anchor is None:
        return False, {"mode": "no-anchor", "drift_px": None, "ssim": 0.0}
    zoom = dpi / 72.0
    full = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(full.tobytes("png")))
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    best, best_hit = None, -1
    at = anchor["text"].lower()
    for i, t in enumerate(data.get("text", [])):
        t = (t or "").strip().lower()
        if not t:
            continue
        hit = len(set(t) & set(at)) / max(len(set(t) | set(at)), 1)
        if hit > best_hit:
            best_hit, best = hit, i
    if best is None or best_hit < 0.5:
        return False, {"mode": "anchor-lost", "drift_px": None, "ssim": 0.0}
    ox = (data["left"][best] + data["width"][best] / 2) / zoom
    oy = (data["top"][best] + data["height"][best] / 2) / zoom
    ax = (anchor["x0"] + anchor["x1"]) / 2
    ay = (anchor["y0"] + anchor["y1"]) / 2
    drift = (((ox - ax) * zoom) ** 2 + ((oy - ay) * zoom) ** 2) ** 0.5
    clip = (anchor["x0"], anchor["y0"], anchor["x1"], anchor["y1"])
    aimg = Image.open(io.BytesIO(
        page.get_pixmap(clip=clip, dpi=dpi).tobytes("png"))).convert("L")
    if mask_ratio(ink_mask(aimg)) < 0.005:
        # Invisible OCR layer (white text on raster): SSIM is meaningless on
        # blank pixels, so alignment rests on OCR token fidelity + drift.
        aligned = best_hit >= 0.9 and drift <= drift_px
        return aligned, {"mode": "invisible-layer", "anchor": anchor["text"],
                         "drift_px": round(drift, 2), "ocr_hit": round(best_hit, 3)}
    ox0, oy0 = data["left"][best] / zoom, data["top"][best] / zoom
    oclip = (ox0, oy0, ox0 + data["width"][best] / zoom, oy0 + data["height"][best] / zoom)
    oimg = Image.open(io.BytesIO(
        page.get_pixmap(clip=oclip, dpi=dpi).tobytes("png"))).convert("L").resize(aimg.size)
    s = ssim_gray(list(aimg.getdata()), list(oimg.getdata()))
    detail = {"mode": "anchored", "anchor": anchor["text"],
              "drift_px": round(drift, 2), "ssim": round(s, 3)}
    return (drift <= drift_px and s >= ssim_floor), detail
