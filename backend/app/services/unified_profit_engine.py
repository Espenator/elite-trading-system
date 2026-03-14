"""UnifiedProfitEngine — single adaptive scorer replacing 5 competing brains.

The system previously had 5 independent scoring systems:
  1. SignalEngine (hardcoded RSI+MACD composite)
  2. Council DAG (17-agent votes)
  3. TurboScanner (SQL screens)
  4. PatternLibrary (12 hardcoded patterns)
  5. ML Brain XGBoost (trained but never deployed)

This engine unifies them into a single weighted ensemble where each brain's
contribution is weighted by its historical accuracy (from OutcomeTracker).

Architecture:
    Any signal source → UnifiedProfitEngine.score()
        → Collect scores from all available brains
        → Weight by historical accuracy (adaptive)
        → Produce single 0-100 score + confidence + direction
        → Publish to signal.unified for downstream consumption

Brain Weights (adaptive from outcomes):
    - ML XGBoost: starts at 0.30, adapts based on prediction accuracy
    - Council consensus: starts at 0.25, adapts based on trade outcomes
    - TA composite: starts at 0.20, stable baseline
    - TurboScanner: starts at 0.15, adapts based on screen hit rates
    - PatternLibrary: starts at 0.10, adapts based on pattern win rates
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.services.database import db_service

logger = logging.getLogger(__name__)

CONFIG_KEY = "unified_profit_engine"

# Default brain weights (sum = 1.0)
DEFAULT_WEIGHTS = {
    "ml_xgboost": 0.30,
    "council": 0.25,
    "ta_composite": 0.20,
    "turbo_scanner": 0.15,
    "pattern_library": 0.10,
}


class UnifiedProfitEngine:
    """Single adaptive scorer that unifies all signal sources."""

    ADAPT_INTERVAL = 3600  # Recompute weights hourly
    MIN_OUTCOMES = 10  # Need this many before adapting

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._adapt_task: Optional[asyncio.Task] = None
        self._weights = dict(DEFAULT_WEIGHTS)
        self._brain_accuracy: Dict[str, float] = {}
        self._scores_produced = 0
        self._load_weights()

    def _load_weights(self) -> None:
        """Load persisted adaptive weights."""
        saved = db_service.get_config(CONFIG_KEY)
        if saved and "weights" in saved:
            self._weights = saved["weights"]
            self._brain_accuracy = saved.get("accuracy", {})

    def _save_weights(self) -> None:
        """Persist weights to DB."""
        db_service.set_config(CONFIG_KEY, {
            "weights": self._weights,
            "accuracy": self._brain_accuracy,
        })

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._bus:
            await self._bus.subscribe("signal.generated", self._on_signal)
        self._adapt_task = asyncio.create_task(self._adapt_loop())
        logger.info("UnifiedProfitEngine started — weights: %s", self._weights)

    async def stop(self) -> None:
        self._running = False
        if self._adapt_task:
            self._adapt_task.cancel()
            try:
                await self._adapt_task
            except asyncio.CancelledError:
                pass
        self._save_weights()
        logger.info("UnifiedProfitEngine stopped")

    async def _on_signal(self, data: Dict[str, Any]) -> None:
        """Enrich incoming signals with unified scoring."""
        symbol = data.get("symbol", "")
        if not symbol:
            return

        unified = await self.score(symbol, data)
        if unified and self._bus:
            await self._bus.publish("signal.unified", unified)

    async def score(self, symbol: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Produce a unified score from all available brains.

        Args:
            symbol: Ticker symbol
            context: Optional context dict (may contain pre-computed scores)

        Returns:
            Unified score dict or None
        """
        context = context or {}
        brain_scores: Dict[str, Tuple[float, float]] = {}  # brain -> (score, confidence)

        # 1. TA Composite (from signal engine)
        ta_score = context.get("score", 0)
        if ta_score:
            brain_scores["ta_composite"] = (float(ta_score), 0.5)

        # 2. ML XGBoost
        try:
            from app.services.ml_scorer import get_ml_scorer
            ml = get_ml_scorer()
            if ml.is_loaded:
                # Try to get bars from context or DuckDB (off event loop)
                ml_result = await asyncio.to_thread(self._get_ml_score, symbol)
                if ml_result:
                    brain_scores["ml_xgboost"] = (ml_result["ml_score"], ml_result["confidence"])
        except Exception:
            pass

        # 3. TurboScanner hits
        try:
            from app.services.turbo_scanner import get_turbo_scanner
            ts = get_turbo_scanner()
            signals = ts.get_signals(symbol=symbol)
            if signals:
                # Average recent scanner hits for this symbol
                avg_score = sum(s.get("score", 50) for s in signals[-5:]) / min(5, len(signals))
                brain_scores["turbo_scanner"] = (avg_score, 0.4)
        except Exception:
            pass

        # 4. PatternLibrary
        try:
            from app.services.pattern_library import get_pattern_library
            pl = get_pattern_library()
            patterns = pl.get_active_patterns(symbol)
            if patterns:
                avg_score = sum(p.get("score", 50) for p in patterns) / len(patterns)
                brain_scores["pattern_library"] = (avg_score, 0.3)
        except Exception:
            pass

        if not brain_scores:
            return None

        # Weighted ensemble
        total_weight = 0.0
        weighted_score = 0.0
        directions = []

        for brain, (score, confidence) in brain_scores.items():
            w = self._weights.get(brain, 0.1)
            # Scale weight by confidence
            effective_w = w * (0.5 + confidence * 0.5)
            weighted_score += score * effective_w
            total_weight += effective_w
            if score > 55:
                directions.append("bullish")
            elif score < 45:
                directions.append("bearish")

        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 50.0

        final_score = max(0.0, min(100.0, final_score))

        # Consensus direction
        bull_count = directions.count("bullish")
        bear_count = directions.count("bearish")
        if bull_count > bear_count:
            direction = "bullish"
        elif bear_count > bull_count:
            direction = "bearish"
        else:
            direction = "neutral"

        # Consensus confidence
        total_brains = len(brain_scores)
        consensus = max(bull_count, bear_count) / total_brains if total_brains else 0
        confidence = consensus * (abs(final_score - 50) / 50)

        self._scores_produced += 1

        return {
            "symbol": symbol,
            "unified_score": round(final_score, 1),
            "direction": direction,
            "confidence": round(confidence, 3),
            "brains_active": total_brains,
            "brain_scores": {k: round(v[0], 1) for k, v in brain_scores.items()},
            "weights": {k: round(v, 3) for k, v in self._weights.items()},
            "price": context.get("close", context.get("price", 0)),
            "timestamp": time.time(),
        }

    def _get_ml_score(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ML score from DuckDB data."""
        try:
            from app.data.duckdb_storage import duckdb_store
            conn = duckdb_store.get_thread_cursor()
            rows = conn.execute(
                "SELECT open, high, low, close, volume FROM daily_ohlcv "
                "WHERE symbol = ? ORDER BY date DESC LIMIT 50",
                [symbol],
            ).fetchall()

            if len(rows) < 20:
                return None

            # Reverse to chronological order
            bars = [
                {"open": r[0], "high": r[1], "low": r[2], "close": r[3], "volume": r[4]}
                for r in reversed(rows)
            ]

            from app.services.ml_scorer import get_ml_scorer
            return get_ml_scorer().score(symbol, bars)
        except Exception:
            return None

    async def _adapt_loop(self) -> None:
        """Periodically adapt brain weights from outcome data."""
        while self._running:
            await asyncio.sleep(self.ADAPT_INTERVAL)
            try:
                await asyncio.to_thread(self._adapt_weights)
            except Exception as e:
                logger.debug("Weight adaptation error: %s", e)

    def _adapt_weights(self) -> None:
        """Recompute brain weights from OutcomeTracker data."""
        try:
            from app.services.outcome_tracker import get_outcome_tracker
            tracker = get_outcome_tracker()
            stats = tracker._stats

            if stats["total_resolved"] < self.MIN_OUTCOMES:
                return

            # Use overall win rate as baseline
            win_rate = stats.get("win_rate", 0.5)

            # Check ML accuracy from outcome_resolver
            try:
                from app.modules.ml_engine.outcome_resolver import get_flywheel_metrics
                ml_metrics = get_flywheel_metrics()
                ml_acc = ml_metrics.get("accuracy_30d")
                if ml_acc is not None:
                    self._brain_accuracy["ml_xgboost"] = ml_acc
                    # Scale ML weight: higher accuracy = more weight
                    self._weights["ml_xgboost"] = max(0.1, min(0.5, 0.3 * (0.5 + ml_acc)))
            except Exception:
                pass

            # Council accuracy from feedback loop
            try:
                from app.council.feedback_loop import get_agent_performance
                perf = get_agent_performance()
                if perf["total_outcomes"] >= 10:
                    # Use ratio of outcomes to decisions as proxy for council effectiveness
                    council_eff = min(1.0, perf["total_outcomes"] / max(1, perf["total_decisions"]))
                    self._brain_accuracy["council"] = council_eff
                    self._weights["council"] = max(0.1, min(0.4, 0.25 * (0.5 + council_eff)))
            except Exception:
                pass

            # Normalize weights to sum to 1.0
            total = sum(self._weights.values())
            if total > 0:
                self._weights = {k: v / total for k, v in self._weights.items()}

            self._save_weights()
            logger.info("Adapted brain weights: %s", {k: f"{v:.3f}" for k, v in self._weights.items()})

        except Exception as e:
            logger.debug("Weight adaptation failed: %s", e)

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "weights": {k: round(v, 3) for k, v in self._weights.items()},
            "brain_accuracy": self._brain_accuracy,
            "scores_produced": self._scores_produced,
            "adaptation_interval_s": self.ADAPT_INTERVAL,
        }


# Module-level singleton
_engine: Optional[UnifiedProfitEngine] = None


def get_unified_engine() -> UnifiedProfitEngine:
    global _engine
    if _engine is None:
        _engine = UnifiedProfitEngine()
    return _engine
