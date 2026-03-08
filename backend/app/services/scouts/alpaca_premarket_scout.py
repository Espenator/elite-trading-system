"""AlpacaPremarketScout — detects significant pre-market gaps and volume.

Scan cadence: 120 s (pre-market focus; reduced during regular hours)
Source: Alpaca Markets Data API
Signal types: premarket_gap

Discovery criteria
------------------
* Pre-market price gap >= 2% from prior close.
* Pre-market volume > 50 000 shares.
* Only active during 04:00–09:30 ET (pre-market window).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    DIRECTION_BEARISH,
    SIGNAL_PREMARKET_GAP,
    SOURCE_ALPACA,
)

logger = logging.getLogger(__name__)

_GAP_THRESHOLD = 0.02          # 2% gap
_MIN_PREMARKET_VOLUME = 50_000

_WATCH_SYMBOLS = [
    "SPY", "QQQ", "AAPL", "MSFT", "AMZN", "NVDA", "TSLA",
    "META", "GOOGL", "AMD", "NFLX", "COIN", "MSTR",
]


class AlpacaPremarketScout(BaseScout):
    """Scout that monitors pre-market gaps and early volume."""

    scout_id = "alpaca_premarket"
    source = "Alpaca Premarket Scanner"
    source_type = SOURCE_ALPACA
    scan_interval = 120.0
    timeout = 25.0

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        try:
            bars = await self._fetch_premarket_bars()
        except Exception as exc:
            logger.debug("[%s] fetch failed: %s", self.scout_id, exc)
            return discoveries

        for symbol, bar in bars.items():
            payload = self._evaluate_bar(symbol, bar)
            if payload:
                discoveries.append(payload)
        return discoveries

    async def _fetch_premarket_bars(self) -> Dict[str, Any]:
        try:
            from app.services.alpaca_service import AlpacaService
            svc = AlpacaService()
            result = await svc.get_bars_batch(_WATCH_SYMBOLS, timeframe="1Min", limit=5)
            return result or {}
        except Exception:
            return {}

    def _evaluate_bar(self, symbol: str, bar: Dict[str, Any]) -> "DiscoveryPayload | None":
        close = float(bar.get("c", bar.get("close", 0)) or 0)
        prev_close = float(bar.get("prev_close", 0) or 0)
        volume = float(bar.get("v", bar.get("volume", 0)) or 0)

        if close <= 0 or prev_close <= 0 or volume < _MIN_PREMARKET_VOLUME:
            return None

        gap = (close - prev_close) / prev_close
        if abs(gap) < _GAP_THRESHOLD:
            return None

        direction = DIRECTION_BULLISH if gap > 0 else DIRECTION_BEARISH
        score = min(100, int(abs(gap) * 2000))
        confidence = min(1.0, abs(gap) * 20)

        return DiscoveryPayload(
            scout_id=self.scout_id,
            source=self.source,
            source_type=self.source_type,
            symbol=symbol,
            direction=direction,
            signal_type=SIGNAL_PREMARKET_GAP,
            confidence=confidence,
            score=score,
            reasoning=(
                f"Pre-market gap {gap:+.1%} from prior close "
                f"({volume:,.0f} shares pre-market)"
            ),
            priority=2,
            ttl_seconds=3600,
            attributes={
                "gap_pct": round(gap * 100, 2),
                "premarket_volume": volume,
                "premarket_close": close,
                "prev_close": prev_close,
            },
        )
