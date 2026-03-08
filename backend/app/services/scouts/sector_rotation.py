"""SectorRotationScout — sector ETF flow, 30-second interval."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

SECTOR_ETFS = [
    "XLK", "XLF", "XLE", "XLV", "XLI",
    "XLP", "XLY", "XLU", "XLRE", "XLB", "XLC",
]
ROTATION_THRESHOLD = 0.008  # 0.8% divergence signals rotation


class SectorRotationScout(BaseScout):
    """Detects sector ETF rotation patterns in real-time."""

    @property
    def name(self) -> str:
        return "sector_rotation_scout"

    @property
    def interval(self) -> float:
        return 30.0

    async def scout(self) -> List[DiscoveryPayload]:
        payloads = []
        try:
            from app.services.correlation_radar import get_correlation_radar
            radar = get_correlation_radar()
            divergences = await radar.get_sector_divergences(symbols=SECTOR_ETFS)
        except Exception as exc:
            logger.debug("SectorRotationScout: radar error: %s", exc)
            return []

        for div in divergences or []:
            symbol = div.get("symbol", "")
            magnitude = float(div.get("divergence", div.get("magnitude", 0)))
            if not symbol or abs(magnitude) < ROTATION_THRESHOLD:
                continue
            direction = "bullish" if magnitude > 0 else "bearish"
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=[symbol],
                direction=direction,
                reasoning=(
                    f"Sector rotation: {symbol} divergence={magnitude:.3f} "
                    f"({'inflow' if magnitude > 0 else 'outflow'})"
                ),
                priority=3,
                metadata={"divergence": magnitude, "sector": symbol},
            ))
        return payloads
