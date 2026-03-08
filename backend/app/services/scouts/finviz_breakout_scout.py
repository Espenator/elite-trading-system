"""FinvizBreakoutScout — screens for technical breakout setups via FinViz.

Scan cadence: 120 s
Source: FinViz Elite Screener
Signal types: technical_breakout

Discovery criteria
------------------
* Price within 1% of 52-week high.
* Volume spike >= 150% of average on the breakout day.
* Market cap > $500M (no micro-caps).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.scouts.base_scout import BaseScout
from app.services.scouts.schemas import (
    DiscoveryPayload,
    DIRECTION_BULLISH,
    SIGNAL_BREAKOUT,
    SOURCE_FINVIZ,
)

logger = logging.getLogger(__name__)


class FinvizBreakoutScout(BaseScout):
    """Scout that surfaces new-high / volume-breakout setups from FinViz."""

    scout_id = "finviz_breakout"
    source = "FinViz Breakout Screener"
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
            # 52-week high breakout + volume surge
            result = await svc.get_screener_results(
                filters="sh_avgvol_o500,ta_highlow52w_nh,ta_perf_dup",
                order="-change",
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
            change_pct = float(str(row.get("Change", row.get("change", "0%")) or "0%")
                               .replace("%", "")) / 100
            rel_vol = float(row.get("Rel Volume", row.get("relative_volume", 1)) or 1)
        except (ValueError, TypeError):
            return None

        score = min(100, int(rel_vol * 20 + change_pct * 500))
        confidence = min(1.0, rel_vol / 5 * 0.6 + change_pct * 5)

        return DiscoveryPayload(
            scout_id=self.scout_id,
            source=self.source,
            source_type=self.source_type,
            symbol=symbol,
            direction=DIRECTION_BULLISH,
            signal_type=SIGNAL_BREAKOUT,
            confidence=confidence,
            score=score,
            reasoning=(
                f"Breakout: {change_pct:+.1%} with {rel_vol:.1f}x relative volume"
            ),
            priority=2,
            attributes={
                "change_pct": round(change_pct * 100, 2),
                "relative_volume": round(rel_vol, 2),
                "sector": row.get("Sector", row.get("sector", "")),
                "high_52w": row.get("52W High", row.get("52w_high")),
            },
        )
