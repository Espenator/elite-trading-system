"""Homeostasis Monitor — autonomic nervous system of Embodier Trader.

Monitors system vitals and automatically switches trading modes:
  AGGRESSIVE: Strong trend, low drawdown, all agents healthy → 1.5x positions
  NORMAL: Default state → 1.0x positions
  DEFENSIVE: Elevated volatility, moderate drawdown → 0.5x positions
  HALTED: Circuit breaker fired, extreme drawdown → 0.0x positions

Used by runner.py to load appropriate directives and scale positions.

Usage:
    from app.council.homeostasis import get_homeostasis
    monitor = get_homeostasis()
    mode = monitor.get_mode()
    scale = monitor.get_position_scale()
"""
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class HomeostasisMonitor:
    """Monitors system health and switches modes automatically."""

    # Mode thresholds
    AGGRESSIVE_THRESHOLD = 80  # Risk score > 80 = aggressive
    NORMAL_THRESHOLD = 50      # Risk score 50-80 = normal
    DEFENSIVE_THRESHOLD = 30   # Risk score 30-50 = defensive
    # Below 30 = HALTED

    def __init__(self):
        self._last_vitals: Dict[str, Any] = {}
        self._last_check: float = 0
        self._mode: str = "NORMAL"
        self._cache_ttl: float = 10.0  # Recheck every 10s (fast enough for crisis detection)

    async def check_vitals(self) -> Dict[str, Any]:
        """Returns system state: portfolio heat, agent health, data freshness, drawdown.

        Caches results briefly. Uses shorter TTL during DEFENSIVE/HALTED modes.
        """
        now = time.time()
        # Bypass cache faster during crisis modes
        effective_ttl = 3.0 if self._mode in ("DEFENSIVE", "HALTED") else self._cache_ttl
        if self._last_vitals and (now - self._last_check) < effective_ttl:
            return self._last_vitals

        vitals = {
            "risk_score": 50,
            "portfolio_heat": 0.0,
            "drawdown_pct": 0.0,
            "drawdown_breached": False,
            "agent_health": {},
            "data_freshness": "unknown",
            "positions_count": 0,
            "trading_allowed": True,
        }

        # Portfolio risk score
        try:
            from app.api.v1.risk import risk_score as get_risk
            risk_data = await get_risk()
            vitals["risk_score"] = risk_data.get("risk_score", 50)
            vitals["portfolio_heat"] = risk_data.get("portfolio_heat", 0)
        except Exception:
            pass

        # Drawdown status
        try:
            from app.api.v1.risk import drawdown_check_status
            dd = await drawdown_check_status()
            vitals["drawdown_pct"] = dd.get("daily_pnl_pct", 0)
            vitals["drawdown_breached"] = dd.get("drawdown_breached", False)
            vitals["trading_allowed"] = dd.get("trading_allowed", True)
        except Exception:
            pass

        # Position count
        try:
            from app.services.alpaca_service import alpaca_service
            positions = await alpaca_service.get_positions()
            vitals["positions_count"] = len(positions)
        except Exception:
            pass

        # Agent health
        try:
            from app.council.self_awareness import get_self_awareness
            sa = get_self_awareness()
            vitals["agent_health"] = sa.health.get_all_health()
        except Exception:
            pass

        # Data quality — track PNS data source freshness
        try:
            from app.council.data_quality import get_data_quality_monitor
            dqm = get_data_quality_monitor()
            dq_health = dqm.get_health()
            vitals["data_quality_score"] = dq_health["overall_quality_score"]
            vitals["data_sources_stale"] = dq_health["critical_stale"]
            if dqm.should_degrade():
                vitals["data_freshness"] = "stale"
                # Lower risk score to trigger DEFENSIVE mode
                vitals["risk_score"] = min(vitals["risk_score"], 45)
        except Exception:
            pass

        # Memory watchdog — track layered_memory_agent health
        try:
            from app.council.memory_watchdog import get_memory_watchdog
            mw = get_memory_watchdog()
            mem_health = await mw.check_health()
            vitals["memory_health"] = mem_health["health_status"]
            vitals["memory_metrics"] = mem_health["metrics"]
            vitals["memory_warnings"] = mem_health["warnings"]
            # Degrade if memory is unhealthy
            if mem_health["health_status"] == "unhealthy":
                vitals["risk_score"] = min(vitals["risk_score"], 40)
                logger.warning("Memory watchdog reports unhealthy state: %s", mem_health["warnings"])
            elif mem_health["health_status"] == "degraded":
                vitals["risk_score"] = min(vitals["risk_score"], 45)
        except Exception as e:
            logger.debug("Memory watchdog check failed: %s", e)

        self._last_vitals = vitals
        self._last_check = now
        self._mode = self._compute_mode(vitals)

        return vitals

    def _compute_mode(self, vitals: Dict[str, Any]) -> str:
        """Determine mode from vitals."""
        if not vitals.get("trading_allowed", True):
            return "HALTED"
        if vitals.get("drawdown_breached", False):
            return "HALTED"

        risk_score = vitals.get("risk_score", 50)
        if risk_score >= self.AGGRESSIVE_THRESHOLD:
            return "AGGRESSIVE"
        elif risk_score >= self.NORMAL_THRESHOLD:
            return "NORMAL"
        elif risk_score >= self.DEFENSIVE_THRESHOLD:
            return "DEFENSIVE"
        return "HALTED"

    def get_mode(self) -> str:
        """Get current mode: AGGRESSIVE | NORMAL | DEFENSIVE | HALTED.

        Uses cached vitals if available, otherwise returns last known mode.
        """
        return self._mode

    def get_position_scale(self) -> float:
        """Position size multiplier based on current mode.

        AGGRESSIVE: 1.5x, NORMAL: 1.0x, DEFENSIVE: 0.5x, HALTED: 0.0x
        """
        return {
            "AGGRESSIVE": 1.5,
            "NORMAL": 1.0,
            "DEFENSIVE": 0.5,
            "HALTED": 0.0,
        }.get(self._mode, 1.0)

    def get_directive_regime(self) -> str:
        """Map mode to directive regime for DirectiveLoader.

        AGGRESSIVE -> bullish, DEFENSIVE -> bearish, else -> unknown
        """
        return {
            "AGGRESSIVE": "bullish",
            "DEFENSIVE": "bearish",
        }.get(self._mode, "unknown")

    def get_status(self) -> Dict[str, Any]:
        """Full status for dashboard."""
        return {
            "mode": self._mode,
            "position_scale": self.get_position_scale(),
            "directive_regime": self.get_directive_regime(),
            "vitals": self._last_vitals,
            "last_check": self._last_check,
        }


# Global singleton
_homeostasis: Optional[HomeostasisMonitor] = None


def get_homeostasis() -> HomeostasisMonitor:
    """Get or create the singleton HomeostasisMonitor."""
    global _homeostasis
    if _homeostasis is None:
        _homeostasis = HomeostasisMonitor()
    return _homeostasis
