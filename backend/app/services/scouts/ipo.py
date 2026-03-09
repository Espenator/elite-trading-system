"""IPOScout — new listings entering the universe, daily interval."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

MIN_IPO_MARKET_CAP = 500_000_000  # $500M minimum to avoid micro-caps


class IPOScout(BaseScout):
    """Monitors new IPOs and recent listings."""

    @property
    def name(self) -> str:
        return "ipo_scout"

    @property
    def interval(self) -> float:
        return 86_400.0  # Daily

    async def scout(self) -> List[DiscoveryPayload]:
        payloads = []
        try:
            from app.services.finviz_service import get_finviz_service
            svc = get_finviz_service()
            ipos = await svc.get_recent_ipos(days_back=7, limit=20)
        except Exception as exc:
            logger.debug("IPOScout: fetch error: %s", exc)
            return []

        for ipo in ipos or []:
            symbol = ipo.get("ticker", ipo.get("symbol", ""))
            if not symbol:
                continue
            market_cap = float(ipo.get("market_cap", 0))
            if market_cap < MIN_IPO_MARKET_CAP:
                continue
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=[symbol],
                direction="neutral",
                reasoning=(
                    f"New IPO/listing: {symbol} "
                    f"market_cap=${market_cap:,.0f} "
                    + (f"(IPO date: {ipo.get('ipo_date', 'recent')})")
                ),
                priority=3,
                metadata={"ipo": ipo, "market_cap": market_cap},
            ))
        return payloads
