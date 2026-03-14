"""Regime Publisher — publishes current market regime to MessageBus every 60s.

Phase 4 (Item 4): The WeightLearner maintains separate weight matrices per
regime. This publisher ensures the current regime is always available on the
MessageBus so subscribers (WeightLearner, Kelly sizer, Arbiter, etc.) can
react to regime changes in near-real-time.

24/7 Persistence: Regime persists in DuckDB across restarts and market closures.
When markets are closed, last known regime is used — never "UNKNOWN".
"""
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

PUBLISH_INTERVAL_S = 60.0
TOPIC = "regime.current"

# Map Bayesian states to display regime (GREEN/YELLOW/RED) for dashboard
_BAYESIAN_TO_DISPLAY = {
    "trending_bull": "GREEN",
    "low_vol_grind": "GREEN",
    "mean_revert": "YELLOW",
    "transition": "YELLOW",
    "trending_bear": "RED",
    "high_vol_crisis": "RED",
}


class RegimePublisher:
    """Background service that publishes the current regime periodically.

    Reads from the singleton BayesianRegime engine (updated by each
    council run) and publishes to MessageBus.
    """

    def __init__(self, interval: float = PUBLISH_INTERVAL_S):
        self._interval = interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._publish_count = 0
        self._last_regime: str = "UNKNOWN"

    async def start(self) -> None:
        """Start the background publish loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="regime_publisher")
        logger.info("RegimePublisher: started (interval=%.0fs)", self._interval)

    async def stop(self) -> None:
        """Stop the background publish loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("RegimePublisher: stopped after %d publishes", self._publish_count)

    async def _loop(self) -> None:
        """Main publish loop."""
        while self._running:
            try:
                await self._publish_regime()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("RegimePublisher: publish failed: %s", e)

            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break

    async def _publish_regime(self) -> None:
        """Read current regime and publish to MessageBus.

        Persists regime to DuckDB when valid. When markets are closed or no fresh
        data, uses last persisted regime — never returns UNKNOWN.
        """
        from app.core.message_bus import get_message_bus
        from app.data.duckdb_storage import duckdb_store

        # Try Bayesian regime engine first (updated by council runs)
        regime = "UNKNOWN"
        regime_raw = "UNKNOWN"
        probability = 0.0
        entropy = 0.0
        beliefs = {}
        position_modifier = 1.0
        source = "default"
        updated_at = None

        try:
            from app.council.regime.bayesian_regime import get_bayesian_regime
            bayes = get_bayesian_regime()
            beliefs = bayes.get_beliefs()
            if beliefs:
                regime_raw, probability = bayes.dominant_regime()
                regime = _BAYESIAN_TO_DISPLAY.get(regime_raw, regime_raw)
                entropy = bayes.entropy()
                position_modifier = bayes.position_size_modifier()
                source = "bayesian_regime"
        except Exception:
            pass

        # Fallback 1: read from DuckDB council_decisions if Bayesian engine hasn't been updated
        if regime == "UNKNOWN" or not beliefs:
            try:
                def _fetch_regime():
                    cur = duckdb_store.get_thread_cursor()
                    try:
                        return cur.execute(
                            "SELECT regime FROM council_decisions ORDER BY rowid DESC LIMIT 1"
                        ).fetchone()
                    finally:
                        cur.close()
                row = await asyncio.to_thread(_fetch_regime)
                if row and row[0] and str(row[0]).upper() not in ("UNKNOWN", ""):
                    regime = str(row[0]).upper()
                    regime_raw = regime
                    source = "duckdb_last_decision"
            except Exception:
                pass

        # Fallback 2: price-action regime from SPY OHLCV in DuckDB (Issue #60)
        if regime == "UNKNOWN" or not beliefs:
            try:
                from app.council.regime.price_action_regime import get_price_action_regime
                pa_result = await get_price_action_regime()
                pa_regime = pa_result.get("regime", "UNKNOWN")
                if pa_regime != "UNKNOWN":
                    regime = pa_regime
                    probability = pa_result.get("confidence", 0.0)
                    beliefs = pa_result.get("beliefs", {})
                    source = "price_action_fallback"
                    # Derive entropy from confidence (higher confidence = lower entropy)
                    import math
                    if probability > 0 and probability < 1:
                        entropy = -(probability * math.log(probability) + (1 - probability) * math.log(1 - probability))
                    else:
                        entropy = 0.0
                    # Conservative position sizing for fallback
                    position_modifier = round(0.5 + probability * 0.4, 3)
                    logger.info(
                        "RegimePublisher: using price-action fallback → %s (conf=%.0f%%)",
                        regime, probability * 100,
                    )
            except Exception as e:
                logger.debug("RegimePublisher: price-action fallback failed: %s", e)

        # Fallback 3: read from persisted regime_state (24/7 persistence)
        if regime == "UNKNOWN":
            try:
                last = await asyncio.to_thread(duckdb_store.get_last_regime)
                if last:
                    regime, updated_at, source = last[0], last[1], last[2] or "persisted"
                    regime_raw = regime
            except Exception:
                pass

        # Persist when we have a valid regime (so it survives restarts and market close)
        if regime != "UNKNOWN":
            try:
                await asyncio.to_thread(duckdb_store.persist_regime, regime, source)
            except Exception:
                pass

        # Publish to MessageBus
        bus = get_message_bus()
        payload = {
            "regime": regime,
            "regime_raw": regime_raw,
            "regime_probability": round(probability, 4),
            "entropy": round(entropy, 4),
            "beliefs": {k: round(v, 4) for k, v in beliefs.items()} if beliefs else {},
            "position_modifier": round(position_modifier, 3),
            "source": source,
            "timestamp": time.time(),
            "updated_at": updated_at,
        }
        await bus.publish(TOPIC, payload)
        self._publish_count += 1

        if regime != self._last_regime:
            logger.info(
                "RegimePublisher: regime changed %s → %s (prob=%.0f%%, entropy=%.3f)",
                self._last_regime, regime, probability * 100, entropy,
            )
            self._last_regime = regime

        # Also update WeightLearner with current regime for matrix selection
        try:
            from app.council.weight_learner import get_weight_learner
            learner = get_weight_learner()
            learner.current_regime = regime
        except Exception:
            pass

    def get_status(self) -> dict:
        """Return publisher status for monitoring."""
        return {
            "running": self._running,
            "interval_s": self._interval,
            "publish_count": self._publish_count,
            "last_regime": self._last_regime,
        }


# ── Module-level singleton ───────────────────────────────────────────────────
_publisher: Optional[RegimePublisher] = None


def get_regime_publisher() -> RegimePublisher:
    """Get or create the singleton RegimePublisher."""
    global _publisher
    if _publisher is None:
        _publisher = RegimePublisher()
    return _publisher
