"""Regime Publisher — publishes current market regime to MessageBus every 60s.

Phase 4 (Item 4): The WeightLearner maintains separate weight matrices per
regime. This publisher ensures the current regime is always available on the
MessageBus so subscribers (WeightLearner, Kelly sizer, Arbiter, etc.) can
react to regime changes in near-real-time.

Topic: ``regime.current``

Payload:
    {
        "regime": "BULLISH",
        "regime_probability": 0.72,
        "entropy": 0.45,
        "beliefs": {"BULLISH": 0.72, "NEUTRAL": 0.15, ...},
        "position_modifier": 1.0,
        "source": "bayesian_regime",
    }
"""
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

PUBLISH_INTERVAL_S = 60.0
TOPIC = "regime.current"


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
        """Read current regime and publish to MessageBus."""
        from app.core.message_bus import get_message_bus

        # Try Bayesian regime engine first (updated by council runs)
        regime = "UNKNOWN"
        probability = 0.0
        entropy = 0.0
        beliefs = {}
        position_modifier = 1.0
        source = "default"

        try:
            from app.council.regime.bayesian_regime import get_bayesian_regime
            bayes = get_bayesian_regime()
            beliefs = bayes.get_beliefs()
            if beliefs:
                regime, probability = bayes.dominant_regime()
                entropy = bayes.entropy()
                position_modifier = bayes.position_size_modifier()
                source = "bayesian_regime"
        except Exception:
            pass

        # Fallback: read from DuckDB if Bayesian engine hasn't been updated
        if regime == "UNKNOWN" or not beliefs:
            try:
                def _fetch_regime():
                    from app.data.duckdb_storage import duckdb_store
                    cur = duckdb_store.get_thread_cursor()
                    try:
                        return cur.execute(
                            "SELECT regime FROM council_decisions ORDER BY rowid DESC LIMIT 1"
                        ).fetchone()
                    finally:
                        cur.close()
                row = await asyncio.to_thread(_fetch_regime)
                if row and row[0]:
                    regime = str(row[0])
                    source = "duckdb_last_decision"
            except Exception:
                pass

        # Publish to MessageBus
        bus = get_message_bus()
        payload = {
            "regime": regime,
            "regime_probability": round(probability, 4),
            "entropy": round(entropy, 4),
            "beliefs": {k: round(v, 4) for k, v in beliefs.items()} if beliefs else {},
            "position_modifier": round(position_modifier, 3),
            "source": source,
            "timestamp": time.time(),
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
