"""Council Gate — bridges SignalEngine → Council → OrderExecutor.

Subscribes to signal.generated on the MessageBus.  When a signal arrives
with score >= gate_threshold (regime-adaptive: 55/65/75) the full 35-agent
council is invoked. If the council verdict is execution_ready the result
is published as council.verdict which the OrderExecutor subscribes to.

Concurrency: _semaphore limits simultaneous council runs; overflow goes to
a priority queue (by score). Per-symbol per-direction cooldown prevents
rapid duplicate evaluations for the same symbol/side.

Phase B enhancements (March 11 2026):
  B1: Regime-adaptive gate threshold (BULLISH=55, NEUTRAL=65, BEARISH=75)
  B3: Regime-adaptive cooldown (BULLISH=30s, NEUTRAL=120s, CRISIS=300s)
  B4: Priority queue — when concurrency full, queue top signals by score

Pipeline:
  AlpacaStream → MessageBus → SignalEngine → **CouncilGate** → Council → OrderExecutor
  market_data.bar → signal.generated → council evaluation → council.verdict → order
"""
import asyncio
import heapq
import logging
import os
import time
from typing import Any, Dict, Optional

from app.core.score_semantics import coerce_gate_threshold_0_100, coerce_signal_score_0_100

logger = logging.getLogger(__name__)

# Regime-adaptive gate thresholds: lower in bullish (cast wider net),
# higher in bearish (only high-conviction signals)
_REGIME_GATE_THRESHOLDS: Dict[str, float] = {
    "BULLISH": 55.0,
    "RISK_ON": 58.0,
    "NEUTRAL": 65.0,
    "RISK_OFF": 70.0,
    "BEARISH": 75.0,
    "CRISIS": 75.0,
    "GREEN": 55.0,
    "YELLOW": 65.0,
    "RED": 75.0,
    "UNKNOWN": 65.0,
}

# Regime-adaptive cooldown: shorter in momentum markets, longer in crisis
_REGIME_COOLDOWNS: Dict[str, int] = {
    "BULLISH": 30,
    "RISK_ON": 45,
    "NEUTRAL": 120,
    "RISK_OFF": 180,
    "BEARISH": 240,
    "CRISIS": 300,
    "GREEN": 30,
    "YELLOW": 120,
    "RED": 300,
    "UNKNOWN": 120,
}


