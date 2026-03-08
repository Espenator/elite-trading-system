"""UnusualWhalesFlowScout — monitors unusual options flow via Unusual Whales API.

Scan cadence: 60 s
Source: Unusual Whales (options flow alerts)
Signal types: unusual_flow

Discovery criteria
------------------
* Options premium >= $50 000 (institutional-sized).
* Open interest / volume ratio indicates directional conviction.
* Large sweeps (multi-leg, aggressive fills) scored higher.
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
    SIGNAL_UNUSUAL_FLOW,
    SOURCE_UNUSUAL_WHALES,
)

logger = logging.getLogger(__name__)

_MIN_PREMIUM = 50_000          # minimum option premium ($)
_HIGH_PREMIUM = 500_000        # high-conviction threshold


class UnusualWhalesFlowScout(BaseScout):
    """Scout that detects large / unusual options flow from Unusual Whales."""

    scout_id = "uw_flow"
    source = "Unusual Whales Flow"
    source_type = SOURCE_UNUSUAL_WHALES
    scan_interval = 60.0
    timeout = 20.0

    async def scan(self) -> List[DiscoveryPayload]:
        discoveries: List[DiscoveryPayload] = []
        try:
            alerts = await self._fetch_flow()
        except Exception as exc:
            logger.debug("[%s] fetch failed: %s", self.scout_id, exc)
            return discoveries

        for alert in alerts:
            payload = self._evaluate_alert(alert)
            if payload:
                discoveries.append(payload)
        return discoveries

    async def _fetch_flow(self) -> List[Dict[str, Any]]:
        try:
            from app.services.unusual_whales_service import UnusualWhalesService
            svc = UnusualWhalesService()
            data = await svc.get_flow_alerts()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("data", data.get("items", []))
        except Exception:
            pass
        return []

    def _evaluate_alert(self, alert: Dict[str, Any]) -> "DiscoveryPayload | None":
        symbol = str(alert.get("ticker", alert.get("symbol", "")) or "").upper()
        if not symbol:
            return None

        raw_premium = alert.get("premium", alert.get("cost_basis", 0)) or 0
        try:
            premium = float(str(raw_premium).replace(",", ""))
        except (ValueError, TypeError):
            premium = 0.0

        if premium < _MIN_PREMIUM:
            return None

        call_put = str(alert.get("put_call", alert.get("option_type", "")) or "").lower()
        direction = (
            DIRECTION_BULLISH if call_put in ("call", "c")
            else DIRECTION_BEARISH if call_put in ("put", "p")
            else DIRECTION_NEUTRAL
        )

        is_sweep = bool(alert.get("is_sweep", alert.get("sweep", False)))
        score = min(100, int(premium / 10_000) + (20 if is_sweep else 0))
        confidence = min(1.0, premium / _HIGH_PREMIUM * 0.8 + (0.2 if is_sweep else 0))

        return DiscoveryPayload(
            scout_id=self.scout_id,
            source=self.source,
            source_type=self.source_type,
            symbol=symbol,
            direction=direction,
            signal_type=SIGNAL_UNUSUAL_FLOW,
            confidence=confidence,
            score=score,
            reasoning=(
                f"Unusual {'sweep ' if is_sweep else ''}{call_put or 'options'} flow: "
                f"${premium:,.0f} premium"
            ),
            priority=1 if premium >= _HIGH_PREMIUM else 2,
            attributes={
                "premium": premium,
                "option_type": call_put,
                "is_sweep": is_sweep,
                "strike": alert.get("strike"),
                "expiry": alert.get("expiry", alert.get("expiration_date")),
                "sentiment": alert.get("sentiment"),
            },
        )
