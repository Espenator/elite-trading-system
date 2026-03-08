"""CorrelationBreakScout — cross-asset divergence detection, 60-second interval."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

DIVERGENCE_THRESHOLD = 0.75   # Correlation coefficient drop below this


class CorrelationBreakScout(BaseScout):
    """Detects cross-asset correlation breakdowns."""

    @property
    def name(self) -> str:
        return "correlation_break_scout"

    @property
    def interval(self) -> float:
        return 60.0

    async def scout(self) -> List[DiscoveryPayload]:
        payloads = []
        try:
            from app.services.correlation_radar import get_correlation_radar
            radar = get_correlation_radar()
            breaks = await radar.get_correlation_breaks(threshold=DIVERGENCE_THRESHOLD)
        except Exception as exc:
            logger.debug("CorrelationBreakScout: radar error: %s", exc)
            return []

        for brk in breaks or []:
            symbols = brk.get("symbols", [])
            if not symbols:
                continue
            corr = float(brk.get("correlation", 0))
            baseline = float(brk.get("baseline_correlation", 0))
            delta = baseline - corr
            direction = brk.get("direction", "neutral")
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=list(symbols)[:5],
                direction=direction,
                reasoning=(
                    f"Correlation break: {symbols} corr dropped from "
                    f"{baseline:.2f} to {corr:.2f} (delta={delta:.2f})"
                ),
                priority=3,
                metadata={"correlation": corr, "baseline": baseline, "delta": delta},
            ))
        return payloads
