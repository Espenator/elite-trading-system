"""CongressScout — UW congressional trades, 300-second interval."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)


class CongressScout(BaseScout):
    """Monitors congressional trade disclosures via UnusualWhales."""

    @property
    def name(self) -> str:
        return "congress_scout"

    @property
    def interval(self) -> float:
        return 300.0

    async def scout(self) -> List[DiscoveryPayload]:
        try:
            from app.services.unusual_whales_service import get_unusual_whales_service
            svc = get_unusual_whales_service()
            trades = await svc.get_congressional_trades(limit=10)
        except Exception as exc:
            logger.debug("CongressScout: fetch error: %s", exc)
            return []

        payloads = []
        for trade in trades or []:
            symbol = trade.get("ticker", trade.get("symbol", ""))
            if not symbol:
                continue
            tx_type = trade.get("transaction_type", trade.get("type", "")).lower()
            direction = "bullish" if "buy" in tx_type or "purchase" in tx_type else "bearish"
            member = trade.get("representative", trade.get("name", "official"))
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=[symbol],
                direction=direction,
                reasoning=f"Congressional {tx_type} of {symbol} by {member}",
                priority=2,
                metadata={"trade": trade},
            ))
        return payloads
