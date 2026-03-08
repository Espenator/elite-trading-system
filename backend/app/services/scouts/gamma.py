"""GammaScout — UW GEX levels and dynamic watchlist, 60-second interval."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

GEX_SIGNIFICANCE_THRESHOLD = 1_000_000  # $1M GEX threshold


class GammaScout(BaseScout):
    """Monitors GEX levels for gamma squeeze candidates."""

    @property
    def name(self) -> str:
        return "gamma_scout"

    @property
    def interval(self) -> float:
        return 60.0

    async def scout(self) -> List[DiscoveryPayload]:
        try:
            from app.services.unusual_whales_service import get_unusual_whales_service
            svc = get_unusual_whales_service()
            gex_data = await svc.get_gex_levels(limit=15)
        except Exception as exc:
            logger.debug("GammaScout: fetch error: %s", exc)
            return []

        payloads = []
        for entry in gex_data or []:
            symbol = entry.get("ticker", entry.get("symbol", ""))
            if not symbol:
                continue
            gex = float(entry.get("gex", entry.get("gamma_exposure", 0)))
            if abs(gex) < GEX_SIGNIFICANCE_THRESHOLD:
                continue
            direction = "bullish" if gex > 0 else "bearish"
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=[symbol],
                direction=direction,
                reasoning=(
                    f"GEX signal: {symbol} gamma exposure=${gex:,.0f} "
                    f"({'positive' if gex > 0 else 'negative'} GEX)"
                ),
                priority=2,
                metadata={"gex": gex, "entry": entry},
            ))
        return payloads
