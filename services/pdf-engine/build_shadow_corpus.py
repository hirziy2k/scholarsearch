#!/usr/bin/env python3
"""build_shadow_corpus.py — Stratified Entropy Matrix gate for shadow runs.

A randomized production dump is structurally invalid: it over-fits floors to
dominant vendors. The corpus MUST meet exact quotas before one document is
processed. Active matrix: Operational-Reality-V1 (45% localized / 35% native
/ 10% decay / 10% mobscan); FLAT-20 is retained below for history only.

Usage: python build_shadow_corpus.py <pdf_dir[;pdf_dir2;...]> <out_manifest.json> [--need N]
       python build_shadow_corpus.py --verify <manifest.json>
       python build_shadow_corpus.py --mutate <manifest.json> <out_dir> [--rate R] [--seed S]
Exit 0 + manifest only when every quota is met; otherwise exit 1 listing the
shortfall (no partial runs — a short stratum silently biases every threshold).

Immutability: the manifest pins SHA-256 per document plus a corpus digest
(sorted per-doc hashes, hashed again). --verify rehashes and halts nonzero on
any drift, deletion, or substitution — tuning against a shifting foundation
is mathematical fiction, so a drifted corpus refuses to run.

Heuristics are v0, deterministic, and documented below. Requires PyMuPDF.
"""

import hashlib
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

STRATA = ["native", "clean_scan", "decay", "localized", "mobile"]
QUOTA = {"native": 0.2, "clean_scan": 0.2, "decay": 0.2, "localized": 0.2, "mobile": 0.2}

# Versioned matrix amendments. FLAT-20 was an academic hallucination: equal
# weight to phantom mobile captures dilutes the asymmetric penalty where the
# liability actually sits (digital + localized contracts). Operational-
# Reality-V1 encodes the measured liability surface; mobile/clean_scan merge
# into one defensive-perimeter bucket. History is preserved, never edited.
MATRICES = {
    "FLAT-20": {"native": 0.2, "clean_scan": 0.2, "decay": 0.2,
                "localized": 0.2, "mobile": 0.2},
    "Operational-Reality-V1": {"localized": 0.45, "native": 0.35,
                               "decay": 0.10, "mobscan": 0.10},
}
ACTIVE_MATRIX = "Operational-Reality-V1"


def phenomena(sig: Dict[str, Any], n_img: int, n_words: int) -> List[str]:
    """Independent phenomenon predicates (coverage sets, NOT a partition).

    A scanned chop-bearing circular IS both scan-grain stock and localized
    content — single-label assignment drained shared docs into whichever
    bucket was checked first and starved the rest (measured: mobscan pool
    collapsed to 5 while ~12% of the population exhibits capture phenomena).
    Buckets overlap by design; the manifest records every membership and the
    optimizer consumes per-field marginals, never bucket identity.
    """
    out = []
    if sig.get("non_latin", 0) > 0.02 or sig.get("chroma", 0) > 0.0005:
        out.append("localized")
    if n_img == 0 and n_words >= 20:
        out.append("native")
    if (sig.get("grime", 0) >= 0.05 or sig.get("specks", 0) >= 0.01
            or (n_img > 0 and n_words < 3)):
        out.append("decay")
    calm = (n_img > 0 and sig.get("grime", 9) < 0.05 and sig.get("specks", 9) < 0.01
            and n_words >= 3 and sig.get("warp", 9) <= 0.06)
    if sig.get("warp", 0) > 0.06 or calm:
        out.append("mobscan")
    return out


def _non_latin_ratio(text: str) -> float:
    letters = [c for c in text if unicodedata.category(c).startswith("L")]
    if not letters:
        return 0.0
    return sum(1 for c in letters
               if unicodedata.name(c, "").split(" ")[0] not in ("LATIN",)) / len(letters)


def _chromatic_ratio(page: Any, dpi: int = 50) -> float:
    import io
    from PIL import Image
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    px = list(img.getdata())
    chrom = sum(1 for r, g, b in px if max(r, g, b) - min(r, g, b) > 60)
    return chrom / len(px) if px else 0.0