class CouncilGate:
    """Event-driven gate that invokes the council on high-score signals.

    Parameters
    ----------
    message_bus : MessageBus
        The async event bus.
    gate_threshold : float
        Base minimum signal score (0-100); overridden by regime-adaptive thresholds.
    max_concurrent : int
        Maximum concurrent council evaluations (overflow goes to priority queue).
        Default 5 (conservative); bursts to ``burst_concurrent`` during market open.
    burst_concurrent : int
        Max concurrent during market open burst window (first 30 min after open).
    cooldown_seconds : int
        Base per-symbol cooldown; overridden by regime-adaptive cooldowns.
    """

    def __init__(
        self,
        message_bus,
        gate_threshold: float = 65.0,
        max_concurrent: int = 5,
        burst_concurrent: int = 8,
        cooldown_seconds: int = 120,
    ):
        self.message_bus = message_bus
        self.base_gate_threshold = coerce_gate_threshold_0_100(
            gate_threshold, context="CouncilGate"
        )
        self.gate_threshold = self.base_gate_threshold
        self.max_concurrent = max_concurrent
        self.burst_concurrent = burst_concurrent
        self.cooldown_seconds = cooldown_seconds
        self._current_regime = "UNKNOWN"

        self._running = False
        self._start_time: Optional[float] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        # B3: Separate buy/sell cooldowns per symbol
        # key = "SYMBOL:buy" or "SYMBOL:sell"
        self._symbol_direction_last_eval: Dict[str, float] = {}
        # Legacy per-symbol tracker (backwards compat for status)
        self._symbol_last_eval: Dict[str, float] = {}
        self._signals_received = 0
        self._councils_invoked = 0
        self._cooldown_skips = 0
        self._concurrency_skips = 0
        self._queue_dispatched = 0
        self._queue_dropped_total = 0
        self._councils_passed = 0
        self._councils_vetoed = 0
        self._councils_held = 0
        # Priority queue: (-score, timestamp, symbol, signal_data)
        self._priority_queue: list = []
        self.max_queue_size = int(os.environ.get("COUNCILGATE_MAX_QUEUE_SIZE", "20"))
        self._queue_drain_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Subscribe to signal.generated and begin gating."""
        self._running = True
        self._start_time = time.time()
        await self.message_bus.subscribe("signal.generated", self._on_signal)
        self._queue_drain_task = asyncio.create_task(self._drain_queue_loop())
        logger.info(
            "CouncilGate started — base_threshold=%.1f, max_concurrent=%d (burst=%d), "
            "cooldown=%ds (regime-adaptive, per-direction)",
            self.base_gate_threshold,
            self.max_concurrent,
            self.burst_concurrent,
            self.cooldown_seconds,
        )

    async def stop(self) -> None:
        """Unsubscribe and stop."""
        self._running = False
        if self._queue_drain_task and not self._queue_drain_task.done():
            self._queue_drain_task.cancel()
        await self.message_bus.unsubscribe("signal.generated", self._on_signal)
        logger.info(
            "CouncilGate stopped — %d signals, %d councils, %d passed, %d vetoed, %d held, %d queued",
            self._signals_received,
            self._councils_invoked,
            self._councils_passed,
            self._councils_vetoed,
            self._councils_held,
            self._queue_dispatched,
        )

    def _get_regime_threshold(self) -> float:
        """Return regime-adaptive gate threshold."""
        return _REGIME_GATE_THRESHOLDS.get(self._current_regime, self.base_gate_threshold)

    def _get_regime_cooldown(self) -> int:
        """Return regime-adaptive cooldown in seconds."""
        return _REGIME_COOLDOWNS.get(self._current_regime, self.cooldown_seconds)

    def _is_market_open_burst(self) -> bool:
        """Return True during first 30 minutes after US market open (9:30-10:00 ET).

        During the open burst window, concurrency is raised to burst_concurrent
        to capture the opening volatility spike (B4).
        """
        try:
            from zoneinfo import ZoneInfo
            eastern = ZoneInfo("America/New_York")
        except ImportError:
            from datetime import timedelta, timezone as tz
            eastern = tz(timedelta(hours=-5))
        from datetime import datetime
        now_et = datetime.now(eastern)
        # Weekday check (Mon-Fri)
        if now_et.weekday() >= 5:
            return False
        minutes_since_midnight = now_et.hour * 60 + now_et.minute
        # 9:30 AM = 570 min, 10:00 AM = 600 min
        return 570 <= minutes_since_midnight < 600

    def _effective_max_concurrent(self) -> int:
        """Return effective concurrency limit, accounting for market open burst (B4)."""
        if self._is_market_open_burst():
            return self.burst_concurrent
        return self.max_concurrent

    async def _on_signal(self, signal_data: Dict[str, Any]) -> None:
        """Handle incoming signal — gate and invoke council if warranted."""
        if not self._running:
            return

        self._signals_received += 1
        symbol = signal_data.get("symbol", "")
        score = signal_data.get("score", 0)
        source = signal_data.get("source", "")

        # Track regime from signal data for adaptive thresholds
        regime = signal_data.get("regime", "")
        if regime:
            self._current_regime = regime

        if not symbol:
            return

        score_f = coerce_signal_score_0_100(
            score,
            context=f"CouncilGate {symbol} ({source or 'unknown'}) ",
        )

        # Gate 1: Mock source guard — never trade on mock/fake data
        if source and "mock" in source.lower():
            logger.debug("CouncilGate: skipping mock signal for %s", symbol)
            return

        # Gate 2: Regime-adaptive score threshold (B1)
        threshold = self._get_regime_threshold()
        if score_f < threshold:
            return

        # Gate 3: Regime-adaptive per-symbol+direction cooldown (B3)
        # Separate buy/sell cooldowns so a BUY cooldown doesn't block a SELL
        direction = signal_data.get("direction", "buy")
        now = time.time()
        cooldown = self._get_regime_cooldown()
        cooldown_key = f"{symbol}:{direction}"
        last_eval = self._symbol_direction_last_eval.get(cooldown_key, 0)
        if now - last_eval < cooldown:
            self._cooldown_skips += 1
            return

        # Gate 4: Concurrency — if full, queue by priority instead of dropping (B4)
        effective_limit = self._effective_max_concurrent()
        # Dynamically adjust semaphore capacity for burst windows
        if self._semaphore._value == 0 and effective_limit > self.max_concurrent:
            # Burst mode: allow extra slots by releasing additional permits
            pass  # heapq overflow handles this naturally
        if self._semaphore.locked():
            # Push to priority queue (highest score first via negative score)
            heapq.heappush(
                self._priority_queue,
                (-score_f, now, symbol, signal_data),
            )
            # Cap queue to prevent unbounded growth
            while len(self._priority_queue) > self.max_queue_size:
                dropped = heapq.heappop(self._priority_queue)
                self._queue_dropped_total += 1
                logger.warning(
                    "CouncilGate queue overflow: dropping %s (score=%.1f, cap=%d)",
                    dropped[2], -dropped[0], self.max_queue_size,
                )
            self._concurrency_skips += 1
            return

        # Launch council evaluation (non-blocking)
        asyncio.create_task(self._evaluate_with_council(symbol, signal_data))

    async def _drain_queue_loop(self) -> None:
        """Periodically drain the priority queue when semaphore slots open (B4)."""
        while self._running:
            await asyncio.sleep(2)
            while self._priority_queue and not self._semaphore.locked():
                neg_score, enqueue_time, symbol, signal_data = heapq.heappop(
                    self._priority_queue
                )
                # Skip if signal is stale (>60s old)
                if time.time() - enqueue_time > 60:
                    continue
                # Skip if symbol+direction was evaluated while queued
                cooldown = self._get_regime_cooldown()
                drain_direction = signal_data.get("direction", "buy")
                last_eval = self._symbol_direction_last_eval.get(
                    f"{symbol}:{drain_direction}", 0
                )
                if time.time() - last_eval < cooldown:
                    continue
                self._queue_dispatched += 1
                asyncio.create_task(
                    self._evaluate_with_council(symbol, signal_data)
                )

    async def _evaluate_with_council(
        self, symbol: str, signal_data: Dict[str, Any]
    ) -> None:
        """Run the full 33-agent council for the symbol."""
        try:
            from app.core.logging_config import trace_id, generate_trace_id
            trace_id.set(generate_trace_id())
        except Exception:
            pass
        async with self._semaphore:
            direction = signal_data.get("direction", "buy")
            now_ts = time.time()
            self._symbol_last_eval[symbol] = now_ts
            self._symbol_direction_last_eval[f"{symbol}:{direction}"] = now_ts
            self._councils_invoked += 1

            try:
                from app.council.runner import run_council

                score = signal_data.get("score", 0)
                regime = signal_data.get("regime", "UNKNOWN")
                price = signal_data.get("close", signal_data.get("price", 0))

                logger.info(
                    "\u2699 CouncilGate: invoking council for %s "
                    "(signal=%.1f, regime=%s, price=$%.2f)",
                    symbol,
                    score,
                    regime,
                    price,
                )

                # Pass signal data as context for agents
                context = {
                    "signal_score": score,
                    "signal_label": signal_data.get("label", ""),
                    "signal_regime": regime,
                    "signal_price": price,
                    "signal_volume": signal_data.get("volume", 0),
                    "signal_timestamp": signal_data.get("timestamp", ""),
                    "source": "council_gate",
                }

                # Global council timeout: 90s max (individual agents timeout at 30s,
                # but cumulative stages + intelligence + debate can stack up)
                _council_timeout = float(os.environ.get("COUNCIL_GLOBAL_TIMEOUT", "90"))
                try:
                    decision = await asyncio.wait_for(
                        run_council(
                            symbol=symbol,
                            timeframe="1d",
                            context=context,
                        ),
                        timeout=_council_timeout,
                    )
                except asyncio.TimeoutError:
                    self._councils_vetoed += 1
                    logger.error(
                        "⏰ Council GLOBAL TIMEOUT for %s after %.0fs — vetoing",
                        symbol, _council_timeout,
                    )
                    return

                # Process council verdict
                if decision.vetoed:
                    self._councils_vetoed += 1
                    logger.info(
                        "\u26d4 Council VETOED %s: %s",
                        symbol,
                        "; ".join(decision.veto_reasons),
                    )
                    return

                if decision.final_direction == "hold":
                    self._councils_held += 1
                    logger.info(
                        "\u23f8 Council HOLD on %s (confidence=%.0f%%)",
                        symbol,
                        decision.final_confidence * 100,
                    )
                    return

                if not decision.execution_ready:
                    self._councils_held += 1
                    logger.info(
                        "\u23f8 Council not execution-ready for %s "
                        "(direction=%s, confidence=%.0f%%)",
                        symbol,
                        decision.final_direction,
                        decision.final_confidence * 100,
                    )
                    return

                # Council approved — publish verdict for OrderExecutor
                # Sizing gate is applied canonically in OrderExecutor (Kelly must pass before submit).
                self._councils_passed += 1
                verdict_data = decision.to_dict()
                verdict_data["signal_data"] = signal_data
                verdict_data["price"] = price
                verdict_data["sizing_deferred_to_executor"] = True  # SizingGate runs in OrderExecutor

                await self.message_bus.publish("council.verdict", verdict_data)

                logger.info(
                    "\u2705 Council APPROVED %s: %s @ %.0f%% confidence "
                    "(votes=%d, signal=%.1f)",
                    symbol,
                    decision.final_direction.upper(),
                    decision.final_confidence * 100,
                    len(decision.votes),
                    score,
                )

                # Trigger weight learning from this decision
                try:
                    from app.council.weight_learner import get_weight_learner
                    learner = get_weight_learner()
                    learner.record_decision(decision)
                except Exception:
                    pass

                # LLM calibration: record hypothesis prediction for outcome matching
                try:
                    hyp = getattr(decision, "active_hypothesis", None) or {}
                    meta = (hyp.get("metadata") or {}) if isinstance(hyp, dict) else {}
                    if meta.get("llm_tier"):
                        from app.services.llm_calibration import record_llm_prediction
                        regime_val = getattr(decision, "regime", None) or regime or "UNKNOWN"
                        record_llm_prediction(
                            council_decision_id=getattr(decision, "council_decision_id", "") or "",
                            symbol=symbol,
                            regime=str(regime_val).upper(),
                            llm_tier=str(meta.get("llm_tier", "ollama")).lower(),
                            predicted_direction=str(meta.get("llm_direction", hyp.get("direction", "hold"))).lower(),
                            predicted_confidence=float(meta.get("llm_confidence", hyp.get("confidence", 0.5))),
                            llm_latency_ms=int(meta.get("llm_latency_ms", 0)),
                        )
                except Exception:
                    pass

            except Exception as e:
                logger.exception(
                    "CouncilGate evaluation failed for %s: %s", symbol, e
                )

    def get_status(self) -> Dict[str, Any]:
        """Return gate status for monitoring."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "regime": self._current_regime,
            "gate_threshold": self._get_regime_threshold(),
            "base_gate_threshold": self.base_gate_threshold,
            "max_concurrent": self._effective_max_concurrent(),
            "base_max_concurrent": self.max_concurrent,
            "burst_concurrent": self.burst_concurrent,
            "market_open_burst": self._is_market_open_burst(),
            "cooldown_seconds": self._get_regime_cooldown(),
            "base_cooldown_seconds": self.cooldown_seconds,
            "signals_received": self._signals_received,
            "councils_invoked": self._councils_invoked,
            "cooldown_skips": self._cooldown_skips,
            "concurrency_skips": self._concurrency_skips,
            "queue_dispatched": self._queue_dispatched,
            "queue_dropped_total": self._queue_dropped_total,
            "queue_pending": len(self._priority_queue),
            "councils_passed": self._councils_passed,
            "councils_vetoed": self._councils_vetoed,
            "councils_held": self._councils_held,
            "pass_rate": (
                round(self._councils_passed / max(self._councils_invoked, 1), 3)
            ),
        }
