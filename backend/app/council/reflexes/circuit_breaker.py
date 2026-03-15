"""Circuit Breaker — brainstem reflexes that run BEFORE the council DAG.

These are fast (<50ms) safety checks that can halt trading instantly.
If any check fires, the council is skipped entirely and a HOLD is returned.

Thresholds are loaded from agent_config (settings service / directives).

Issue #70: Added live SPY price monitoring via Alpaca snapshots and
VIX approximation from SPY ATR. SPY drawdown detector trips if SPY
drops >5% in the current session.
"""
import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

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

# Issue #70: SPY/VIX monitoring cache (avoids hammering Alpaca on every signal)
_spy_vix_cache: Dict[str, Any] = {
    "spy_price": 0.0,
    "spy_prev_close": 0.0,
    "spy_change_pct": 0.0,
    "vix_estimate": 0.0,
    "timestamp": 0.0,
}
_SPY_VIX_CACHE_TTL = 30.0  # seconds


async def _fetch_spy_vix_data() -> Dict[str, Any]:
    """Fetch live SPY snapshot from Alpaca to compute price change and VIX estimate.

    Uses Alpaca Market Data API (works 24/7). Caches for 30 seconds.
    VIX is approximated from SPY daily range (ATR proxy) when no direct VIX feed.

    Returns dict with spy_price, spy_prev_close, spy_change_pct, vix_estimate.
    """
    global _spy_vix_cache
    now = time.time()
    if now - _spy_vix_cache["timestamp"] < _SPY_VIX_CACHE_TTL and _spy_vix_cache["spy_price"] > 0:
        return _spy_vix_cache

    try:
        from app.services.alpaca_service import alpaca_service
        snapshots = await alpaca_service.get_snapshots(["SPY"])
        if not snapshots or "SPY" not in snapshots:
            return _spy_vix_cache

        snap = snapshots["SPY"]
        daily_bar = snap.get("dailyBar") or {}
        prev_daily = snap.get("prevDailyBar") or {}
        latest_trade = snap.get("latestTrade") or {}

        spy_price = float(latest_trade.get("p", 0)) or float(daily_bar.get("c", 0))
        spy_prev_close = float(prev_daily.get("c", 0))

        if spy_price > 0 and spy_prev_close > 0:
            spy_change_pct = (spy_price - spy_prev_close) / spy_prev_close
        else:
            spy_change_pct = 0.0

        # VIX approximation: annualized ATR as % of price
        # Daily range / price * sqrt(252) gives a rough implied vol estimate
        high = float(daily_bar.get("h", 0))
        low = float(daily_bar.get("l", 0))
        if high > 0 and low > 0 and spy_price > 0:
            daily_range_pct = (high - low) / spy_price
            # Annualize: multiply by sqrt(252) * 100 for VIX-like scale
            vix_estimate = daily_range_pct * 15.87 * 100  # sqrt(252) ~ 15.87
        else:
            vix_estimate = 0.0

        _spy_vix_cache = {
            "spy_price": spy_price,
            "spy_prev_close": spy_prev_close,
            "spy_change_pct": spy_change_pct,
            "vix_estimate": vix_estimate,
            "timestamp": now,
        }
        return _spy_vix_cache

    except Exception as e:
        logger.debug("SPY/VIX data fetch failed (non-fatal): %s", e)
        return _spy_vix_cache


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
            self.spy_drawdown_detector(blackboard),  # Issue #70: live SPY monitoring
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
        """Detect VIX above panic threshold.

        Issue #70: Now checks both blackboard features AND live Alpaca SPY data.
        If no direct VIX feed is available, uses SPY ATR-based VIX estimate.
        """
        thresholds = _get_thresholds()
        f = blackboard.raw_features.get("features", blackboard.raw_features)
        raw = blackboard.raw_features

        # Check blackboard features first (may have real VIX from data feeds)
        vix = f.get("vix_close", 0) or f.get("vix", 0) or raw.get("vix", 0)

        # Issue #70: If no VIX from features, use live SPY ATR-based estimate
        if not vix or vix == 0:
            try:
                spy_data = await _fetch_spy_vix_data()
                vix = spy_data.get("vix_estimate", 0)
            except Exception:
                pass

        if vix and vix > thresholds["cb_vix_spike_threshold"]:
            return f"VIX spike: {vix:.1f} exceeds {thresholds['cb_vix_spike_threshold']:.0f} threshold"
        return None

    async def spy_drawdown_detector(self, blackboard: BlackboardState) -> Optional[str]:
        """Issue #70: Detect SPY drawdown exceeding flash crash threshold.

        Trips the circuit breaker if SPY drops more than 5% from previous close
        using live Alpaca snapshot data. This catches broad market selloffs
        that individual stock features might miss.
        """
        thresholds = _get_thresholds()
        threshold = thresholds["cb_flash_crash_threshold"]  # default 5%

        try:
            spy_data = await _fetch_spy_vix_data()
            spy_change = spy_data.get("spy_change_pct", 0)

            # Only trigger on drops (negative change exceeding threshold)
            if spy_change < -threshold:
                return (
                    f"SPY drawdown detected: {spy_change:.1%} drop from previous close "
                    f"exceeds {threshold:.0%} threshold"
                )
        except Exception:
            pass  # Alpaca unavailable — don't block trading

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
        """Check if we're in an active trading session.

        24/7 mode: no session blocks trading. Orders submitted on weekends
        will queue at Alpaca until Monday market open.
        All sessions are active for intelligence and order submission.
        """
        # 24/7 mode — never block. Weekend orders queue at broker.
        return None

    def get_session_position_limit(self) -> float:
        """Return session-aware position sizing limit as fraction of max.

        24/7 mode: all sessions allow trading. Weekend orders queue
        at Alpaca until next market open.
          REGULAR:     1.0  (100% of normal position size)
          PRE_MARKET:  0.75 (75% — thinner liquidity)
          AFTER_HOURS: 0.75 (75% — thinner liquidity)
          OVERNIGHT:   0.50 (50% — minimal liquidity)
          WEEKEND:     0.50 (50% — orders queue until Monday open)
        """
        from app.services.data_swarm.session_clock import get_session_clock, TradingSession
        session = get_session_clock().get_current_session()
        _limits = {
            TradingSession.REGULAR: 1.0,
            TradingSession.PRE_MARKET: 0.75,
            TradingSession.AFTER_HOURS: 0.75,
            TradingSession.OVERNIGHT: 0.50,
            TradingSession.WEEKEND: 0.50,
        }
        return _limits.get(session, 0.5)


# Global singleton
circuit_breaker = CircuitBreaker()