def _bg_noise(page: Any, dpi: int = 50) -> float:
    import io
    from PIL import Image
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    vals = [v for v in img.getdata() if v > 150]
    if len(vals) < 100:
        return 0.0
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals) / len(vals)


def _warp(page: Any, dpi: int = 120) -> float:
    """Skew via monotonicity-gated edge march over RAW dark pixels.

    Deliberately no chromatic/opening filter here: re-rendered (rotated)
    glyphs wash out past the ink mask and vanish (measured 2e-05), blinding
    geometry. Random speck/chop steps are suppressed instead by the
    monotonicity gate (consistency^2): true tilt marches every band the same
    way, noise does not. Decay still exits first via grime/specks."""
    import io
    from PIL import Image
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    W, H = img.size
    dd = list(img.getdata())
    rows = [y for y in range(H) if any(dd[y * W + x] < 128 for x in range(W))]
    if len(rows) < 12:
        return 0.0
    # Adaptive bands across the CONTENT span (not the page): sparse pages
    # otherwise starve the band count and warp reads 0 by construction.
    # Edge march, not centroid wander: global rotation preserves per-band
    # centroids of symmetric blocks but marches the left ink edge across
    # bands. Slope of band-min-x vs band-y ≈ tan(skew), scale-free.
    y0, y1 = min(rows), max(rows)
    edges = []
    bands = 24
    for b in range(bands):
        lo = y0 + b * (y1 - y0 + 1) // bands
        hi = min(H - 1, y0 + (b + 1) * (y1 - y0 + 1) // bands)
        xs = [x for y in range(lo, hi + 1) for x in range(W) if dd[y * W + x] < 128]
        if xs:
            edges.append(min(xs) / W)
    if len(edges) < 6:
        return 0.0
    n = len(edges)
    mu = (n - 1) / 2
    me = sum(edges) / n
    var = sum((i - mu) ** 2 for i in range(n))
    if var == 0:
        return 0.0
    slope = sum((i - mu) * (e - me) for i, e in enumerate(edges)) / var
    # Monotonicity gate: true skew marches every band the same direction;
    # chop rects and glyph jitter step randomly. Consistency suppresses the
    # latter quadratically while preserving the former.
    diffs = [b - a for a, b in zip(edges, edges[1:])]
    if not diffs:
        return 0.0
    cons = max(sum(1 for v in diffs if v > 0), sum(1 for v in diffs if v < 0)) / len(diffs)
    return round(abs(slope) * n * cons * cons, 4)


def _specks(page: Any, dpi: int = 50) -> float:
    """Isolated-dot fraction: raw ink minus opened ink. Fax salt lives here."""
    import io
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from pdf_meta import ink_mask, mask_ratio
    from PIL import Image
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    lum = img.convert("L")
    px = list(lum.getdata())
    raw = sum(1 for v in px if v < 128) / len(px)
    return max(0.0, raw - mask_ratio(ink_mask(img)))


def _grime(page: Any, dpi: int = 50) -> float:
    """Fax-generation proxy: fraction of mid-tone pixels (neither paper white
    nor glyph black). Smudge, bleed-through, and copy grain live here; pure
    black specks do not move it, so salt-and-pepper needs _specks too."""
    import io
    from PIL import Image
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    px = list(img.getdata())
    mid = sum(1 for v in px if 80 <= v <= 210)
    return mid / len(px) if px else 0.0


def classify(pdf: Path) -> Dict[str, Any]:
    """First-page v0 heuristics. Order matters: localized/mobile override."""
    import fitz
    doc = fitz.open(_longpath(pdf))
    page = doc[0]
    words = page.get_text("words")
    text = page.get_text()
    n_img = len(page.get_images())
    signals = {
        "words": len(words),
        "images": n_img,
        "non_latin": round(_non_latin_ratio(text), 4),
        "chroma": round(_chromatic_ratio(page), 5),
        "bg_noise": round(_bg_noise(page), 2),
        "grime": round(_grime(page), 4),
        "specks": round(_specks(page), 5),
        "warp": round(_warp(page), 4),
    }
    if n_img == 0 and len(words) >= 20:
        # Digital ground truth first: pixel stats are pristine regardless of
        # content markings.
        stratum = "native"
    elif n_img == 0 and (signals["non_latin"] > 0.02 or signals["chroma"] > 0.0005):
        # Digital admin with color graphics / non-Latin letterheads.
        stratum = "localized"
    elif signals["warp"] > 0.06:
        # Capture-first: geometric warp is a property of the camera, not the
        # content — any warped doc is physical-capture stock.
        stratum = "mobile"
    elif signals["grime"] > 0.02 or signals["specks"] > 0.005 or (n_img > 0 and len(words) < 3):
        stratum = "decay"
    elif n_img > 0:
        # Image-backed and calm: the clean-scan perimeter (includes pristine
        # digital-with-logo, statistically harmless here).
        stratum = "clean_scan"
    elif signals["non_latin"] > 0.02 or signals["chroma"] > 0.0005:
        stratum = "localized"
    else:
        stratum = "native"
    return {"path": str(pdf), "stratum": stratum, "signals": signals}


def _longpath(p: Any) -> str:
    """Windows MAX_PATH bypass: extended-length prefix for deep nests."""
    s = str(p)
    if sys.platform == "win32" and len(s) > 240 and not s.startswith("\\\\?\\"):
        return "\\\\?\\" + str(Path(s).absolute())
    return s


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(_longpath(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


HOMOGLYPH_MAP = str.maketrans({"a": "а", "e": "е", "o": "о", "c": "с", "A": "А",
                                "E": "Е", "O": "О", "C": "С", "p": "р", "x": "х"})


def mutate_whiteout(doc: Any, seed: int = 0) -> Dict[str, Any]:
    """Cover a deterministic text word with an opaque white rect (Tipp-Ex)."""
    import random
    rng = random.Random(seed)
    words = [w for w in doc[0].get_text("words") if len((w[4] or "").strip()) >= 3]
    if not words:
        raise ValueError("mutate_whiteout: no words")
    w = rng.choice(words)
    rect = [round(v, 1) for v in (w[0] - 1, w[1] - 1, w[2] + 1, w[3] + 1)]
    doc[0].draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    return {"method": "whiteout", "page": 0, "bbox": rect, "covered": w[4]}


def mutate_drift(doc: Any, seed: int = 0) -> Dict[str, Any]:
    """Ghost-duplicate a word invisibly offset ~1px (cheap-scanner layer slip:
    1px at 150dpi ≈ 0.48pt). Extraction sees doubled tokens."""
    import random
    rng = random.Random(seed)
    words = [w for w in doc[0].get_text("words") if len((w[4] or "").strip()) >= 4]
    if not words:
        raise ValueError("mutate_drift: no words")
    w = rng.choice(words)
    doc[0].insert_text((w[0] + 0.48, w[3]), w[4], fontsize=10, color=(1, 1, 1))
    return {"method": "drift1px", "page": 0, "bbox": [round(v, 1) for v in w[:4]],
            "text": w[4]}


def mutate_homoglyph(doc: Any, seed: int = 0) -> Dict[str, Any]:
    """Append an invisible Cyrillic-swapped entity line (CMap/homoglyph vector:
    renders blank, extracts hostile)."""
    import random
    rng = random.Random(seed)
    cands = [w[4] for w in doc[0].get_text("words")
             if (w[4] or "").isascii() and (w[4] or "").isalpha() and len(w[4]) >= 4]
    base = rng.choice(cands) if cands else "Acme"
    hostile = base.translate(HOMOGLYPH_MAP)
    if hostile == base:
        hostile = "Аcme"
    doc[0].insert_text((72, 40), hostile, fontsize=10, color=(1, 1, 1))
    return {"method": "homoglyph", "page": 0, "text": hostile, "base": base}


MUTATORS = {"whiteout": mutate_whiteout, "drift1px": mutate_drift, "homoglyph": mutate_homoglyph}


def mutate_manifest(manifest_path: str, out_dir: str, rate: float = 0.10,
                    seed: int = 7) -> int:
    """Poison our own well: mutate `rate` of pristine docs (round-robin across
    the three methods, seeded positions), hash the mutants, and reseal the
    manifest. Mutants are appended as first-class docs (mutated:true) with
    ground-truth zones for zero-human auto-labeling. Quota counts stay pure.
    """
    import fitz
    man = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    docs = man.get("docs", [])
    if man.get("mutated"):
        print("REFUSE: manifest already mutated (re-mutating compounds ground truth)")
        return 1
    n = max(1, int(len(docs) * rate))
    step = max(1, len(docs) // n)
    picks = docs[::step][:n]
    methods = list(MUTATORS)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    mutants = []
    for i, rec in enumerate(picks):
        method = methods[i % len(methods)]
        try:
            doc = fitz.open(_longpath(rec["path"]))
        except Exception as e:
            print(f"skip {rec['path']}: {e}")
            continue
        # Unique mutant filename: source-hash prefix disambiguates duplicate
        # stems across folders (measured: 36 duplicate stems in VUC dump —
        # stem-only names silently overwrote each other and forged DRIFT).
        try:
            srchash = sha256_file(Path(rec["path"]))[:8]
        except Exception as e:
            print(f"skip {rec['path']}: {e}")
            continue
        try:
            detail = MUTATORS[method](doc, seed=seed + i)
        except ValueError as e:
            print(f"skip {rec['path']}: {e}")
            continue
        mp = out / (Path(rec["path"]).stem + f".{srchash}.mutated-{method}.pdf")
        try:
            doc.save(str(mp))
        except Exception as e:
            print(f"skip {rec['path']}: save failed: {e}")
            doc.close()
            continue
        doc.close()
        mutants.append({"path": str(mp), "stratum": rec["stratum"], "mutated": True,
                        "sha256": sha256_file(mp), "mutation": detail,
                        "source": rec["path"]})
    man["mutated"] = mutants
    man["mutation_rate"] = rate
    all_hashes = sorted([r["sha256"] for r in docs] + [m["sha256"] for m in mutants])
    man["corpus_sha256"] = hashlib.sha256("".join(all_hashes).encode()).hexdigest()
    Path(manifest_path).write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(f"MUTATED: {len(mutants)} ({', '.join(methods)}) | corpus {man['corpus_sha256'][:16]}…")
    return 0


def label_from_mutations(field_bbox: Optional[tuple],
                         mutations: List[Dict[str, Any]]) -> Optional[bool]:
    """Zero-human ground truth: a field intersecting a mutation zone is a
    known anomaly (expected strict_ok=False); anything else is unlabeled
    (None) — never auto-legit. Harness-side label assist for shadow runs."""
    if not field_bbox or not mutations:
        return None
    for m in mutations:
        zone = (m.get("mutation") or {}).get("bbox")
        if zone and not (field_bbox[2] <= zone[0] or zone[2] <= field_bbox[0]
                         or field_bbox[3] <= zone[1] or zone[3] <= field_bbox[1]):
            return False
        if (m.get("mutation") or {}).get("method") in ("homoglyph", "drift1px"):
            return False  # page-level contamination: no field on it is clean
    return None


def verify_manifest(manifest_path: str) -> int:
    """Rehash every pinned doc AND mutant. Any drift/missing/substitution -> halt 1."""
    man = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    items = list(man.get("docs", [])) + list(man.get("mutated", []))
    bad = []
    for rec in items:
        p = Path(rec["path"])
        # exists() needs the same long-path bypass (returns False past 260 chars)
        if not os.path.exists(_longpath(p)):
            bad.append(f"{rec['path']}: MISSING")
            continue
        if sha256_file(p) != rec.get("sha256", ""):
            bad.append(f"{rec['path']}: DRIFT")
    if bad:
        print(f"DRIFT-HALT ({len(bad)}):")
        for b in bad[:20]:
            print(f"  {b}")
        return 1
    combo = hashlib.sha256("".join(sorted(r.get("sha256", "") for r in items)).encode()).hexdigest()
    if combo != man.get("corpus_sha256", ""):
        print("DRIFT-HALT: corpus digest mismatch (membership changed)")
        return 1
    print(f"VERIFIED: {len(items)} docs ({len(man.get('mutated', []))} mutated), "
          f"corpus {man.get('corpus_sha256', '')[:16]}…")
    return 0


def main(argv: List[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(argv) >= 2 and argv[1] == "--verify":
        if len(argv) < 3:
            print("usage: build_shadow_corpus.py --verify <manifest.json>")
            return 2
        return verify_manifest(argv[2])
    if len(argv) >= 2 and argv[1] == "--mutate":
        if len(argv) < 4:
            print("usage: build_shadow_corpus.py --mutate <manifest.json> <out_dir> [--rate R] [--seed S]")
            return 2
        rate, seed = 0.10, 7
        if "--rate" in argv:
            rate = float(argv[argv.index("--rate") + 1])
        if "--seed" in argv:
            seed = int(argv[argv.index("--seed") + 1])
        return mutate_manifest(argv[2], argv[3], rate=rate, seed=seed)
    if len(argv) < 3:
        print("usage: build_shadow_corpus.py <pdf_dir> <out_manifest.json> [--need N]")
        print("   or: build_shadow_corpus.py --verify <manifest.json>")
        return 2
    need = 1000
    if "--need" in argv:
        need = int(argv[argv.index("--need") + 1])
    matrix = MATRICES[ACTIVE_MATRIX]
    # Multi-root: semicolon-separated source dirs (top-up pools merge; the
    # manifest records each doc's origin root for provenance).
    roots = [r for r in argv[1].split(";") if r]
    pdfs = []
    for rt in roots:
        pdfs.extend(sorted(Path(rt).rglob("*.pdf")))
    buckets: Dict[str, List[Dict[str, Any]]] = {s: [] for s in STRATA}
    pheno: Dict[str, List[Dict[str, Any]]] = {b: [] for b in matrix}
    for pdf in pdfs:
        try:
            rec = classify(pdf)
        except Exception as e:  # noqa: BLE001
            print(f"skip {pdf}: {e}")
            continue
        buckets[rec["stratum"]].append(rec)
        for b in phenomena(rec["signals"], rec["signals"].get("images", 0),
                           rec["signals"].get("words", 0)):
            if b in pheno:
                pheno[b].append(rec)
    quota_n = {b: int(need * q) for b, q in matrix.items()}
    short = {b: quota_n[b] - len(pheno[b]) for b in quota_n if len(pheno[b]) < quota_n[b]}
    have = {b: len(pheno[b]) for b in quota_n}
    if short:
        print(f"INVALID corpus [{ACTIVE_MATRIX}]: shortfall {short} (have {have})")
        return 1
    import random
    # Deterministic shuffle (seed 7) before quota slicing: directory order is
    # vendor-clustered, and first-N slicing would over-fit dominant folders.
    rng = random.Random(7)
    by_path: Dict[str, Dict[str, Any]] = {}
    for b in quota_n:
        pool = list(pheno[b])
        rng.shuffle(pool)
        for r in pool[:quota_n[b]]:
            e = by_path.setdefault(r["path"], dict(r))
            e.setdefault("buckets", [])
            if b not in e["buckets"]:
                e["buckets"].append(b)
    docs = []
    for e in by_path.values():
        e["sha256"] = sha256_file(Path(e["path"]))
        docs.append(e)
    overlap = sum(len(e.get("buckets", [])) for e in docs) - len(docs)
    corpus_sha = hashlib.sha256("".join(sorted(r["sha256"] for r in docs)).encode()).hexdigest()
    manifest = {"need": need, "matrix": ACTIVE_MATRIX, "quota": quota_n,
                "unique_docs": len(docs), "overlap_assignments": overlap,
                "corpus_sha256": corpus_sha, "docs": docs}
    Path(argv[2]).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"VALID corpus [{ACTIVE_MATRIX}]: {len(docs)} unique docs "
          f"({overlap} multi-bucket) @ "
          + ", ".join(f"{b}={quota_n[b]}" for b in quota_n)
          + f" | corpus {corpus_sha[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
