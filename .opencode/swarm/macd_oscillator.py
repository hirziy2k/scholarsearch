"""
MACD Momentum Oscillator
Tracks velocity of query occurrences for semantic volatility detection.
Gated by volume_velocity.py to prevent zero-day calculation failures.
"""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MACDResult:
    macd_line: float
    signal_line: float
    divergence: float
    momentum_detected: bool
    ema_short: float
    ema_long: float
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "macd_line": self.macd_line,
            "signal_line": self.signal_line,
            "divergence": self.divergence,
            "momentum_detected": self.momentum_detected,
            "ema_short": self.ema_short,
            "ema_long": self.ema_long,
            "timestamp": self.timestamp,
        }


class MACDOscillator:
    """
    Exponential Moving Average-based MACD for query volatility tracking.

    Periods:
        - Short EMA: 12 periods
        - Long EMA: 26 periods
        - Signal EMA: 9 periods (of MACD line)
    """

    def __init__(
        self,
        short_period: int = 12,
        long_period: int = 26,
        signal_period: int = 9,
        min_data_points: int = 26,
    ):
        self._short_period = short_period
        self._long_period = long_period
        self._signal_period = signal_period
        self._min_data_points = min_data_points

        self._short_ema: Optional[float] = None
        self._long_ema: Optional[float] = None
        self._signal_ema: Optional[float] = None
        self._macd_history: list[float] = []
        self._data_points: int = 0

    def _ema_multiplier(self, period: int) -> float:
        return 2 / (period + 1)

    def update(self, value: float) -> MACDResult:
        """
        Feed a new occurrence count and get updated MACD state.

        Args:
            value: Current period's occurrence count.

        Returns:
            MACDResult with current momentum state.
        """
        self._data_points += 1

        if self._short_ema is None:
            self._short_ema = value
            self._long_ema = value
            return self._build_result(ema_short=value, ema_long=value)

        alpha_short = self._ema_multiplier(self._short_period)
        alpha_long = self._ema_multiplier(self._long_period)

        self._short_ema = (value - self._short_ema) * alpha_short + self._short_ema
        self._long_ema = (value - self._long_ema) * alpha_long + self._long_ema

        macd_line = self._short_ema - self._long_ema
        self._macd_history.append(macd_line)

        if len(self._macd_history) >= self._signal_period:
            alpha_signal = self._ema_multiplier(self._signal_period)
            recent_macd = self._macd_history[-self._signal_period:]

            if self._signal_ema is None:
                self._signal_ema = sum(recent_macd) / len(recent_macd)
            else:
                self._signal_ema = (
                    macd_line - self._signal_ema
                ) * alpha_signal + self._signal_ema
        else:
            self._signal_ema = macd_line

        divergence = macd_line - self._signal_ema

        return self._build_result(
            ema_short=self._short_ema,
            ema_long=self._long_ema,
            macd_line=macd_line,
            signal_line=self._signal_ema,
            divergence=divergence,
        )

    def _build_result(
        self,
        ema_short: float,
        ema_long: float,
        macd_line: float = 0.0,
        signal_line: float = 0.0,
        divergence: float = 0.0,
    ) -> MACDResult:
        return MACDResult(
            macd_line=round(macd_line, 6),
            signal_line=round(signal_line, 6),
            divergence=round(divergence, 6),
            momentum_detected=divergence > 0,
            ema_short=round(ema_short, 6),
            ema_long=round(ema_long, 6),
            timestamp=time.time(),
        )

    def has_sufficient_data(self) -> bool:
        return self._data_points >= self._min_data_points

    def reset(self) -> None:
        self._short_ema = None
        self._long_ema = None
        self._signal_ema = None
        self._macd_history.clear()
        self._data_points = 0
