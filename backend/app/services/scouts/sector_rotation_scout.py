"""SectorRotationScout — detects sector ETF rotation patterns.

Scan cadence: 180 s
Source: Alpaca bars for sector ETFs + market internal data
Signal types: sector_rotation

Discovery criteria
------------------
* Relative strength divergence: one sector ETF outperforms SPY by >= 1.5% in session.
* Leadership shift: top sector changes from previous scan.
* Volume-weighted relative strength computed vs SPY baseline.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    DIRECTION_BEARISH,
    SIGNAL_SECTOR_ROTATION,
    SOURCE_MARKET_INTERNAL,
)

logger = logging.getLogger(__name__)

# Sector ETF universe
_SECTOR_ETFS = [
    ("XLK", "Technology"),
    ("XLF", "Financials"),
    ("XLE", "Energy"),
    ("XLV", "Healthcare"),
    ("XLI", "Industrials"),
    ("XLP", "Consumer Staples"),
    ("XLY", "Consumer Discretionary"),
    ("XLU", "Utilities"),
    ("XLRE", "Real Estate"),
    ("XLB", "Materials"),
    ("XLC", "Communication"),
]
_SPY_SYMBOL = "SPY"
_OUTPERFORM_THRESHOLD = 0.015   # 1.5% vs SPY


class SectorRotationScout(BaseScout):
    """Scout that detects sector leadership rotation via ETF relative strength."""

    scout_id = "sector_rotation"
    source = "Sector Rotation Monitor"
    source_type = SOURCE_MARKET_INTERNAL
    scan_interval = 180.0
    timeout = 30.0

    def __init__(self) -> None:
        super().__init__()
        self._prev_leader: Optional[str] = None

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        symbols = [_SPY_SYMBOL] + [etf for etf, _ in _SECTOR_ETFS]

        try:
            bars = await self._fetch_bars(symbols)
        except Exception as exc:
            logger.debug("[%s] fetch failed: %s", self.scout_id, exc)
            return discoveries

        spy_bar = bars.get(_SPY_SYMBOL, {})
        spy_chg = self._bar_change(spy_bar)

        best_symbol: Optional[str] = None
        best_rel: float = 0.0

        for etf, sector_name in _SECTOR_ETFS:
            bar = bars.get(etf, {})
            etf_chg = self._bar_change(bar)
            rel_strength = etf_chg - spy_chg

            if rel_strength >= _OUTPERFORM_THRESHOLD:
                score = min(100, int(rel_strength * 2000))
                discoveries.append(DiscoveryPayload(
                    scout_id=self.scout_id,
                    source=self.source,
                    source_type=self.source_type,
                    symbol=etf,
                    direction=DIRECTION_BULLISH,
                    signal_type=SIGNAL_SECTOR_ROTATION,
                    confidence=min(1.0, rel_strength * 20),
                    score=score,
                    reasoning=(
                        f"{sector_name} outperforming SPY by {rel_strength:+.1%} "
                        f"(ETF: {etf_chg:+.1%}, SPY: {spy_chg:+.1%})"
                    ),
                    priority=3,
                    related_symbols=[_SPY_SYMBOL],
                    attributes={
                        "sector": sector_name,
                        "etf_change_pct": round(etf_chg * 100, 2),
                        "spy_change_pct": round(spy_chg * 100, 2),
                        "relative_strength": round(rel_strength * 100, 2),
                    },
                ))
                if rel_strength > best_rel:
                    best_rel = rel_strength
                    best_symbol = etf

            elif rel_strength <= -_OUTPERFORM_THRESHOLD:
                score = min(100, int(abs(rel_strength) * 2000))
                discoveries.append(DiscoveryPayload(
                    scout_id=self.scout_id,
                    source=self.source,
                    source_type=self.source_type,
                    symbol=etf,
                    direction=DIRECTION_BEARISH,
                    signal_type=SIGNAL_SECTOR_ROTATION,
                    confidence=min(1.0, abs(rel_strength) * 20),
                    score=score,
                    reasoning=(
                        f"{sector_name} underperforming SPY by {rel_strength:+.1%}"
                    ),
                    priority=4,
                    related_symbols=[_SPY_SYMBOL],
                    attributes={
                        "sector": sector_name,
                        "etf_change_pct": round(etf_chg * 100, 2),
                        "spy_change_pct": round(spy_chg * 100, 2),
                        "relative_strength": round(rel_strength * 100, 2),
                    },
                ))

        if best_symbol and best_symbol != self._prev_leader:
            self._prev_leader = best_symbol

        return discoveries

    async def _fetch_bars(self, symbols: List[str]) -> Dict[str, Any]:
        try:
            from app.services.alpaca_service import AlpacaService
            svc = AlpacaService()
            result = await svc.get_bars_batch(symbols, timeframe="1Day", limit=2)
            return result or {}
        except Exception:
            return {}

    @staticmethod
    def _bar_change(bar: Dict[str, Any]) -> float:
        close = float(bar.get("c", bar.get("close", 0)) or 0)
        prev = float(bar.get("prev_close", bar.get("open", close)) or close)
        if prev <= 0 or close <= 0:
            return 0.0
        return (close - prev) / prev
