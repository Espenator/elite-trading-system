"""
Logs API — system activity logs (stub until logging pipeline is wired).
GET /api/v1/logs returns recent activity for Operator Console / debugging.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_logs(limit: int = 100):
    """Return recent system logs. Used by Operator Console. Fields: ts, level, message, source, agent, type (for filter)."""
    raw = [
        {
            "ts": "2024-02-18T14:32:15Z",
            "level": "info",
            "message": "BUY signal generated",
            "source": "signals",
            "agent": "SignalAgent",
            "type": "signal",
            "ticker": "NVDA",
            "confidence": 0.87,
            "pnlImpact": "+$2,450",
        },
        {
            "ts": "2024-02-18T14:32:14Z",
            "level": "info",
            "message": "Position size approved",
            "source": "agents",
            "agent": "RiskAgent",
            "type": "risk",
            "ticker": "NVDA",
            "confidence": 0.92,
            "pnlImpact": "Risk: $500 max",
        },
        {
            "ts": "2024-02-18T14:32:12Z",
            "level": "info",
            "message": "Pattern detected: Bull Flag",
            "source": "signals",
            "agent": "MLAgent",
            "type": "ml",
            "ticker": "NVDA",
            "confidence": 0.84,
            "pnlImpact": "Hist. win rate: 72%",
        },
        {
            "ts": "2024-02-18T14:31:58Z",
            "level": "info",
            "message": "Unusual volume spike",
            "source": "data-sources",
            "agent": "DataAgent",
            "type": "data",
            "ticker": "AAPL",
            "confidence": 0.78,
            "pnlImpact": "Watching...",
        },
        {
            "ts": "2024-02-18T14:31:45Z",
            "level": "info",
            "message": "Bullish sentiment surge",
            "source": "sentiment",
            "agent": "SentimentAgent",
            "type": "sentiment",
            "ticker": "TSLA",
            "confidence": 0.81,
            "pnlImpact": "+15% sentiment",
        },
        {
            "ts": "2024-02-18T14:00:00Z",
            "level": "info",
            "message": "Signal batch completed",
            "source": "signals",
            "agent": "SignalAgent",
            "type": "signal",
            "ticker": None,
            "confidence": None,
            "pnlImpact": "142 signals",
        },
        {
            "ts": "2024-02-18T13:58:00Z",
            "level": "info",
            "message": "Agent Market Data Agent started",
            "source": "agents",
            "agent": "Market Data Agent",
            "type": "risk",
            "ticker": None,
            "confidence": None,
            "pnlImpact": "—",
        },
        {
            "ts": "2024-02-18T13:55:00Z",
            "level": "warning",
            "message": "Data source SEC EDGAR latency high",
            "source": "data-sources",
            "agent": "DataAgent",
            "type": "data",
            "ticker": None,
            "confidence": None,
            "pnlImpact": "2.1s",
        },
    ]
    for r in raw:
        r.setdefault("agent", r.get("source", "system"))
        r.setdefault(
            "type",
            (
                "signal"
                if r["source"] == "signals"
                else "risk" if r["source"] == "agents" else "data"
            ),
        )
        r.setdefault("ticker", None)
        r.setdefault("confidence", None)
        r.setdefault("pnlImpact", "—")
    return {"logs": raw[:limit]}
