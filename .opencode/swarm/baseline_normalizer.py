"""
Baseline Normalization Cron Job
Recalculates EMA(26) historical baseline monthly to prevent
regime drift from platform adoption inflation.
"""

import time
import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class NormalizationResult:
    query_hash: str
    old_baseline: float
    new_baseline: float
    adjustment_factor: float
    normalized_at: float

    def to_dict(self) -> dict:
        return {
            "query_hash": self.query_hash,
            "old_baseline": self.old_baseline,
            "new_baseline": self.new_baseline,
            "adjustment_factor": round(self.adjustment_factor, 4),
            "normalized_at": self.normalized_at,
        }


class BaselineNormalizer:
    """
    Normalizes MACD baselines against platform-wide query volume
    to prevent false positive momentum spikes from adoption drift.
    """

    def __init__(
        self,
        telemetry_db: sqlite3.Connection,
        lookback_days: int = 90,
        min_queries: int = 10,
    ):
        self._db = telemetry_db
        self._lookback_days = lookback_days
        self._min_queries = min_queries

    def normalize_all_baselines(
        self,
        current_volume: int,
    ) -> list[NormalizationResult]:
        """
        Normalize all tracked baselines against current platform volume.

        Args:
            current_volume: Total platform queries in current period.
        """
        cursor = self._db.cursor()
        cursor.execute("""
            SELECT query_hash, baseline_average, total_occurrences
            FROM query_baselines
            WHERE total_occurrences >= ?
        """, (self._min_queries,))

        results = []
        for row in cursor.fetchall():
            query_hash = row[0]
            old_baseline = row[1]
            total_occurrences = row[2]

            new_baseline = self._calculate_normalized_baseline(
                old_baseline, total_occurrences, current_volume
            )

            adjustment = new_baseline / old_baseline if old_baseline > 0 else 1.0

            cursor.execute("""
                UPDATE query_baselines
                SET baseline_average = ?,
                    last_normalized_at = ?,
                    normalization_count = normalization_count + 1
                WHERE query_hash = ?
            """, (new_baseline, time.time(), query_hash))

            results.append(NormalizationResult(
                query_hash=query_hash,
                old_baseline=old_baseline,
                new_baseline=new_baseline,
                adjustment_factor=adjustment,
                normalized_at=time.time(),
            ))

        self._db.commit()
        return results

    def _calculate_normalized_baseline(
        self,
        old_baseline: float,
        total_occurrences: int,
        current_volume: int,
    ) -> float:
        """
        Calculate normalized baseline using volume-weighted adjustment.
        """
        if current_volume <= 0:
            return old_baseline

        adoption_ratio = total_occurrences / current_volume
        target_baseline = old_baseline * (1 + adoption_ratio * 0.1)
        return (old_baseline * 0.7) + (target_baseline * 0.3)

    def get_platform_stats(self) -> dict:
        """Get current platform statistics."""
        cursor = self._db.cursor()

        cursor.execute("SELECT COUNT(*) FROM query_baselines")
        total_tracked = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(total_occurrences) FROM query_baselines")
        total_occurrences = cursor.fetchone()[0] or 0

        cursor.execute("SELECT AVG(baseline_average) FROM query_baselines")
        avg_baseline = cursor.fetchone()[0] or 0

        return {
            "tracked_queries": total_tracked,
            "total_occurrences": total_occurrences,
            "average_baseline": round(avg_baseline, 4),
            "normalized_at": time.time(),
        }


class CronScheduler:
    """
    Simple cron scheduler for baseline normalization.
    """

    def __init__(
        self,
        normalizer: BaselineNormalizer,
        interval_days: int = 30,
    ):
        self._normalizer = normalizer
        self._interval_days = interval_days
        self._last_run: Optional[float] = None

    def should_run(self) -> bool:
        """Check if normalization is due."""
        if self._last_run is None:
            return True

        elapsed_days = (time.time() - self._last_run) / 86400
        return elapsed_days >= self._interval_days

    def execute(self, current_volume: int) -> list[NormalizationResult]:
        """Execute normalization if due."""
        if not self.should_run():
            return []

        results = self._normalizer.normalize_all_baselines(current_volume)
        self._last_run = time.time()
        return results
