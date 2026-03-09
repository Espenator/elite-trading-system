"""ShortSqueezeScout — short interest + rising volume detection, hourly."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

SHORT_FLOAT_THRESHOLD = 0.20  # ≥20% short float
VOLUME_SURGE_MULT = 2.0       # Volume 2× vs average


class ShortSqueezeScout(BaseScout):
    """Identifies high short-float stocks with rising volume."""

    @property
    def name(self) -> str:
        return "short_squeeze_scout"

    @property
    def interval(self) -> float:
        return 3600.0  # Hourly

    async def scout(self) -> List[DiscoveryPayload]:
        payloads = []
        try:
            from app.services.finviz_service import get_finviz_service
            svc = get_finviz_service()
            candidates = await svc.get_short_squeeze_candidates(
                min_short_float=SHORT_FLOAT_THRESHOLD,
                limit=15,
            )
        except Exception as exc:
            logger.debug("ShortSqueezeScout: fetch error: %s", exc)
            return []

        for cand in candidates or []:
            symbol = cand.get("ticker", cand.get("symbol", ""))
            if not symbol:
                continue
            short_float = float(cand.get("short_float", 0))
            vol_ratio = float(cand.get("volume_ratio", cand.get("relative_volume", 0)))
            if short_float < SHORT_FLOAT_THRESHOLD:
                continue
            priority = 2 if vol_ratio >= VOLUME_SURGE_MULT * 1.5 else 3
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=[symbol],
                direction="bullish",
                reasoning=(
                    f"Short squeeze candidate: {symbol} "
                    f"short_float={short_float:.1%} vol_ratio={vol_ratio:.1f}×"
                ),
                priority=priority,
                metadata={"short_float": short_float, "volume_ratio": vol_ratio},
            ))
        return payloads
