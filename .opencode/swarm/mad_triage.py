"""
MAD Triage — Outlier-Immune Routing Gate
Uses Median Absolute Deviation instead of Z-score for robust
signal detection in skewed embedding neighborhoods.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import List


class RoutingDecision(Enum):
    VAULT_ONLY = "VAULT_ONLY"
    SPECULATIVE = "SPECULATIVE"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class TriageResult:
    decision: RoutingDecision
    top1_score: float
    median: float
    mad: float
    modified_z: float
    decayed_top1: float
    k_neighbors: int
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "top1_score": self.top1_score,
            "median": self.median,
            "mad": self.mad,
            "modified_z": self.modified_z,
            "decayed_top1": self.decayed_top1,
            "k_neighbors": self.k_neighbors,
            "timestamp": self.timestamp,
        }


# Thresholds for modified Z-score (MAD-based)
VAULT_THRESHOLD = 3.5
SPECULATIVE_THRESHOLD = 1.0
# Consistency constant for normal distribution alignment
MAD_CONSISTENCY = 0.6745


def _median(values: List[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def calculate_modified_z(
    scores: List[float],
    decay_factor: float = 1.0,
) -> TriageResult:
    """
    Calculate Modified Z-score using Median Absolute Deviation.

    Args:
        scores: Cosine similarity scores of top-k Vault neighbors.
        decay_factor: Half-life decay multiplier applied to Top-1 score.

    Returns:
        TriageResult with routing decision.
    """
    if not scores:
        return TriageResult(
            decision=RoutingDecision.SPECULATIVE,
            top1_score=0.0,
            median=0.0,
            mad=0.0,
            modified_z=0.0,
            decayed_top1=0.0,
            k_neighbors=0,
            timestamp=time.time(),
        )

    sorted_scores = sorted(scores, reverse=True)
    top1_raw = sorted_scores[0]
    decayed_top1 = top1_raw * decay_factor

    med = _median(scores)

    absolute_deviations = [abs(s - med) for s in scores]
    mad = _median(absolute_deviations)

    if mad == 0:
        if decayed_top1 > med:
            modified_z = 10.0
        elif decayed_top1 == med:
            modified_z = 0.0
        else:
            modified_z = -10.0
    else:
        modified_z = MAD_CONSISTENCY * (decayed_top1 - med) / mad

    if modified_z > VAULT_THRESHOLD:
        decision = RoutingDecision.VAULT_ONLY
    elif modified_z < SPECULATIVE_THRESHOLD:
        decision = RoutingDecision.SPECULATIVE
    else:
        decision = RoutingDecision.AMBIGUOUS

    return TriageResult(
        decision=decision,
        top1_score=round(top1_raw, 6),
        median=round(med, 6),
        mad=round(mad, 6),
        modified_z=round(modified_z, 4),
        decayed_top1=round(decayed_top1, 6),
        k_neighbors=len(scores),
        timestamp=time.time(),
    )
