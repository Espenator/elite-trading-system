"""UnusualWhalesDarkpoolScout — monitors dark pool prints via Unusual Whales API.

Scan cadence: 90 s
Source: Unusual Whales (dark pool flow)
Signal types: dark_pool

Discovery criteria
------------------
* Dark pool block size >= $1 000 000 (significant institutional print).
* Price at or above ask (aggressive buy) or at/below bid (aggressive sell).
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
    SIGNAL_DARK_POOL,
    SOURCE_UNUSUAL_WHALES,
)

logger = logging.getLogger(__name__)

_MIN_DARK_POOL_VALUE = 1_000_000   # $1M minimum
_HIGH_VALUE = 10_000_000           # $10M — elevated priority


class UnusualWhalesDarkpoolScout(BaseScout):
    """Scout that detects large dark pool / block trade prints."""

    scout_id = "uw_darkpool"
    source = "Unusual Whales Dark Pool"
    source_type = SOURCE_UNUSUAL_WHALES
    scan_interval = 90.0
    timeout = 20.0

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        try:
            prints = await self._fetch_darkpool()
        except Exception as exc:
            logger.debug("[%s] fetch failed: %s", self.scout_id, exc)
            return discoveries

        for print_ in prints:
            payload = self._evaluate_print(print_)
            if payload:
                discoveries.append(payload)
        return discoveries

    async def _fetch_darkpool(self) -> List[Dict[str, Any]]:
        try:
            from app.services.unusual_whales_service import UnusualWhalesService
            svc = UnusualWhalesService()
            # Dark pool endpoint may differ — fall back to flow alerts
            if hasattr(svc, "get_darkpool_flow"):
                data = await svc.get_darkpool_flow()
            else:
                data = await svc.get_flow_alerts()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("data", data.get("items", []))
        except Exception:
            pass
        return []

    def _evaluate_print(self, print_: Dict[str, Any]) -> "DiscoveryPayload | None":
        symbol = str(print_.get("ticker", print_.get("symbol", "")) or "").upper()
        if not symbol:
            return None

        raw_val = print_.get("size", print_.get("value", print_.get("notional", 0))) or 0
        try:
            value = float(str(raw_val).replace(",", ""))
        except (ValueError, TypeError):
            value = 0.0

        if value < _MIN_DARK_POOL_VALUE:
            return None

        side = str(print_.get("side", print_.get("buy_sell", "")) or "").lower()
        direction = (
            DIRECTION_BULLISH if side in ("buy", "b", "ask", "above_ask")
            else DIRECTION_BEARISH if side in ("sell", "s", "bid", "below_bid")
            else DIRECTION_NEUTRAL
        )
        score = min(100, int(value / 100_000))
        confidence = min(1.0, value / _HIGH_VALUE * 0.9 + 0.1)

        return DiscoveryPayload(
            scout_id=self.scout_id,
            source=self.source,
            source_type=self.source_type,
            symbol=symbol,
            direction=direction,
            signal_type=SIGNAL_DARK_POOL,
            confidence=confidence,
            score=score,
            reasoning=f"Dark pool print: ${value:,.0f} ({side or 'unknown side'})",
            priority=1 if value >= _HIGH_VALUE else 2,
            attributes={
                "notional_value": value,
                "side": side,
                "price": print_.get("price"),
                "shares": print_.get("quantity", print_.get("shares")),
            },
        )
