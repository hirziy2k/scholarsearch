#!/usr/bin/env python3
"""shadow_telemetry.py — dual-execution deployment gate (no hard rejects yet).

Every production field runs twice: the strict pipeline (all gates, verdicts
recorded but NOT enforced) and the permissive baseline (quarantine + match
only). The record captures the delta per field with coordinates and the
parameter snapshot. Hard rejection stays OFF until N production docs prove
the floors/tolerances. JSONL append-only; aggregate() summarizes.

Stdlib only. The strict/permissive callables are injected (no imports).
"""

import json
from typing import Any, Callable, Dict, List, Optional

PARAM_SNAPSHOT = {
    "ink_ratio_floor": 0.02,
    "x_tol_pt": 10.0,
    "carry_fraction": 0.20,
    "overlap_long": 0.85,
    "drift_px": 5.0,
    "ssim_floor": 0.75,
    "min_font_pt": 6.0,
}

# Adversarial cost model: a false accept (poisoned doc passes) is a legal /
# financial breach; a false reject is an availability dip the sender retries.
# COST_FALSE_ACCEPT = 50x COST_FALSE_REJECT (directive floor: 10x-100x).
COST_FALSE_ACCEPT = 50.0
COST_FALSE_REJECT = 1.0


def run_shadow(doc_id: str, page_num: int, field: Dict[str, Any], value: Any,
               source_text: str,
               strict_fn: Callable[[], Any],
               permissive_fn: Callable[[], Any],
               field_bbox: Optional[tuple] = None,
               probes: Optional[Dict[str, Any]] = None,
               label: Optional[bool] = None) -> Dict[str, Any]:
    """Execute both paths; never raises (a crashing gate is itself telemetry).

    probes: raw gate marginals for exact threshold recombination, e.g.
      {"ink_ratio": 0.0, "ssim": 0.97, "drift_px": 1.2, "other_ok": True}.
      Only the ink/ssim floors are swept; other gates are param-independent.
    label: expected strict_ok (True=legit, False=true anomaly). Unlabeled
      records are excluded from optimization but kept for rate telemetry.
    """
    try:
        s_ok, s_reason = strict_fn()
    except Exception as e:  # noqa: BLE001
        s_ok, s_reason = False, f"STRICT_CRASH: {type(e).__name__}: {e}"
    try:
        p_ok, p_reason = permissive_fn()
    except Exception as e:  # noqa: BLE001
        p_ok, p_reason = False, f"PERMISSIVE_CRASH: {type(e).__name__}: {e}"
    return {
        "doc": doc_id,
        "page": page_num,
        "field": field.get("name", field.get("type", "?")),
        "ftype": field.get("type", "?"),
        "strict_ok": bool(s_ok),
        "strict_reason": str(s_reason),
        "permissive_ok": bool(p_ok),
        "permissive_reason": str(p_reason),
        "shadow_reject": bool(p_ok and not s_ok),  # strict-only kill: the tuning signal
        "bbox": list(field_bbox) if field_bbox else None,
        "probes": dict(probes) if probes else None,
        "label": label,  # expected strict_ok or None
        "params": dict(PARAM_SNAPSHOT),
    }


def append_jsonl(path: str, record: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=True) + "\n")


