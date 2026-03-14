"""Homeostasis Monitor — autonomic nervous system of Embodier Trader.

Monitors system vitals and automatically switches trading modes based on
real-time conditions (drawdown, regime, VIX, agent health, circuit breakers):

  AGGRESSIVE (1.5x): drawdown < 0.5%, all vitals green, regime BULLISH
  NORMAL    (1.0x): default state, drawdown < 1%
  CAUTIOUS  (0.75x): drawdown 1-2% or error_rate > 5%
  DEFENSIVE (0.5x): drawdown 2-3% or regime BEARISH
  PROTECTIVE(0.25x): drawdown > 3% or VIX > 35 or circuit breaker tripped
  HALTED    (0.0x): circuit breaker killed trading entirely

Used by runner.py to load appropriate directives and scale positions.
OrderExecutor uses get_position_scale() to size positions.

Agent 7: Tracks circuit breaker halt count per day for dashboard / vigilance.
"""
import logging
import time
from datetime import date, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Mode definitions: name -> (position_scale, directive_regime)
MODE_CONFIG = {
    "AGGRESSIVE":  (1.5,  "bullish"),
    "NORMAL":      (1.0,  "unknown"),
    "CAUTIOUS":    (0.75, "unknown"),
    "DEFENSIVE":   (0.5,  "bearish"),
    "PROTECTIVE":  (0.25, "bearish"),
    "HALTED":      (0.0,  "bearish"),
}


