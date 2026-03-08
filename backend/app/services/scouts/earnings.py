"""EarningsScout — Benzinga earnings calendar + drift detection, daily + event."""
import logging
from datetime import date, timedelta
from typing import List

from app.services.scouts.base import BaseScout, DiscoveryPayload

logger = logging.getLogger(__name__)

LOOKAHEAD_DAYS = 3     # Scan earnings within next 3 days
DRIFT_THRESHOLD = 0.03 # 3% post-earnings drift


class EarningsScout(BaseScout):
    """Monitors upcoming earnings and post-earnings drift opportunities."""

    @property
    def name(self) -> str:
        return "earnings_scout"

    @property
    def interval(self) -> float:
        return 3600.0  # Hourly — earnings don't change minute-to-minute

    async def scout(self) -> List[DiscoveryPayload]:
        payloads = []
        today = date.today()
        lookahead = today + timedelta(days=LOOKAHEAD_DAYS)

        try:
            from app.services.news_aggregator import get_news_aggregator
            agg = get_news_aggregator()
            calendar = await agg.get_earnings_calendar(
                from_date=today.isoformat(),
                to_date=lookahead.isoformat(),
            )
        except Exception as exc:
            logger.debug("EarningsScout: calendar fetch error: %s", exc)
            calendar = []

        for event in calendar or []:
            symbol = event.get("ticker", event.get("symbol", ""))
            if not symbol:
                continue
            eps_est = event.get("eps_estimate", event.get("eps_est"))
            report_date = event.get("report_date", event.get("date", ""))
            days_out = (
                (date.fromisoformat(report_date) - today).days
                if report_date else LOOKAHEAD_DAYS
            )
            priority = 2 if days_out <= 1 else 3
            payloads.append(DiscoveryPayload(
                source=self.name,
                symbols=[symbol],
                direction="neutral",
                reasoning=(
                    f"Earnings in {days_out}d: {symbol} "
                    + (f"EPS est={eps_est}" if eps_est is not None else "")
                ),
                priority=priority,
                metadata={"event": event, "days_out": days_out},
            ))
        return payloads
