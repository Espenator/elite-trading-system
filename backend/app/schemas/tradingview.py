"""TradingView webhook payload schemas.

Used by POST /api/v1/webhooks/tradingview to validate and parse alert payloads.
All credentials (e.g. secret) are validated against config/env only; never hardcoded.
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class TradingViewAlertMeta(BaseModel):
    """Optional metadata from TradingView (exchange, alert name, etc.)."""

    model_config = ConfigDict(extra="allow")

    exchange: Optional[str] = None
    alert_name: Optional[str] = None


class TradingViewWebhookPayload(BaseModel):
    """Full TradingView webhook payload shape.

    Supports both minimal (ticker/action/price) and full payloads.
    Secret is validated server-side against TRADINGVIEW_WEBHOOK_SECRET.
    """

    secret: Optional[str] = Field(None, description="Shared secret; validated against env")
    symbol: Optional[str] = Field(None, description="Ticker symbol (e.g. AAPL)")
    ticker: Optional[str] = Field(None, description="Alias for symbol")
    action: Optional[str] = Field(None, description="BUY, SELL, or LONG, SHORT")
    side: Optional[str] = Field(None, description="Alias for action")
    timeframe: Optional[str] = Field("1d", description="Chart timeframe (e.g. 5m, 1d)")
    price: Optional[float] = Field(None, description="Price at alert time")
    close: Optional[float] = Field(None, description="Alias for price")
    strategy: Optional[str] = Field(None, description="Strategy name (e.g. EMA Cross)")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of alert")
    order_type: Optional[str] = Field("market", description="market, limit, etc.")
    qty: Optional[int] = Field(None, ge=0, description="Optional quantity override")
    mode: Optional[str] = Field(
        "council",
        description="council = route through council; direct_execution = testing only",
    )
    meta: Optional[TradingViewAlertMeta] = None
    message: Optional[str] = None
    exchange: Optional[str] = None
    volume: Optional[float] = None

    def resolved_symbol(self) -> str:
        """Return normalized symbol (ticker or symbol)."""
        s = (self.symbol or self.ticker or "").strip().upper()
        return s or ""

    def resolved_action(self) -> str:
        """Return normalized action (buy, sell, or hold)."""
        a = (self.action or self.side or "").strip().upper()
        if a in ("BUY", "LONG"):
            return "buy"
        if a in ("SELL", "SHORT"):
            return "sell"
        return "hold"

    def resolved_price(self) -> float:
        """Return price (price or close)."""
        p = self.price if self.price is not None else self.close
        return float(p) if p is not None else 0.0

    def resolved_timeframe(self) -> str:
        """Return timeframe with default."""
        t = (self.timeframe or "1d").strip()
        return t or "1d"

    def resolved_mode(self) -> str:
        """Return mode: council or direct_execution."""
        m = (self.mode or "council").strip().lower()
        return m if m in ("council", "direct_execution") else "council"
