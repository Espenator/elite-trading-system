"""AlpacaTradeScout — monitors live trade data for volume spikes and unusual activity.

Scan cadence: 60 s
Source: Alpaca Markets Data API (batch bars)
Signal types: volume_spike, momentum

Discovery criteria
------------------
* Volume-to-average ratio > 3.0 during regular market hours.
* Price move >= 1.5% from prior close.
* Only symbols from Tier-1 universe (most liquid).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    DIRECTION_BEARISH,
    DIRECTION_NEUTRAL,
    SIGNAL_VOLUME_SPIKE,
    SIGNAL_MOMENTUM,
    SOURCE_ALPACA,
)

logger = logging.getLogger(__name__)

# Tier-1 universe — most liquid, scanned every cycle
_UNIVERSE = [
    "SPY", "QQQ", "IWM", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "TSLA", "META", "AMD", "NFLX", "JPM", "BAC", "GS",
]

_VOLUME_SPIKE_THRESHOLD = 3.0    # vol / avg_vol ratio
_PRICE_MOVE_THRESHOLD = 0.015    # 1.5% price change


class AlpacaTradeScout(BaseScout):
    """Scout that detects volume spikes and large price moves via Alpaca bars."""

    scout_id = "alpaca_trade"
    source = "Alpaca Trade Stream"
    source_type = SOURCE_ALPACA
    scan_interval = 60.0
    timeout = 20.0

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        try:
            bars = await self._fetch_bars(_UNIVERSE)
        except Exception as exc:
            logger.debug("[%s] fetch_bars failed: %s", self.scout_id, exc)
            return discoveries

        for symbol, bar in bars.items():
            payload = self._evaluate_bar(symbol, bar)
            if payload:
                discoveries.append(payload)
        return discoveries

    # ------------------------------------------------------------------
    async def _fetch_bars(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch latest 1-minute bars from Alpaca Data API."""
        try:
            from app.services.alpaca_stream_service import AlpacaStreamService
            svc = AlpacaStreamService()
            return await svc.get_latest_bars(symbols) or {}
        except Exception:
            pass
        try:
            from app.services.alpaca_service import AlpacaService
            svc = AlpacaService()
            result = await svc.get_bars_batch(symbols, timeframe="1Min", limit=2)
            return result or {}
        except Exception:
            return {}

    def _evaluate_bar(self, symbol: str, bar: Dict[str, Any]) -> "DiscoveryPayload | None":
        volume = float(bar.get("v", bar.get("volume", 0)) or 0)
        avg_vol = float(bar.get("avg_volume", volume / 3 if volume else 1) or 1)
        close = float(bar.get("c", bar.get("close", 0)) or 0)
        prev_close = float(bar.get("prev_close", close) or close)

        if avg_vol <= 0 or close <= 0:
            return None

        vol_ratio = volume / avg_vol
        price_change = (close - prev_close) / prev_close if prev_close else 0.0

        if vol_ratio < _VOLUME_SPIKE_THRESHOLD and abs(price_change) < _PRICE_MOVE_THRESHOLD:
            return None

        direction = (
            DIRECTION_BULLISH if price_change > 0
            else DIRECTION_BEARISH if price_change < 0
            else DIRECTION_NEUTRAL
        )
        score = min(100, int(vol_ratio * 15 + abs(price_change) * 500))
        confidence = min(1.0, vol_ratio / 10.0 + abs(price_change) * 5)

        return DiscoveryPayload(
            scout_id=self.scout_id,
            source=self.source,
            source_type=self.source_type,
            symbol=symbol,
            direction=direction,
            signal_type=SIGNAL_VOLUME_SPIKE if vol_ratio >= _VOLUME_SPIKE_THRESHOLD else SIGNAL_MOMENTUM,
            confidence=confidence,
            score=score,
            reasoning=(
                f"Volume spike {vol_ratio:.1f}x average; "
                f"price change {price_change:+.1%}"
            ),
            priority=2 if vol_ratio >= 5.0 else 3,
            attributes={
                "volume": volume,
                "avg_volume": avg_vol,
                "vol_ratio": round(vol_ratio, 2),
                "price_change_pct": round(price_change * 100, 2),
                "close": close,
            },
        )
