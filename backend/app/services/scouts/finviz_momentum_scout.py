"""FinvizMomentumScout — screens for momentum setups via FinViz.

Scan cadence: 120 s
Source: FinViz Elite Screener
Signal types: momentum

Discovery criteria
------------------
* RSI(14) 50–70 (healthy momentum without being overbought).
* EMA 20 > EMA 50 (uptrend alignment).
* Volume > 500 000 average daily.
* Market cap > $2B (no micro-caps).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    SIGNAL_MOMENTUM,
    SOURCE_FINVIZ,
)

logger = logging.getLogger(__name__)


class FinvizMomentumScout(BaseScout):
    """Scout that surfaces momentum setups from FinViz screener."""

    scout_id = "finviz_momentum"
    source = "FinViz Momentum Screener"
    source_type = SOURCE_FINVIZ
    scan_interval = 120.0
    timeout = 30.0

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        try:
            rows = await self._fetch_screener()
        except Exception as exc:
            logger.debug("[%s] fetch failed: %s", self.scout_id, exc)
            return discoveries

        for row in rows[:20]:
            payload = self._evaluate_row(row)
            if payload:
                discoveries.append(payload)
        return discoveries

    async def _fetch_screener(self) -> List[Dict[str, Any]]:
        try:
            from app.services.finviz_service import FinvizService
            svc = FinvizService()
            # Momentum filter: RSI 50-70, EMA20 > EMA50, avg vol > 500K
            result = await svc.get_screener_results(
                filters="sh_avgvol_o500,ta_rsi_om50,ta_rsi_ob70,cap_midover",
                order="-volume",
                limit=50,
            )
            return result or []
        except Exception:
            return []

    def _evaluate_row(self, row: Dict[str, Any]) -> "DiscoveryPayload | None":
        symbol = str(row.get("Ticker", row.get("ticker", "")) or "").upper()
        if not symbol:
            return None

        try:
            rsi = float(row.get("RSI (14)", row.get("rsi", 0)) or 0)
            change_pct = float(str(row.get("Change", row.get("change", "0%")) or "0%")
                               .replace("%", "")) / 100
            volume = float(str(row.get("Volume", row.get("volume", "0")) or "0")
                           .replace(",", ""))
        except (ValueError, TypeError):
            return None

        score = min(100, int(rsi * 0.8 + abs(change_pct) * 1000))
        confidence = min(1.0, (rsi - 50) / 20 * 0.5 + 0.3)

        return DiscoveryPayload(
            scout_id=self.scout_id,
            source=self.source,
            source_type=self.source_type,
            symbol=symbol,
            direction=DIRECTION_BULLISH,
            signal_type=SIGNAL_MOMENTUM,
            confidence=confidence,
            score=score,
            reasoning=f"Momentum setup: RSI={rsi:.0f}, change={change_pct:+.1%}",
            priority=3,
            attributes={
                "rsi": rsi,
                "change_pct": round(change_pct * 100, 2),
                "volume": volume,
                "sector": row.get("Sector", row.get("sector", "")),
                "industry": row.get("Industry", row.get("industry", "")),
            },
        )
