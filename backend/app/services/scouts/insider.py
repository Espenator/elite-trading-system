"""InsiderScout — SEC EDGAR + UW insider buys > $100K, 60-second interval."""
import logging
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

MIN_INSIDER_VALUE = 100_000  # $100K threshold


class InsiderScout(BaseScout):
    """Monitors SEC EDGAR and UW for insider transactions > $100 K."""

    @property
    def name(self) -> str:
        return "insider_scout"

    @property
    def interval(self) -> float:
        return 60.0

    async def scout(self) -> List[DiscoveryPayload]:
        payloads = []
        try:
            from app.services.sec_edgar_service import get_edgar_service
            svc = get_edgar_service()
            filings = await svc.get_recent_insider_transactions(limit=20)
        except Exception as exc:
            logger.debug("InsiderScout: EDGAR fetch error: %s", exc)
            return []

        for filing in filings or []:
            symbol = filing.get("ticker", filing.get("symbol", ""))
            value = float(filing.get("transaction_value", filing.get("value", 0)))
            if not symbol or value < MIN_INSIDER_VALUE:
                continue
            tx_type = filing.get("transaction_type", filing.get("type", "")).lower()
            direction = "bullish" if "buy" in tx_type or "purchase" in tx_type else "bearish"
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=[symbol],
                direction=direction,
                reasoning=(
                    f"Insider {tx_type}: {symbol} valued at ${value:,.0f} "
                    f"by {filing.get('insider_name', 'insider')}"
                ),
                priority=1,  # Insider buys are historically strong signals
                metadata={"filing": filing, "value": value},
            ))
        return payloads
