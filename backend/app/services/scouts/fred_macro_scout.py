"""FredMacroScout — detects macro regime shifts via FRED data.

Scan cadence: 300 s (macro data changes slowly)
Source: FRED (Federal Reserve Economic Data)
Signal types: macro_shift

Monitored series
----------------
* FEDFUNDS — Fed funds rate (monetary policy)
* T10Y2Y  — 10Y-2Y yield curve spread (recession signal)
* VIXCLS  — CBOE Volatility Index
* CPIAUCSL — CPI (inflation)
* UNRATE  — Unemployment rate
* DGS10   — 10-Year Treasury yield
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    DIRECTION_BEARISH,
    DIRECTION_NEUTRAL,
    SIGNAL_MACRO_SHIFT,
    SOURCE_FRED,
)

logger = logging.getLogger(__name__)

# (series_id, display_name, bearish_direction_if_rising)
_SERIES: List[Tuple[str, str, str]] = [
    ("FEDFUNDS", "Fed Funds Rate", "bearish"),
    ("T10Y2Y", "Yield Curve (10Y-2Y)", "bearish"),    # inversion = bearish
    ("VIXCLS", "VIX", "bearish"),
    ("CPIAUCSL", "CPI Inflation", "bearish"),
    ("UNRATE", "Unemployment", "bearish"),
    ("DGS10", "10Y Treasury Yield", "bearish"),
]

# Minimum % change to flag as a macro shift
_CHANGE_THRESHOLD = 0.03   # 3% relative change


class FredMacroScout(BaseScout):
    """Scout that monitors FRED macro data series for regime-shift signals."""

    scout_id = "fred_macro"
    source = "FRED Macro Data"
    source_type = SOURCE_FRED
    scan_interval = 300.0
    timeout = 45.0

    def __init__(self) -> None:
        super().__init__()
        self._prev_values: Dict[str, float] = {}

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        for series_id, display_name, bear_dir in _SERIES:
            try:
                obs = await self._fetch_series(series_id)
                payload = self._evaluate_series(series_id, display_name, bear_dir, obs)
                if payload:
                    discoveries.append(payload)
            except Exception as exc:
                logger.debug("[%s] %s fetch failed: %s", self.scout_id, series_id, exc)
        return discoveries

    async def _fetch_series(self, series_id: str) -> List[Dict[str, Any]]:
        try:
            from app.services.fred_service import FredService
            svc = FredService()
            return await svc.get_observations(series_id, limit=2, sort_order="desc")
        except Exception:
            return []

    def _evaluate_series(
        self,
        series_id: str,
        display_name: str,
        bear_direction_if_rising: str,
        observations: List[Dict[str, Any]],
    ) -> "DiscoveryPayload | None":
        if len(observations) < 2:
            return None

        try:
            current = float(observations[0].get("value", 0) or 0)
            previous = float(observations[1].get("value", current) or current)
        except (ValueError, TypeError):
            return None

        if previous == 0:
            return None

        change = (current - previous) / abs(previous)
        if abs(change) < _CHANGE_THRESHOLD:
            # Also store for next comparison
            self._prev_values[series_id] = current
            return None

        direction = (
            bear_direction_if_rising if change > 0
            else (DIRECTION_BULLISH if bear_direction_if_rising == DIRECTION_BEARISH else DIRECTION_BEARISH)
        )
        score = min(100, int(abs(change) * 500))
        confidence = min(1.0, abs(change) * 10)

        self._prev_values[series_id] = current

        return DiscoveryPayload(
            scout_id=self.scout_id,
            source=self.source,
            source_type=self.source_type,
            symbol="SPY",     # macro signals map to broad market
            direction=direction,
            signal_type=SIGNAL_MACRO_SHIFT,
            confidence=confidence,
            score=score,
            reasoning=(
                f"FRED {display_name} ({series_id}): "
                f"{previous:.3f} → {current:.3f} ({change:+.1%})"
            ),
            priority=2,
            ttl_seconds=3600,
            related_symbols=["QQQ", "TLT", "GLD"],
            attributes={
                "series_id": series_id,
                "display_name": display_name,
                "current_value": current,
                "previous_value": previous,
                "change_pct": round(change * 100, 4),
                "date": observations[0].get("date", ""),
            },
        )
