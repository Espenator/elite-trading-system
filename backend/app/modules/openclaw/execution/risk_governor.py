#!/usr/bin/env python3
"""
risk_governor.py — OpenClaw Real-Time Risk Governor v1.0

Central risk authority that gates EVERY order before execution.
Runs as a singleton; streaming_engine and auto_executor call
`RiskGovernor.approve(order)` before any Alpaca submission.

Checks performed (in order):
 1. Circuit breaker (daily P&L limit)
 2. Max exposure (60% of equity)
 3. Per-ticker concentration (5% cap)
 4. Sector concentration (3 positions max)
 5. Correlation guard (0.75 threshold)
 6. Regime gate (RED = no new longs)
 7. Drawdown velocity (rolling 30-min P&L)
 8. Daily trade count limit
 9. Position-level stop enforcement

If ANY check fails, the order is REJECTED with a reason string
and optionally published to Slack #oc-trade-desk.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field, asdict
from zoneinfo import ZoneInfo

logger = logging.getLogger("openclaw.risk_governor")
ET = ZoneInfo("America/New_York")


# ── Data Classes ─────────────────────────────────────────────

@dataclass
class RiskDecision:
    """Immutable result from the governor."""
    approved: bool
    ticker: str
    action: str           # BUY / SELL / SHORT
    requested_shares: int
    approved_shares: int  # may be reduced
    requested_value: float
    reason: str           # "APPROVED" or rejection reason
    checks_passed: list = field(default_factory=list)
    checks_failed: list = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(ET).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OrderRequest:
    """Incoming order to be validated."""
    ticker: str
    side: str             # "buy" | "sell" | "short"
    shares: int
    price: float          # limit price
    stop_loss: float = 0.0
    take_profit: float = 0.0
    composite_score: float = 0.0
    setup_type: str = ""
    sector: str = ""
    regime: str = "neutral"


# ── Risk Governor Singleton ──────────────────────────────────

class RiskGovernor:
    """
    Thread-safe risk governor. One instance per process.
    All public methods acquire the internal lock.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._state_lock = threading.Lock()

        # ── Load limits from config (import-safe) ──
        try:
            from app.core.config import settings as app_settings
            self.max_position_pct = getattr(app_settings, "MAX_SINGLE_POSITION", 0.05)
            self.max_deployed_pct = getattr(app_settings, "MAX_DEPLOYED_PCT", 0.60)
            self.max_daily_loss_pct = getattr(app_settings, "MAX_DAILY_LOSS_PCT", 2.0)
            self.max_portfolio_heat = getattr(app_settings, "MAX_PORTFOLIO_HEAT", 0.06)
            self.max_daily_trades = getattr(app_settings, "MAX_DAILY_TRADES", 10)
            self.max_positions_per_sector = getattr(app_settings, "MAX_POSITIONS_PER_SECTOR", 3)
            self.correlation_threshold = getattr(app_settings, "CORRELATION_THRESHOLD", 0.75)
            self.circuit_breaker_pct = getattr(app_settings, "CIRCUIT_BREAKER_THRESHOLD", -0.03)
        except ImportError:
            try:
                import config as cfg
                self.max_position_pct = cfg.MAX_POSITION_PCT        # 0.05
                self.max_deployed_pct = cfg.MAX_DEPLOYED_PCT         # 0.60
                self.max_daily_loss_pct = cfg.MAX_DAILY_LOSS_PCT     # 2.0
                self.max_portfolio_heat = cfg.MAX_PORTFOLIO_HEAT     # 0.06
                self.max_daily_trades = cfg.MAX_DAILY_TRADES         # 10
                self.max_positions_per_sector = cfg.MAX_POSITIONS_PER_SECTOR  # 3
                self.correlation_threshold = cfg.CORRELATION_THRESHOLD  # 0.75
                self.circuit_breaker_pct = cfg.CIRCUIT_BREAKER_THRESHOLD  # -0.03
            except ImportError:
                self.max_position_pct = 0.05
                self.max_deployed_pct = 0.60
                self.max_daily_loss_pct = 2.0
                self.max_portfolio_heat = 0.06
                self.max_daily_trades = 10
                self.max_positions_per_sector = 3
                self.correlation_threshold = 0.75
                self.circuit_breaker_pct = -0.03

        # ── Runtime state ──
        self.daily_trade_count = 0
        self.daily_pnl = 0.0
        self.trade_count_reset_date = datetime.now(ET).date()
        self.equity = 100_000.0  # updated from Alpaca on each call
        self.open_positions: dict = {}   # ticker -> {value, sector, entry_time}
        self.recent_pnl_window: list = []  # (timestamp, pnl_delta) for velocity
        self.rejection_log: list = []
        self._last_alpaca_sync = 0.0

        logger.info("RiskGovernor initialized | max_pos=%.0f%% max_deploy=%.0f%% "
                     "daily_loss=%.1f%% max_trades=%d",
                     self.max_position_pct * 100, self.max_deployed_pct * 100,
                     self.max_daily_loss_pct, self.max_daily_trades)

    # ── Public API ───────────────────────────────────────────

    def approve(self, order: OrderRequest) -> RiskDecision:
        """
        Main entry point. Returns RiskDecision with approved=True/False.
        Thread-safe.
        """
        with self._state_lock:
            self._maybe_reset_daily_counter()
            self._maybe_sync_alpaca()

            passed = []
            failed = []

            # 1. Circuit breaker
            ok, msg = self._check_circuit_breaker()
            (passed if ok else failed).append(msg)
            if not ok:
                return self._reject(order, msg, passed, failed)

            # 2. Max exposure
            ok, msg = self._check_max_exposure(order)
            (passed if ok else failed).append(msg)
            if not ok:
                return self._reject(order, msg, passed, failed)

            # 3. Per-ticker concentration
            ok, msg = self._check_ticker_concentration(order)
            (passed if ok else failed).append(msg)
            if not ok:
                return self._reject(order, msg, passed, failed)

            # 4. Sector concentration
            ok, msg = self._check_sector_concentration(order)
            (passed if ok else failed).append(msg)
            if not ok:
                return self._reject(order, msg, passed, failed)

            # 5. Correlation guard
            ok, msg = self._check_correlation(order)
            (passed if ok else failed).append(msg)
            if not ok:
                return self._reject(order, msg, passed, failed)

            # 6. Regime gate
            ok, msg = self._check_regime_gate(order)
            (passed if ok else failed).append(msg)
            if not ok:
                return self._reject(order, msg, passed, failed)

            # 7. Drawdown velocity
            ok, msg = self._check_drawdown_velocity()
            (passed if ok else failed).append(msg)
            if not ok:
                return self._reject(order, msg, passed, failed)

            # 8. Daily trade count
            ok, msg = self._check_daily_trade_count()
            (passed if ok else failed).append(msg)
            if not ok:
                return self._reject(order, msg, passed, failed)

            # 9. Stop-loss enforcement
            ok, msg = self._check_stop_enforcement(order)
            (passed if ok else failed).append(msg)
            if not ok:
                return self._reject(order, msg, passed, failed)

            # All checks passed
            self.daily_trade_count += 1
            approved_shares = self._calculate_approved_shares(order)

            decision = RiskDecision(
                approved=True,
                ticker=order.ticker,
                action=order.side.upper(),
                requested_shares=order.shares,
                approved_shares=approved_shares,
                requested_value=order.shares * order.price,
                reason="APPROVED",
                checks_passed=passed,
                checks_failed=[],
            )
            logger.info("APPROVED: %s %d shares of %s @ $%.2f | %d/%d trades today",
                         order.side.upper(), approved_shares, order.ticker,
                         order.price, self.daily_trade_count, self.max_daily_trades)
            return decision

    def record_fill(self, ticker: str, shares: int, price: float,
                    side: str, sector: str = "") -> None:
        """Record a filled order to update internal state."""
        with self._state_lock:
            value = shares * price
            if side.lower() in ("buy", "long"):
                self.open_positions[ticker] = {
                    "value": value, "shares": shares, "price": price,
                    "sector": sector, "entry_time": datetime.now(ET).isoformat(),
                }
            elif side.lower() in ("sell", "close"):
                self.open_positions.pop(ticker, None)
            logger.info("Recorded fill: %s %s %d @ $%.2f", side, ticker, shares, price)

    def record_pnl(self, pnl_delta: float) -> None:
        """Record incremental P&L for velocity tracking."""
        with self._state_lock:
            now = time.time()
            self.daily_pnl += pnl_delta
            self.recent_pnl_window.append((now, pnl_delta))
            # Keep only last 30 minutes
            cutoff = now - 1800
            self.recent_pnl_window = [
                (t, p) for t, p in self.recent_pnl_window if t > cutoff
            ]

    def get_status(self) -> dict:
        """Return current risk state for dashboard / Slack."""
        with self._state_lock:
            total_exposure = sum(p["value"] for p in self.open_positions.values())
            exposure_pct = (total_exposure / self.equity * 100) if self.equity > 0 else 0
            return {
                "equity": self.equity,
                "daily_pnl": round(self.daily_pnl, 2),
                "daily_pnl_pct": round(self.daily_pnl / self.equity * 100, 2) if self.equity else 0,
                "total_exposure": round(total_exposure, 2),
                "exposure_pct": round(exposure_pct, 1),
                "open_positions": len(self.open_positions),
                "daily_trades": self.daily_trade_count,
                "max_daily_trades": self.max_daily_trades,
                "circuit_breaker_ok": self.daily_pnl > (self.equity * self.circuit_breaker_pct),
                "positions": {t: p for t, p in self.open_positions.items()},
                "recent_rejections": self.rejection_log[-10:],
                "timestamp": datetime.now(ET).isoformat(),
            }

    # ── Check Implementations ────────────────────────────────

    def _check_circuit_breaker(self) -> tuple[bool, str]:
        threshold = self.equity * self.circuit_breaker_pct
        if self.daily_pnl <= threshold:
            return False, (f"CIRCUIT_BREAKER: Daily P&L ${self.daily_pnl:+.2f} "
                           f"breached {self.circuit_breaker_pct*100:.1f}% "
                           f"(${threshold:+.2f})")
        return True, "circuit_breaker: OK"

    def _check_max_exposure(self, order: OrderRequest) -> tuple[bool, str]:
        current = sum(p["value"] for p in self.open_positions.values())
        new_value = order.shares * order.price
        max_allowed = self.equity * self.max_deployed_pct
        if current + new_value > max_allowed:
            return False, (f"MAX_EXPOSURE: ${current + new_value:,.0f} would exceed "
                           f"${max_allowed:,.0f} ({self.max_deployed_pct*100:.0f}% of "
                           f"${self.equity:,.0f})")
        return True, f"exposure: ${current + new_value:,.0f} / ${max_allowed:,.0f}"

    def _check_ticker_concentration(self, order: OrderRequest) -> tuple[bool, str]:
        new_value = order.shares * order.price
        existing = self.open_positions.get(order.ticker, {}).get("value", 0)
        total = existing + new_value
        max_allowed = self.equity * self.max_position_pct
        if total > max_allowed:
            return False, (f"TICKER_CONCENTRATION: {order.ticker} "
                           f"${total:,.0f} > ${max_allowed:,.0f} "
                           f"({self.max_position_pct*100:.0f}% cap)")
        return True, f"ticker_conc: {order.ticker} ${total:,.0f} / ${max_allowed:,.0f}"

    def _check_sector_concentration(self, order: OrderRequest) -> tuple[bool, str]:
        if not order.sector:
            # Attempt sector lookup from static mapping
            try:
                from app.utils.sector_lookup import get_sector_or_none
                order.sector = get_sector_or_none(order.ticker)
            except Exception:
                pass
        if not order.sector:
            return True, "sector_conc: no sector data (skip)"
        count = sum(1 for p in self.open_positions.values()
                    if p.get("sector", "").lower() == order.sector.lower())
        if count >= self.max_positions_per_sector:
            return False, (f"SECTOR_CONCENTRATION: {order.sector} has "
                           f"{count}/{self.max_positions_per_sector} positions")
        return True, f"sector_conc: {order.sector} {count}/{self.max_positions_per_sector}"

    def _check_correlation(self, order: OrderRequest) -> tuple[bool, str]:
        # Lightweight check: same-sector positions count as correlated
        if not order.sector:
            try:
                from app.utils.sector_lookup import get_sector_or_none
                order.sector = get_sector_or_none(order.ticker)
            except Exception:
                pass
        if not order.sector:
            return True, "correlation: no sector (skip)"
        same_sector_value = sum(
            p["value"] for p in self.open_positions.values()
            if p.get("sector", "").lower() == order.sector.lower()
        )
        new_value = order.shares * order.price
        corr_limit = self.equity * 0.15  # 15% max correlated exposure
        if same_sector_value + new_value > corr_limit:
            return False, (f"CORRELATION: Correlated exposure in {order.sector} "
                           f"${same_sector_value + new_value:,.0f} > ${corr_limit:,.0f}")
        return True, f"correlation: {order.sector} ${same_sector_value + new_value:,.0f} / ${corr_limit:,.0f}"

    def _check_regime_gate(self, order: OrderRequest) -> tuple[bool, str]:
        regime = order.regime.upper() if order.regime else "NEUTRAL"
        if regime == "RED" and order.side.lower() in ("buy", "long"):
            return False, f"REGIME_GATE: RED regime — no new longs allowed"
        if regime == "RED" and order.side.lower() == "short":
            return True, "regime_gate: RED allows shorts"
        return True, f"regime_gate: {regime} OK"

    def _check_drawdown_velocity(self) -> tuple[bool, str]:
        if not self.recent_pnl_window:
            return True, "dd_velocity: no data (skip)"
        window_pnl = sum(p for _, p in self.recent_pnl_window)
        velocity_limit = self.equity * -0.01  # -1% in 30 min
        if window_pnl < velocity_limit:
            return False, (f"DRAWDOWN_VELOCITY: ${window_pnl:+.2f} in 30min "
                           f"exceeds ${velocity_limit:+.2f} limit")
        return True, f"dd_velocity: ${window_pnl:+.2f} / ${velocity_limit:+.2f}"

    def _check_daily_trade_count(self) -> tuple[bool, str]:
        if self.daily_trade_count >= self.max_daily_trades:
            return False, (f"DAILY_LIMIT: {self.daily_trade_count}/"
                           f"{self.max_daily_trades} trades exhausted")
        return True, f"trade_count: {self.daily_trade_count}/{self.max_daily_trades}"

    def _check_stop_enforcement(self, order: OrderRequest) -> tuple[bool, str]:
        if order.side.lower() in ("buy", "long") and order.stop_loss <= 0:
            return False, "STOP_REQUIRED: Every buy order MUST include a stop loss"
        if order.stop_loss > 0 and order.price > 0:
            stop_pct = abs(order.price - order.stop_loss) / order.price
            if stop_pct > 0.03:  # max 3% stop distance
                return False, (f"STOP_TOO_WIDE: {stop_pct:.1%} exceeds 3% max "
                               f"(entry=${order.price:.2f} stop=${order.stop_loss:.2f})")
        return True, "stop_enforcement: OK"

    # ── Helpers ───────────────────────────────────────────────

    def _reject(self, order: OrderRequest, reason: str,
                passed: list, failed: list) -> RiskDecision:
        decision = RiskDecision(
            approved=False,
            ticker=order.ticker,
            action=order.side.upper(),
            requested_shares=order.shares,
            approved_shares=0,
            requested_value=order.shares * order.price,
            reason=reason,
            checks_passed=passed,
            checks_failed=failed,
        )
        self.rejection_log.append({
            "ticker": order.ticker, "reason": reason,
            "time": datetime.now(ET).isoformat()
        })
        # Keep only last 100 rejections
        if len(self.rejection_log) > 100:
            self.rejection_log = self.rejection_log[-100:]
        logger.warning("REJECTED: %s %s — %s", order.side.upper(),
                        order.ticker, reason)
        return decision

    def _calculate_approved_shares(self, order: OrderRequest) -> int:
        """May reduce shares to stay within limits."""
        max_value = self.equity * self.max_position_pct
        existing = self.open_positions.get(order.ticker, {}).get("value", 0)
        available = max_value - existing
        max_shares_by_conc = int(available / order.price) if order.price > 0 else 0
        return min(order.shares, max_shares_by_conc) if max_shares_by_conc > 0 else order.shares

    def _maybe_reset_daily_counter(self) -> None:
        today = datetime.now(ET).date()
        if today != self.trade_count_reset_date:
            logger.info("New trading day — resetting counters")
            self.daily_trade_count = 0
            self.daily_pnl = 0.0
            self.recent_pnl_window.clear()
            self.trade_count_reset_date = today

    def _maybe_sync_alpaca(self) -> None:
        """Sync equity & positions from Alpaca every 60s.

        Uses asyncio.run_coroutine_threadsafe when called from a sync context
        while an event loop is running, or falls back to a direct httpx call.
        """
        now = time.time()
        if now - self._last_alpaca_sync < 60:
            return
        self._last_alpaca_sync = now
        try:
            import asyncio
            from app.services.alpaca_service import alpaca_service

            async def _sync():
                acct = await alpaca_service.get_account()
                positions = await alpaca_service.get_positions()
                return acct, positions

            # Run async code from sync context
            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(_sync(), loop)
                acct, positions = future.result(timeout=10)
            except RuntimeError:
                # No running loop — run directly
                acct, positions = asyncio.run(_sync())

            if acct:
                self.equity = float(acct.get("equity", self.equity))
            if positions:
                self.open_positions.clear()
                for p in positions:
                    sym = p.get("symbol", "")
                    self.open_positions[sym] = {
                        "value": abs(float(p.get("market_value", 0))),
                        "shares": int(p.get("qty", 0)),
                        "price": float(p.get("current_price", 0)),
                        "sector": p.get("sector", ""),
                        "entry_time": p.get("entry_time", ""),
                    }
                logger.debug("Synced %d positions from Alpaca, equity=$%.2f",
                             len(self.open_positions), self.equity)
        except Exception as e:
            logger.debug("Alpaca sync skipped: %s", e)


