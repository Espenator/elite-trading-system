"""Circuit Breaker — brainstem reflexes that run BEFORE the council DAG.

These are fast (<50ms) safety checks that can halt trading instantly.
If any check fires, the council is skipped entirely and a HOLD is returned.

Thresholds are loaded from agent_config (settings service / directives).
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.council.blackboard import BlackboardState

logger = logging.getLogger(__name__)

# Default thresholds (overridden by directives/settings)
_DEFAULTS = {
    "cb_vix_spike_threshold": 35.0,
    "cb_daily_drawdown_limit": 0.03,  # 3%
    "cb_flash_crash_threshold": 0.05,  # 5% in 5min
    "cb_max_positions": 10,
    "cb_max_single_position_pct": 0.20,  # 20%
}


def _get_thresholds() -> dict:
    """Load circuit breaker thresholds from settings, falling back to defaults."""
    try:
        from app.council.agent_config import get_agent_thresholds
        cfg = get_agent_thresholds()
        return {k: cfg.get(k, v) for k, v in _DEFAULTS.items()}
    except Exception:
        return _DEFAULTS.copy()


class CircuitBreaker:
    """Brainstem-level safety checks. Runs in <50ms before the council DAG."""

    async def check_all(self, blackboard: BlackboardState) -> Optional[str]:
        """Run all circuit breaker checks in parallel.

        Returns:
            Halt reason string if any reflex fires, None if safe to proceed.
        """
        checks = [
            self.flash_crash_detector(blackboard),
            self.vix_spike_detector(blackboard),
            self.daily_drawdown_limit(blackboard),
            self.position_limit_check(blackboard),
            self.single_position_check(blackboard),
            self.market_hours_check(blackboard),
        ]
        results = await asyncio.gather(*checks)
        for reason in results:
            if reason:
                logger.warning("Circuit breaker FIRED: %s", reason)
                return reason
        return None

    async def flash_crash_detector(self, blackboard: BlackboardState) -> Optional[str]:
        """Detect rapid price drops (>5% in 5min equivalent)."""
        thresholds = _get_thresholds()
        f = blackboard.raw_features.get("features", blackboard.raw_features)
        threshold = thresholds["cb_flash_crash_threshold"]
        # Prefer intraday returns if available for true flash crash detection
        intraday_ret = f.get("return_5min") or f.get("return_15min") or f.get("return_1h")
        if intraday_ret is not None:
            ret = abs(intraday_ret)
            if ret > threshold:
                return f"Flash crash detected: {ret:.1%} intraday move exceeds {threshold:.0%} threshold"
        else:
            # Fallback to daily return with a higher threshold
            ret_1d = abs(f.get("return_1d", 0))
            if ret_1d > threshold * 1.5:
                return f"Daily price collapse: {ret_1d:.1%} exceeds {threshold * 1.5:.0%} threshold"
        return None

    async def vix_spike_detector(self, blackboard: BlackboardState) -> Optional[str]:
        """Detect VIX above panic threshold."""
        thresholds = _get_thresholds()
        f = blackboard.raw_features.get("features", blackboard.raw_features)
        vix = f.get("vix_close", 0) or f.get("vix", 0)
        if vix > thresholds["cb_vix_spike_threshold"]:
            return f"VIX spike: {vix:.1f} exceeds {thresholds['cb_vix_spike_threshold']:.0f} threshold"
        return None

    async def daily_drawdown_limit(self, blackboard: BlackboardState) -> Optional[str]:
        """Check if daily drawdown limit has been breached."""
        thresholds = _get_thresholds()
        try:
            from app.api.v1.risk import drawdown_check_status
            dd = await drawdown_check_status()
            if dd.get("drawdown_breached"):
                return f"Daily drawdown limit breached ({thresholds['cb_daily_drawdown_limit']:.0%})"
            daily_pnl_pct = dd.get("daily_pnl_pct", 0)
            if daily_pnl_pct < -thresholds["cb_daily_drawdown_limit"]:
                return f"Daily PnL {daily_pnl_pct:.2%} below -{thresholds['cb_daily_drawdown_limit']:.0%} limit"
        except Exception:
            pass  # Risk API unavailable — don't block
        return None

    async def position_limit_check(self, blackboard: BlackboardState) -> Optional[str]:
        """Check if position count exceeds maximum."""
        thresholds = _get_thresholds()
        try:
            from app.services.alpaca_service import alpaca_service
            positions = await alpaca_service.get_positions()
            if len(positions) >= thresholds["cb_max_positions"]:
                return f"Position limit reached: {len(positions)}/{thresholds['cb_max_positions']} positions"
        except Exception:
            pass  # Alpaca unavailable — don't block
        return None

    async def single_position_check(self, blackboard: BlackboardState) -> Optional[str]:
        """Check if any single position exceeds maximum percentage of portfolio."""
        thresholds = _get_thresholds()
        try:
            from app.services.alpaca_service import alpaca_service
            positions = await alpaca_service.get_positions()
            account = await alpaca_service.get_account()

            if not positions or not account:
                return None

            equity = float(account.get("equity", 0))
            if equity <= 0:
                return None

            max_pct = thresholds["cb_max_single_position_pct"]

            for pos in positions:
                market_value = abs(float(pos.get("market_value", 0)))
                pos_pct = market_value / equity
                if pos_pct > max_pct:
                    symbol = pos.get("symbol", "UNKNOWN")
                    return f"Single position limit exceeded: {symbol} is {pos_pct:.1%} of portfolio (max {max_pct:.0%})"
        except Exception:
            pass  # Alpaca unavailable — don't block
        return None

    async def market_hours_check(self, blackboard: BlackboardState) -> Optional[str]:
        """Check if market is currently open (basic US hours check)."""
        now = datetime.now(timezone.utc)
        # US market hours: 9:30 AM - 4:00 PM ET = 14:30 - 21:00 UTC
        # Allow pre-market from 13:00 UTC (8 AM ET)
        hour = now.hour
        weekday = now.weekday()  # 0=Mon, 6=Sun

        if weekday >= 5:
            return "Market closed: weekend"

        # Allow extended hours (pre-market + after-hours)
        # Only block obvious off-hours (midnight to 8 AM ET)
        if hour < 13 or hour >= 22:
            return f"Market closed: off-hours (UTC hour={hour})"

        return None


# Global singleton
circuit_breaker = CircuitBreaker()
