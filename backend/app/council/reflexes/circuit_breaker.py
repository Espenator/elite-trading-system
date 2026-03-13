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
    "cb_daily_drawdown_limit": float(os.getenv("CB_DAILY_DRAWDOWN_LIMIT", "0.03")),  # 3% default, configurable
    "cb_flash_crash_threshold": 0.05,  # 5% in 5min
    "cb_max_positions": 10,
    "cb_max_single_position_pct": 0.20,  # 20%
}


def _get_thresholds() -> dict:
    """Load circuit breaker thresholds from directives/global.md when available, else agent_config, else defaults."""
    out = _DEFAULTS.copy()
    # Prefer directives/global.md (canonical source)
    try:
        from app.council.directives.loader import directive_loader
        vix = directive_loader.get_threshold("VIX spike threshold")
        if vix is not None:
            out["cb_vix_spike_threshold"] = float(vix)
        dd = directive_loader.get_threshold("Daily drawdown limit")
        if dd is not None:
            out["cb_daily_drawdown_limit"] = float(dd)
        fc = directive_loader.get_threshold("Flash crash threshold")
        if fc is not None:
            out["cb_flash_crash_threshold"] = float(fc)
        max_pos = directive_loader.get_threshold("Max positions")
        if max_pos is not None:
            out["cb_max_positions"] = int(max_pos)
        max_single = directive_loader.get_threshold("Max single position")
        if max_single is not None:
            out["cb_max_single_position_pct"] = float(max_single)
    except Exception:
        pass
    # Override with agent_config / settings if available
    try:
        from app.council.agent_config import get_agent_thresholds
        cfg = get_agent_thresholds()
        for k, v in _DEFAULTS.items():
            if k in cfg:
                out[k] = cfg[k]
    except Exception:
        pass
    return out


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
        # Also check top-level raw_features for price_change_5min (alias for 5min move)
        raw = blackboard.raw_features
        threshold = thresholds["cb_flash_crash_threshold"]
        # Prefer intraday returns if available for true flash crash detection
        intraday_ret = (
            f.get("return_5min")
            or raw.get("price_change_5min")
            or f.get("return_15min")
            or f.get("return_1h")
        )
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
        raw = blackboard.raw_features
        vix = f.get("vix_close", 0) or f.get("vix", 0) or raw.get("vix", 0)
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


# Global singleton
circuit_breaker = CircuitBreaker()
