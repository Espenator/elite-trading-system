"""Circuit Breaker — brainstem reflexes that run BEFORE the council DAG.

These are fast (<50ms) safety checks that can halt trading instantly.
If any check fires, the council is skipped entirely and a HOLD is returned.

Evaluates: flash crash, VIX/volatility spike, daily drawdown limit,
position limit, market-hours check, data/connectivity sanity.

Thresholds are loaded from directives (global + regime overlay) via agent_config.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.council.blackboard import BlackboardState

logger = logging.getLogger(__name__)

# Default thresholds (overridden by directives / agent_config)
_DEFAULTS = {
    "cb_vix_spike_threshold": 35.0,
    "cb_daily_drawdown_limit": float(os.getenv("CB_DAILY_DRAWDOWN_LIMIT", "0.03")),
    "cb_flash_crash_threshold": 0.05,
    "cb_max_positions": 10,
    "cb_max_single_position_pct": 0.20,
    "cb_data_connectivity_min_sources_healthy": 1,  # at least 1 critical source (e.g. alpaca) not DEGRADED
}


def _get_thresholds() -> dict:
    """Load circuit breaker thresholds from directives/agent_config, falling back to defaults."""
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
            self.market_hours_check(blackboard),
            self.data_connectivity_sanity(blackboard),
        ]
        try:
            # Circuit breakers MUST complete within 5s — they're safety-critical
            results = await asyncio.wait_for(
                asyncio.gather(*checks, return_exceptions=True),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            logger.error("Circuit breaker check_all TIMED OUT — halting for safety")
            return "Circuit breaker timeout — halting as precaution"
        for reason in results:
            if isinstance(reason, Exception):
                logger.warning("Circuit breaker check raised: %s", reason)
                continue
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

    async def market_hours_check(self, blackboard: BlackboardState) -> Optional[str]:
        """Check if market is currently open (US/Eastern, handles DST)."""
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo
        now_et = datetime.now(ZoneInfo("America/New_York"))
        hour_et = now_et.hour
        weekday = now_et.weekday()  # 0=Mon, 6=Sun

        if weekday >= 5:
            return "Market closed: weekend"

        # Allow extended hours: pre-market 4 AM ET through after-hours 8 PM ET
        # Only block obvious off-hours (midnight to 4 AM ET, 8 PM to midnight ET)
        if hour_et < 4 or hour_et >= 20:
            return f"Market closed: off-hours (ET hour={hour_et})"

        return None

    async def data_connectivity_sanity(self, blackboard: BlackboardState) -> Optional[str]:
        """Require at least one critical data source (e.g. Alpaca) not DEGRADED.

        If the broker/data health registry reports DEGRADED for critical sources,
        halt to avoid trading on stale or failing data. Best-effort: if registry
        is unavailable, we do not block.
        """
        try:
            from app.services.data_source_health_registry import get_health
            health = get_health()
            sources = health.get("sources", [])
            critical_names = {"alpaca"}
            degraded = [
                s["name"] for s in sources
                if s.get("name") in critical_names and s.get("status") == "DEGRADED"
            ]
            if degraded:
                return (
                    f"Data/connectivity sanity: critical source(s) DEGRADED: {', '.join(degraded)}"
                )
        except Exception as e:
            logger.debug("Data connectivity check skipped: %s", e)
        return None


# Global singleton
circuit_breaker = CircuitBreaker()
