"""FlowHunterScout — UW options flow, 15-second interval."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)


class FlowHunterScout(BaseScout):
    """Monitors unusual options flow via UnusualWhales every 15 s."""

    @property
    def name(self) -> str:
        return "flow_hunter_scout"

    @property
    def interval(self) -> float:
        return 15.0

    async def scout(self) -> List[DiscoveryPayload]:
        try:
            from app.services.unusual_whales_service import get_unusual_whales_service
            svc = get_unusual_whales_service()
            alerts = await svc.get_top_flow_alerts(limit=10)
        except Exception as exc:
            logger.debug("FlowHunterScout: data fetch error: %s", exc)
            return []

        payloads = []
        for alert in alerts or []:
            symbol = alert.get("ticker", alert.get("symbol", ""))
            if not symbol:
                continue
            premium = float(alert.get("premium", alert.get("total_premium", 0)))
            side = alert.get("put_call", "").lower()
            direction = "bullish" if side == "call" else "bearish" if side == "put" else "neutral"
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=[symbol],
                direction=direction,
                reasoning=(
                    f"Unusual options flow detected: {symbol} {side.upper()} "
                    f"premium=${premium:,.0f}"
                ),
                priority=2,
                metadata={"flow_alert": alert, "premium": premium},
            ))
        return payloads