# ── Module-level convenience ─────────────────────────────────

_governor: Optional[RiskGovernor] = None

def get_governor() -> RiskGovernor:
    """Get or create the singleton RiskGovernor."""
    global _governor
    if _governor is None:
        _governor = RiskGovernor()
    return _governor

def approve_order(ticker: str, side: str, shares: int, price: float,
                  stop_loss: float = 0, composite_score: float = 0,
                  sector: str = "", regime: str = "neutral",
                  setup_type: str = "") -> RiskDecision:
    """Convenience function for quick approval checks."""
    order = OrderRequest(
        ticker=ticker, side=side, shares=shares, price=price,
        stop_loss=stop_loss, composite_score=composite_score,
        sector=sector, regime=regime, setup_type=setup_type,
    )
    return get_governor().approve(order)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    gov = get_governor()
    print("\n=== Risk Governor Self-Test ===")
    # Test 1: Valid order
    d = approve_order("AAPL", "buy", 25, 195.0, stop_loss=192.0,
                      composite_score=82, sector="Technology", regime="green")
    print(f"Test 1 (valid):   {d.reason}")
    # Test 2: No stop loss
    d = approve_order("MSFT", "buy", 10, 420.0, stop_loss=0)
    print(f"Test 2 (no stop): {d.reason}")
    # Test 3: RED regime long
    d = approve_order("TSLA", "buy", 5, 250.0, stop_loss=246.0, regime="red")
    print(f"Test 3 (red buy): {d.reason}")
    # Print status
    print(f"\nStatus: {json.dumps(gov.get_status(), indent=2)}")
