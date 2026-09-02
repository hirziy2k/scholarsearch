"""
Volume Velocity Gatekeeper
Laplace-smoothed zero-day detection for the Swarm cascade.
Prevents ZeroDivisionError on novel concepts while preserving spike magnitude.
"""

import time
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class VelocityStatus(Enum):
    ZERO_DAY_SPIKE = "ZERO_DAY_SPIKE"
    TRENDING_VOLATILE = "TRENDING_VOLATILE"
    STABLE_VOLUME = "STABLE_VOLUME"


class RoutingAction(Enum):
    BYPASS_MACD = "BYPASS_MACD"
    ELEVATE_MACD_FLOOR = "ELEVATE_MACD_FLOOR"
    NORMAL_MACD = "NORMAL_MACD"


@dataclass(frozen=True)
class VelocityResult:
    status: VelocityStatus
    action: RoutingAction
    lambda_value: Optional[float]
    velocity_ratio: float
    baseline_count: int
    current_count: int
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "action": self.action.value,
            "lambda_value": self.lambda_value,
            "velocity_ratio": self.velocity_ratio,
            "baseline_count": self.baseline_count,
            "current_count": self.current_count,
            "timestamp": self.timestamp,
        }


# Thresholds
SPIKE_THRESHOLD = 10.0
TRENDING_THRESHOLD = 3.0
MAX_LAMBDA = 0.30


def calculate_volume_velocity(
    current_occurrences: int,
    baseline_average: float,
) -> VelocityResult:
    """
    Laplace-smoothed volume velocity for zero-day detection.

    Args:
        current_occurrences: Rolling 1-hour occurrence count (int).
        baseline_average: Historical average occurrence rate (float).

    Returns:
        VelocityResult with routing decision and lambda override.
    """
    smoothed_current = current_occurrences + 1
    smoothed_baseline = baseline_average + 1

    velocity_ratio = smoothed_current / smoothed_baseline

    if velocity_ratio > SPIKE_THRESHOLD:
        return VelocityResult(
            status=VelocityStatus.ZERO_DAY_SPIKE,
            action=RoutingAction.BYPASS_MACD,
            lambda_value=MAX_LAMBDA,
            velocity_ratio=round(velocity_ratio, 2),
            baseline_count=current_occurrences,
            current_count=current_occurrences,
            timestamp=time.time(),
        )
    elif velocity_ratio > TRENDING_THRESHOLD:
        return VelocityResult(
            status=VelocityStatus.TRENDING_VOLATILE,
            action=RoutingAction.ELEVATE_MACD_FLOOR,
            lambda_value=None,
            velocity_ratio=round(velocity_ratio, 2),
            baseline_count=current_occurrences,
            current_count=current_occurrences,
            timestamp=time.time(),
        )
    else:
        return VelocityResult(
            status=VelocityStatus.STABLE_VOLUME,
            action=RoutingAction.NORMAL_MACD,
            lambda_value=None,
            velocity_ratio=round(velocity_ratio, 2),
            baseline_count=current_occurrences,
            current_count=current_occurrences,
            timestamp=time.time(),
        )


class IngressTelemetry:
    """
    Tracks query occurrences for volume velocity calculation.
    Stores rolling 1-hour windows per query hash.
    """

    def __init__(self, window_seconds: int = 3600):
        self._window_seconds = window_seconds
        self._occurrences: dict[str, list[float]] = {}
        self._baselines: dict[str, float] = {}

    def record_occurrence(self, query_hash: str) -> None:
        now = time.time()
        if query_hash not in self._occurrences:
            self._occurrences[query_hash] = []
        self._occurrences[query_hash].append(now)
        self._prune(query_hash, now)

    def get_current_rate(self, query_hash: str) -> int:
        now = time.time()
        self._prune(query_hash, now)
        return len(self._occurrences.get(query_hash, []))

    def set_baseline(self, query_hash: str, baseline: float) -> None:
        self._baselines[query_hash] = baseline

    def get_baseline(self, query_hash: str) -> float:
        return self._baselines.get(query_hash, 0.0)

    def evaluate(self, query_hash: str) -> VelocityResult:
        current = self.get_current_rate(query_hash)
        baseline = self.get_baseline(query_hash)
        return calculate_volume_velocity(current, baseline)

    def _prune(self, query_hash: str, now: float) -> None:
        if query_hash not in self._occurrences:
            return
        cutoff = now - self._window_seconds
        self._occurrences[query_hash] = [
            t for t in self._occurrences[query_hash] if t > cutoff
        ]


def compute_decay_lambda(
    velocity_result: VelocityResult,
    macd_divergence: float,
    base_lambda: float = 0.02,
) -> float:
    """
    Combines volume velocity with MACD momentum to produce final lambda.

    Args:
        velocity_result: Output from calculate_volume_velocity.
        macd_divergence: MACD line minus signal line.
        base_lambda: Default decay constant for stable topics.

    Returns:
        Final lambda value for half-life decay multiplier.
    """
    if velocity_result.lambda_value is not None:
        return velocity_result.lambda_value

    if macd_divergence > 0:
        momentum_boost = min(macd_divergence * 0.1, 0.15)
        return base_lambda + momentum_boost

    return base_lambda