def aggregate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Rates + top strict-only kill codes. Gate rule: enable hard rejects only
    when shadow_reject_rate is measured AND each top code is dispositioned."""
    n = len(records)
    kills = [r for r in records if r.get("shadow_reject")]
    by_code: Dict[str, int] = {}
    for r in kills:
        by_code[r.get("strict_reason", "?")] = by_code.get(r.get("strict_reason", "?"), 0) + 1
    return {
        "n": n,
        "strict_reject_rate": sum(1 for r in records if not r.get("strict_ok")) / n if n else 0.0,
        "permissive_reject_rate": sum(1 for r in records if not r.get("permissive_ok")) / n if n else 0.0,
        "shadow_reject_rate": len(kills) / n if n else 0.0,
        "top_shadow_codes": sorted(by_code.items(), key=lambda kv: -kv[1])[:10],
    }


def _recompute(probes: Dict[str, Any], ink_floor: float, ssim_floor: float,
               drift_cap: float = 5.0) -> bool:
    """Exact strict verdict under candidate floors. Only ink/ssim/drift gates
    are threshold functions of marginals; every other gate is folded into
    other_ok (param-independent). No re-rendering, no re-execution."""
    if not probes.get("other_ok", True):
        return False
    if probes.get("ink_ratio", 0.0) > ink_floor:
        return False
    if probes.get("drift_px", 0.0) > drift_cap:
        return False
    if probes.get("ssim", 1.0) < ssim_floor:
        return False
    return True


def optimize(records: List[Dict[str, Any]],
             ink_grid: Optional[List[float]] = None,
             ssim_grid: Optional[List[float]] = None,
             cost_fa: float = COST_FALSE_ACCEPT,
             cost_fr: float = COST_FALSE_REJECT) -> Dict[str, Any]:
    """Parameter sweep over labeled records under an ASYMMETRIC cost model.

    cost = cost_fa * FP + cost_fr * FN with cost_fa=50 (false accept = breach,
    false reject = retryable dip). Youden's J is reported for reference only —
    peacetime equal-weighting must never select production floors. Ties break
    toward STRICTER floors (default-deny): equal cost + equal delta selects
    the smallest thresholds. Unlabeled records are excluded.

    Raises ValueError on zero usable labels — an optimizer with no ground
    truth must not emit numbers.
    """
    lab = [r for r in records if r.get("label") is not None and r.get("probes")]
    if not lab:
        raise ValueError("optimize: no labeled records with probes")
    ink_grid = ink_grid or [0.005, 0.01, 0.02, 0.03, 0.05, 0.08]
    ssim_grid = ssim_grid or [0.5, 0.65, 0.75, 0.85, 0.9, 0.95]
    anomalies = [r for r in lab if r["label"] is False]
    legits = [r for r in lab if r["label"] is True]
    best: Optional[Dict[str, Any]] = None
    curve = []
    for f in ink_grid:
        for s in ssim_grid:
            fn = sum(1 for r in anomalies if _recompute(r["probes"], f, s))
            fp = sum(1 for r in legits if not _recompute(r["probes"], f, s))
            tp = len(anomalies) - fn
            tpr = tp / len(anomalies) if anomalies else 0.0
            fpr = fp / len(legits) if legits else 0.0
            delta = sum(1 for r in lab
                        if r.get("permissive_ok") and not _recompute(r["probes"], f, s)) / len(lab)
            # fn = anomaly PASSED (false accept = breach); fp = legit BLOCKED
            # (false reject = retryable dip). Cost weights the breach 50x.
            cost = cost_fa * fn + cost_fr * fp
            j = tpr - fpr
            curve.append({"ink_floor": f, "ssim_floor": s, "tpr": round(tpr, 4),
                          "fpr": round(fpr, 4), "delta": round(delta, 4),
                          "cost": round(cost, 2), "j": round(j, 4)})
            # Default-deny ties: smaller ink floor rejects more; LARGER ssim
            # floor rejects more (direction-aware — a raw sum would conflate
            # them). Equal cost+delta selects min ink AND max ssim.
            key = (cost, delta, (f - s))
            if best is None or key < best["_key"]:
                best = {"ink_ratio_floor": f, "ssim_floor": s, "tpr": round(tpr, 4),
                        "fpr": round(fpr, 4), "delta": round(delta, 4),
                        "cost": round(cost, 2), "j": round(j, 4),
                        "cost_fa": cost_fa, "cost_fr": cost_fr, "_key": key}
    assert best is not None
    best = {k: v for k, v in best.items() if not k.startswith("_")}
    return {"n_labeled": len(lab), "n_anomaly": len(anomalies), "n_legit": len(legits),
            "candidate": best, "curve": curve}


def write_candidate_config(path: str, result: Dict[str, Any]) -> None:
    """candidate_config.json: the computed solution, not a log dump."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"config": result["candidate"],
                   "evidence": {k: v for k, v in result.items() if k != "curve"},
                   "curve": result["curve"]}, fh, indent=2)
