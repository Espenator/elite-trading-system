"""Circuit Breaker — brainstem reflexes that run BEFORE the council DAG.

These are fast (<50ms) safety checks that can halt trading instantly.
If any check fires, the council is skipped entirely and a HOLD is returned.

Implemented Reflexes (9 total):
  1. Flash Crash Detector — Detects rapid price drops (>5% in 5min)
  2. VIX Spike Detector — Detects panic volatility (VIX > 35)
  3. Daily Drawdown Limit — Enforces max 3% daily loss
  4. Position Limit Check — Prevents over-concentration (max 10 positions)
  5. Market Hours Check — Blocks trading outside market hours
  6. Liquidity Check — Ensures sufficient trading volume (>100k shares)
  7. Correlation Spike Detector — Detects market correlation breakdown
  8. Data Connection Health — Monitors critical data source freshness
  9. Profit Target Ceiling — Enforces daily profit taking (>10% gain)

Thresholds are loaded from agent_config (settings service / directives).
"""
import asyncio
import logging
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Optional, Dict, List

from app.council.blackboard import BlackboardState

logger = logging.getLogger(__name__)

# Default thresholds (overridden by directives/settings)
_DEFAULTS = {
    "cb_vix_spike_threshold": 35.0,
    "cb_daily_drawdown_limit": 0.03,  # 3%
    "cb_flash_crash_threshold": 0.05,  # 5% in 5min
    "cb_max_positions": 10,
    "cb_max_single_position_pct": 0.20,  # 20%
    "cb_min_volume": 100000,  # Minimum daily volume for trading
    "cb_correlation_spike_threshold": 0.95,  # Market correlation breakdown
    "cb_daily_profit_ceiling": 0.10,  # 10% daily profit target
    "cb_data_staleness_minutes": 30,  # Max data age before halt
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

    def __init__(self):
        """Initialize circuit breaker with metrics tracking."""
        # Metrics: track last 100 triggers per check type
        self._trigger_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._total_checks = 0
        self._total_triggers = 0
        self._last_trigger_time: Optional[datetime] = None
        self._last_trigger_reason: Optional[str] = None

    def _record_trigger(self, check_name: str, reason: str) -> None:
        """Record a circuit breaker trigger for metrics."""
        self._trigger_history[check_name].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        })
        self._total_triggers += 1
        self._last_trigger_time = datetime.now(timezone.utc)
        self._last_trigger_reason = reason

    def get_metrics(self) -> dict:
        """Get circuit breaker metrics and trigger history."""
        return {
            "total_checks": self._total_checks,
            "total_triggers": self._total_triggers,
            "trigger_rate": self._total_triggers / max(self._total_checks, 1),
            "last_trigger_time": self._last_trigger_time.isoformat() if self._last_trigger_time else None,
            "last_trigger_reason": self._last_trigger_reason,
            "trigger_history": {
                check_name: list(history)
                for check_name, history in self._trigger_history.items()
            },
            "checks_by_type": {
                check_name: len(history)
                for check_name, history in self._trigger_history.items()
            },
        }

    async def check_all(self, blackboard: BlackboardState) -> Optional[str]:
        """Run all circuit breaker checks in parallel.

        Returns:
            Halt reason string if any reflex fires, None if safe to proceed.
        """
        self._total_checks += 1

        check_names = [
            "flash_crash",
            "vix_spike",
            "daily_drawdown",
            "position_limit",
            "market_hours",
            "liquidity",
            "correlation_spike",
            "data_connection",
            "profit_ceiling",
        ]
        checks = [
            self.flash_crash_detector(blackboard),
            self.vix_spike_detector(blackboard),
            self.daily_drawdown_limit(blackboard),
            self.position_limit_check(blackboard),
            self.market_hours_check(blackboard),
            self.liquidity_check(blackboard),
            self.correlation_spike_detector(blackboard),
            self.data_connection_health(blackboard),
            self.profit_target_ceiling(blackboard),
        ]
        results = await asyncio.gather(*checks)

        for check_name, reason in zip(check_names, results):
            if reason:
                logger.warning("Circuit breaker FIRED: %s", reason)
                self._record_trigger(check_name, reason)
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

    async def liquidity_check(self, blackboard: BlackboardState) -> Optional[str]:
        """Check if symbol has sufficient trading volume."""
        thresholds = _get_thresholds()
        f = blackboard.raw_features.get("features", blackboard.raw_features)
        volume = f.get("volume") or f.get("volume_1d") or 0
        min_volume = thresholds["cb_min_volume"]

        if volume > 0 and volume < min_volume:
            return f"Insufficient liquidity: volume={volume:,.0f} below {min_volume:,.0f} threshold"
        return None

    async def correlation_spike_detector(self, blackboard: BlackboardState) -> Optional[str]:
        """Detect market correlation breakdown (all assets moving together)."""
        thresholds = _get_thresholds()
        try:
            from app.services.correlation_radar import get_correlation_radar
            radar = get_correlation_radar()
            status = radar.get_status()

            # Check if correlation breaks exceed threshold
            breaks = status.get("active_breaks", [])
            if len(breaks) > 0:
                # High correlation (>0.95) across multiple pairs indicates systemic risk
                high_corr = [b for b in breaks if abs(b.get("correlation", 0)) > thresholds["cb_correlation_spike_threshold"]]
                if len(high_corr) >= 3:  # 3+ pairs with extreme correlation
                    return f"Correlation spike: {len(high_corr)} pairs with >95% correlation (systemic risk)"
        except Exception:
            pass  # Correlation radar unavailable — don't block
        return None

    async def data_connection_health(self, blackboard: BlackboardState) -> Optional[str]:
        """Check if critical data sources are stale or disconnected."""
        thresholds = _get_thresholds()
        try:
            from app.council.data_quality import get_data_quality_monitor
            dqm = get_data_quality_monitor()
            health = dqm.get_health()

            # Check for critical stale sources
            critical_stale = health.get("critical_stale", [])
            if len(critical_stale) > 0:
                sources = ", ".join(critical_stale[:3])  # Show first 3
                return f"Data connection degraded: {len(critical_stale)} critical sources stale ({sources})"

            # Check overall quality score
            quality_score = health.get("overall_quality_score", 100)
            if quality_score < 50:  # Below 50% quality
                return f"Data quality critically low: {quality_score:.0f}% (threshold: 50%)"
        except Exception:
            pass  # Data quality monitor unavailable — don't block
        return None

    async def profit_target_ceiling(self, blackboard: BlackboardState) -> Optional[str]:
        """Check if daily profit target has been reached (take profits)."""
        thresholds = _get_thresholds()
        try:
            from app.api.v1.risk import drawdown_check_status
            dd = await drawdown_check_status()
            daily_pnl_pct = dd.get("daily_pnl_pct", 0)
            ceiling = thresholds["cb_daily_profit_ceiling"]

            if daily_pnl_pct >= ceiling:
                return f"Daily profit target reached: {daily_pnl_pct:.2%} exceeds {ceiling:.0%} ceiling (take profits)"
        except Exception:
            pass  # Risk API unavailable — don't block
        return None


# Global singleton
circuit_breaker = CircuitBreaker()