class HomeostasisMonitor:
    """Monitors system health and switches modes automatically based on
    drawdown, regime, VIX, error rate, and circuit breaker state."""

    def __init__(self):
        self._last_vitals: Dict[str, Any] = {}
        self._last_check: float = 0
        self._mode: str = "NORMAL"
        self._prev_mode: str = "NORMAL"
        self._cache_ttl: float = 10.0  # Recheck every 10s (fast enough for crisis detection)
        # Agent 7: circuit breaker halt count per calendar day (for dashboard vigilance)
        self._halt_date: Optional[str] = None  # "YYYY-MM-DD"
        self._halt_count_today: int = 0
        # Agent tick health tracking (Issue #77)
        self._agent_tick_health: Dict[str, Dict[str, Any]] = {}
        # High-water mark for drawdown (persisted in memory per session)
        self._high_water_mark: float = 0.0
        # Circuit breaker tripped flag (reset at start of day)
        self._circuit_breaker_tripped: bool = False
        self._circuit_breaker_trip_date: Optional[str] = None

    async def check_vitals(self) -> Dict[str, Any]:
        """Returns system state: portfolio heat, agent health, data freshness, drawdown.

        Caches results briefly. Uses shorter TTL during crisis modes.
        """
        now = time.time()
        # Bypass cache faster during crisis modes
        effective_ttl = 3.0 if self._mode in ("DEFENSIVE", "PROTECTIVE", "HALTED") else self._cache_ttl
        if self._last_vitals and (now - self._last_check) < effective_ttl:
            return self._last_vitals

        vitals = {
            "risk_score": 50,
            "portfolio_heat": 0.0,
            "drawdown_pct": 0.0,
            "drawdown_from_hwm_pct": 0.0,
            "drawdown_breached": False,
            "agent_health": {},
            "agent_tick_health": self._agent_tick_health,
            "data_freshness": "unknown",
            "positions_count": 0,
            "trading_allowed": True,
            "regime": "UNKNOWN",
            "regime_source": "none",
            "vix": 0.0,
            "error_rate": 0.0,
            "circuit_breaker_tripped": self._circuit_breaker_tripped,
            "equity": 0.0,
            "high_water_mark": self._high_water_mark,
        }

        # ── 1. Alpaca account: equity + drawdown from high-water mark ──
        try:
            from app.services.alpaca_service import alpaca_service
            account = await alpaca_service.get_account()
            if account:
                equity = float(account.get("equity", 0))
                last_equity = float(account.get("last_equity", equity))
                vitals["equity"] = equity

                # Update high-water mark (session-based)
                if equity > self._high_water_mark:
                    self._high_water_mark = equity
                if last_equity > self._high_water_mark:
                    self._high_water_mark = last_equity
                vitals["high_water_mark"] = self._high_water_mark

                # Drawdown from high-water mark (intraday)
                if self._high_water_mark > 0:
                    dd_from_hwm = ((self._high_water_mark - equity) / self._high_water_mark) * 100
                    vitals["drawdown_from_hwm_pct"] = max(0.0, dd_from_hwm)

                # Daily drawdown (from last_equity = previous close)
                if last_equity > 0:
                    daily_dd = ((last_equity - equity) / last_equity) * 100
                    vitals["drawdown_pct"] = max(0.0, daily_dd)  # Only track losses as positive dd
        except Exception as e:
            logger.debug("Homeostasis: Alpaca account unavailable: %s", e)

        # ── 2. Portfolio risk score ──
        try:
            from app.api.v1.risk import risk_score as get_risk
            risk_data = await get_risk()
            vitals["risk_score"] = risk_data.get("risk_score", risk_data.get("score", 50))
            vitals["portfolio_heat"] = risk_data.get("portfolio_heat", 0)
        except Exception:
            pass

        # ── 3. Drawdown status (existing endpoint) ──
        try:
            from app.api.v1.risk import drawdown_check_status
            dd = await drawdown_check_status()
            if dd.get("drawdown_breached", False):
                vitals["drawdown_breached"] = True
            vitals["trading_allowed"] = dd.get("trading_allowed", True)
        except Exception:
            pass

        # ── 4. Regime from RegimePublisher ──
        try:
            from app.council.regime_publisher import get_regime_publisher
            rp = get_regime_publisher()
            vitals["regime"] = rp._last_regime or "UNKNOWN"
            vitals["regime_source"] = "regime_publisher"
        except Exception:
            pass
        # Fallback: try Bayesian regime engine directly
        if vitals["regime"] == "UNKNOWN":
            try:
                from app.council.regime.bayesian_regime import get_bayesian_regime
                bayes = get_bayesian_regime()
                dominant, prob = bayes.dominant_regime()
                if dominant and dominant != "UNKNOWN":
                    vitals["regime"] = dominant
                    vitals["regime_source"] = "bayesian_regime"
            except Exception:
                pass

        # ── 5. VIX level ──
        try:
            from app.data.duckdb_storage import duckdb_store
            import asyncio

            def _fetch_vix():
                cur = duckdb_store.get_thread_cursor()
                try:
                    row = cur.execute(
                        "SELECT close FROM daily_ohlcv WHERE symbol IN ('VIX', 'VIXY', '$VIX.X') "
                        "ORDER BY date DESC LIMIT 1"
                    ).fetchone()
                    return float(row[0]) if row else 0.0
                except Exception:
                    return 0.0
                finally:
                    cur.close()

            vitals["vix"] = await asyncio.to_thread(_fetch_vix)
        except Exception:
            pass

        # ── 6. Position count ──
        try:
            from app.services.alpaca_service import alpaca_service
            positions = await alpaca_service.get_positions()
            vitals["positions_count"] = len(positions)
        except Exception:
            pass

        # ── 7. Agent health (council agents) ──
        try:
            from app.council.self_awareness import get_self_awareness
            sa = get_self_awareness()
            vitals["agent_health"] = sa.health.get_all_health()
        except Exception:
            pass

        # ── 8. Data quality ──
        try:
            from app.council.data_quality import get_data_quality_monitor
            dqm = get_data_quality_monitor()
            dq_health = dqm.get_health()
            vitals["data_quality_score"] = dq_health["overall_quality_score"]
            vitals["data_sources_stale"] = dq_health["critical_stale"]
            if dqm.should_degrade():
                vitals["data_freshness"] = "stale"
        except Exception:
            pass

        # ── 9. Error rate from agent tick health ──
        total_runs = 0
        total_errors = 0
        for agent_id, health in self._agent_tick_health.items():
            total_runs += health.get("total_runs", 0)
            total_errors += health.get("errors", 0)
        if total_runs > 0:
            vitals["error_rate"] = (total_errors / total_runs) * 100
        else:
            vitals["error_rate"] = 0.0

        # ── 10. Circuit breaker check (reset daily) ──
        today = date.today().isoformat()
        if self._circuit_breaker_trip_date != today:
            self._circuit_breaker_tripped = False
            self._circuit_breaker_trip_date = today
        vitals["circuit_breaker_tripped"] = self._circuit_breaker_tripped

        self._last_vitals = vitals
        self._last_check = now

        # ── Compute new mode and broadcast if changed ──
        new_mode = self._compute_mode(vitals)
        self._prev_mode = self._mode
        self._mode = new_mode

        if self._prev_mode != self._mode:
            logger.warning(
                "HOMEOSTASIS MODE CHANGE: %s -> %s (dd=%.2f%%, hwm_dd=%.2f%%, regime=%s, vix=%.1f, err=%.1f%%)",
                self._prev_mode, self._mode,
                vitals["drawdown_pct"], vitals["drawdown_from_hwm_pct"],
                vitals["regime"], vitals["vix"], vitals["error_rate"],
            )
            # Broadcast mode change via WebSocket
            try:
                from app.websocket_manager import broadcast_ws
                import asyncio
                asyncio.create_task(broadcast_ws("homeostasis", {
                    "type": "mode_change",
                    "prev_mode": self._prev_mode,
                    "new_mode": self._mode,
                    "position_scale": self.get_position_scale(),
                    "vitals": {
                        "drawdown_pct": vitals["drawdown_pct"],
                        "drawdown_from_hwm_pct": vitals["drawdown_from_hwm_pct"],
                        "regime": vitals["regime"],
                        "vix": vitals["vix"],
                        "error_rate": vitals["error_rate"],
                        "circuit_breaker_tripped": vitals["circuit_breaker_tripped"],
                    },
                    "timestamp": time.time(),
                }))
            except Exception as e:
                logger.debug("Homeostasis WS broadcast failed: %s", e)

            # Also publish to MessageBus for other services
            try:
                from app.core.message_bus import get_message_bus
                import asyncio
                bus = get_message_bus()
                asyncio.create_task(bus.publish("homeostasis.mode_change", {
                    "prev_mode": self._prev_mode,
                    "new_mode": self._mode,
                    "position_scale": self.get_position_scale(),
                    "timestamp": time.time(),
                }))
            except Exception:
                pass

        return vitals

    def _compute_mode(self, vitals: Dict[str, Any]) -> str:
        """Determine mode from vitals using the 5-tier dynamic switching logic.

        Priority (highest to lowest):
          HALTED:     trading killed by circuit breaker or drawdown kill switch
          PROTECTIVE: drawdown > 3% or VIX > 35 or circuit breaker tripped
          DEFENSIVE:  drawdown 2-3% or regime BEARISH
          CAUTIOUS:   drawdown 1-2% or error_rate > 5%
          NORMAL:     default state, drawdown < 1%
          AGGRESSIVE: drawdown < 0.5%, regime BULLISH, low error rate
        """
        # HALTED: trading killed entirely
        if not vitals.get("trading_allowed", True):
            return "HALTED"
        if vitals.get("drawdown_breached", False):
            return "HALTED"

        drawdown = max(vitals.get("drawdown_pct", 0), vitals.get("drawdown_from_hwm_pct", 0))
        regime = (vitals.get("regime", "UNKNOWN") or "UNKNOWN").upper()
        vix = vitals.get("vix", 0.0)
        error_rate = vitals.get("error_rate", 0.0)
        circuit_breaker = vitals.get("circuit_breaker_tripped", False)

        # PROTECTIVE: extreme conditions
        if drawdown > 3.0:
            return "PROTECTIVE"
        if vix > 35.0:
            return "PROTECTIVE"
        if circuit_breaker:
            return "PROTECTIVE"

        # DEFENSIVE: elevated risk
        if drawdown > 2.0:
            return "DEFENSIVE"
        if regime == "BEARISH":
            return "DEFENSIVE"

        # CAUTIOUS: moderate concern
        if drawdown > 1.0:
            return "CAUTIOUS"
        if error_rate > 5.0:
            return "CAUTIOUS"

        # AGGRESSIVE: everything green
        if (drawdown < 0.5
                and regime == "BULLISH"
                and error_rate < 2.0
                and vix < 25.0
                and vitals.get("data_freshness", "ok") != "stale"):
            return "AGGRESSIVE"

        # NORMAL: default
        return "NORMAL"

    def get_mode(self) -> str:
        """Get current mode: AGGRESSIVE | NORMAL | CAUTIOUS | DEFENSIVE | PROTECTIVE | HALTED."""
        return self._mode

    def get_position_scale(self) -> float:
        """Position size multiplier based on current mode."""
        scale, _ = MODE_CONFIG.get(self._mode, (1.0, "unknown"))
        return scale

    def get_directive_regime(self) -> str:
        """Map mode to directive regime for DirectiveLoader."""
        _, regime = MODE_CONFIG.get(self._mode, (1.0, "unknown"))
        return regime

    def record_circuit_breaker_halt(self) -> None:
        """Record that the circuit breaker fired (for per-day count / vigilance)."""
        today = date.today().isoformat()
        if self._halt_date == today:
            self._halt_count_today += 1
        else:
            self._halt_date = today
            self._halt_count_today = 1
        # Mark circuit breaker as tripped for mode switching
        self._circuit_breaker_tripped = True
        self._circuit_breaker_trip_date = today
        logger.warning("Circuit breaker tripped (halt #%d today)", self._halt_count_today)

    def get_halt_count_today(self) -> int:
        """Return how many times the circuit breaker has fired today (dashboard)."""
        today = date.today().isoformat()
        if self._halt_date != today:
            return 0
        return self._halt_count_today

    def record_agent_tick(self, agent_id: str, latency_ms: float, error: bool = False) -> None:
        """Record an agent tick for health tracking (Issue #77).

        Args:
            agent_id: Agent identifier (e.g. "1", "2", etc.)
            latency_ms: How long the tick took in milliseconds
            error: Whether the tick resulted in an error
        """
        key = str(agent_id)
        if key not in self._agent_tick_health:
            self._agent_tick_health[key] = {
                "total_runs": 0,
                "errors": 0,
                "last_latency_ms": 0.0,
                "avg_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "last_tick_at": 0.0,
                "last_error": None,
            }
        h = self._agent_tick_health[key]
        h["total_runs"] += 1
        h["last_latency_ms"] = round(latency_ms, 1)
        h["last_tick_at"] = time.time()
        if latency_ms > h["max_latency_ms"]:
            h["max_latency_ms"] = round(latency_ms, 1)
        # Running average
        prev_avg = h["avg_latency_ms"]
        n = h["total_runs"]
        h["avg_latency_ms"] = round(prev_avg + (latency_ms - prev_avg) / n, 1)
        if error:
            h["errors"] += 1
            h["last_error"] = time.time()

    def get_agent_tick_health(self) -> Dict[str, Dict[str, Any]]:
        """Return per-agent tick health dict for frontend/dashboard."""
        return dict(self._agent_tick_health)

    def get_status(self) -> Dict[str, Any]:
        """Full status for dashboard."""
        return {
            "mode": self._mode,
            "position_scale": self.get_position_scale(),
            "directive_regime": self.get_directive_regime(),
            "vitals": self._last_vitals,
            "last_check": self._last_check,
            "circuit_breaker_halts_today": self.get_halt_count_today(),
            "agent_tick_health": self._agent_tick_health,
            "high_water_mark": self._high_water_mark,
        }


# Global singleton
_homeostasis: Optional[HomeostasisMonitor] = None


def get_homeostasis() -> HomeostasisMonitor:
    """Get or create the singleton HomeostasisMonitor."""
    global _homeostasis
    if _homeostasis is None:
        _homeostasis = HomeostasisMonitor()
    return _homeostasis
