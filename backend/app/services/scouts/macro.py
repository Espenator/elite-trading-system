"""MacroScout — FRED + VIX regime shifts, 300-second interval."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

VIX_HIGH_THRESHOLD = 30.0    # Elevated fear
VIX_EXTREME_THRESHOLD = 40.0 # Extreme fear / potential capitulation


class MacroScout(BaseScout):
    """Monitors FRED macro data and VIX regime shifts."""

    @property
    def name(self) -> str:
        return "macro_scout"

    @property
    def interval(self) -> float:
        return 300.0

    async def scout(self) -> List[DiscoveryPayload]:
        payloads = []

        # VIX regime check
        try:
            from app.services.fred_service import get_fred_service
            fred = get_fred_service()
            macro = await fred.get_latest_macro_snapshot()
        except Exception as exc:
            logger.debug("MacroScout: FRED error: %s", exc)
            macro = {}

        vix = float(macro.get("vix", 0))
        if vix >= VIX_EXTREME_THRESHOLD:
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=["SPY", "QQQ", "VIX"],
                direction="bearish",
                reasoning=f"Extreme VIX={vix:.1f}: potential capitulation / systemic risk",
                priority=1,
                metadata={"vix": vix, "macro": macro},
            ))
        elif vix >= VIX_HIGH_THRESHOLD:
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=["SPY", "QQQ"],
                direction="bearish",
                reasoning=f"Elevated VIX={vix:.1f}: risk-off regime shift",
                priority=2,
                metadata={"vix": vix, "macro": macro},
            ))

        # Yield curve / macro data
        yield_10y = float(macro.get("treasury_10y", 0))
        yield_2y = float(macro.get("treasury_2y", 0))
        if yield_10y and yield_2y:
            spread = yield_10y - yield_2y
            if spread < 0:
                payloads.append(DiscoveryPayload(
                    source=self.name,
                    symbols=["TLT", "IEF", "XLF"],
                    direction="bearish",
                    reasoning=(
                        f"Yield curve inverted: 10y={yield_10y:.2f}% 2y={yield_2y:.2f}% "
                        f"spread={spread:.2f}%"
                    ),
                    priority=3,
                    metadata={"yield_10y": yield_10y, "yield_2y": yield_2y, "spread": spread},
                ))

        return payloads
