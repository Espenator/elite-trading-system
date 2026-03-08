"""Council Gate — bridges SignalEngine → Council → OrderExecutor.

Subscribes to signal.generated on the MessageBus.  When a signal arrives
with score >= gate_threshold the council pipeline is invoked.

Two-tier council pipeline (Issue #38 — E4):
    1. FastCouncil (5 agents, <200 ms) — quick pre-screening.
       If FastCouncil says "hold" / veto, skip the full council entirely.
    2. Full Council (35 agents, ~1 s) — invoked only for promising signals.

Tier-1 can be disabled via ``FAST_COUNCIL_ENABLED=false`` to restore the
original single-tier behaviour.

Pipeline:
  AlpacaStream → MessageBus → SignalEngine → **CouncilGate**
    → FastCouncil (pre-screen)  — skip if hold/veto
    → Full Council (35 agents)  — emit council.verdict
    → OrderExecutor
  market_data.bar → signal.generated → council evaluation → council.verdict → order
"""
import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CouncilGate:
    """Event-driven gate that invokes the council on high-score signals.

    Parameters
    ----------
    message_bus : MessageBus
        The async event bus.
    gate_threshold : float
        Minimum signal score to trigger council evaluation (default 65).
    max_concurrent : int
        Maximum concurrent council evaluations to prevent overload.
    cooldown_seconds : int
        Per-symbol cooldown between council evaluations.
    """

    def __init__(
        self,
        message_bus,
        gate_threshold: float = 65.0,
        max_concurrent: int = 3,
        cooldown_seconds: int = 120,
        fast_council_enabled: Optional[bool] = None,
    ):
        self.message_bus = message_bus
        self.gate_threshold = gate_threshold
        self.max_concurrent = max_concurrent
        self.cooldown_seconds = cooldown_seconds

        # Fast council tier (E4) — enabled unless explicitly disabled
        if fast_council_enabled is None:
            fast_council_enabled = (
                os.getenv("FAST_COUNCIL_ENABLED", "true").lower() != "false"
            )
        self.fast_council_enabled = fast_council_enabled

        self._running = False
        self._start_time: Optional[float] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._symbol_last_eval: Dict[str, float] = {}
        self._signals_received = 0
        self._councils_invoked = 0
        self._councils_passed = 0
        self._councils_vetoed = 0
        self._councils_held = 0
        # Fast-council specific counter
        self._fast_skipped = 0  # Signals short-circuited by FastCouncil

    async def start(self) -> None:
        """Subscribe to signal.generated and begin gating."""
        self._running = True
        self._start_time = time.time()
        await self.message_bus.subscribe("signal.generated", self._on_signal)
        logger.info(
            "CouncilGate started — threshold=%.0f, max_concurrent=%d, cooldown=%ds, fast_council=%s",
            self.gate_threshold,
            self.max_concurrent,
            self.cooldown_seconds,
            self.fast_council_enabled,
        )

    async def stop(self) -> None:
        """Unsubscribe and stop."""
        self._running = False
        await self.message_bus.unsubscribe("signal.generated", self._on_signal)
        logger.info(
            "CouncilGate stopped — %d signals, %d councils, %d passed, %d vetoed, %d held",
            self._signals_received,
            self._councils_invoked,
            self._councils_passed,
            self._councils_vetoed,
            self._councils_held,
        )

    async def _on_signal(self, signal_data: Dict[str, Any]) -> None:
        """Handle incoming signal — gate and invoke council if warranted."""
        if not self._running:
            return

        self._signals_received += 1
        symbol = signal_data.get("symbol", "")
        score = signal_data.get("score", 0)
        source = signal_data.get("source", "")

        if not symbol:
            return

        # Gate 1: Mock source guard — never trade on mock/fake data
        if source and "mock" in source.lower():
            logger.debug("CouncilGate: skipping mock signal for %s", symbol)
            return

        # Gate 2: Score threshold
        if score < self.gate_threshold:
            return

        # Gate 3: Per-symbol cooldown
        now = time.time()
        last_eval = self._symbol_last_eval.get(symbol, 0)
        if now - last_eval < self.cooldown_seconds:
            return

        # Gate 4: Concurrency limit
        if self._semaphore.locked():
            logger.debug(
                "CouncilGate: max concurrent evaluations reached, skipping %s",
                symbol,
            )
            return

        # Launch council evaluation (non-blocking)
        asyncio.create_task(self._evaluate_with_council(symbol, signal_data))

    async def _evaluate_with_council(
        self, symbol: str, signal_data: Dict[str, Any]
    ) -> None:
        """Run the two-tier council pipeline for the symbol.

        Tier 1: FastCouncil (5 agents, <200 ms) — pre-screen.
        Tier 2: Full Council (35 agents) — invoked only when Tier 1 passes.
        """
        async with self._semaphore:
            self._symbol_last_eval[symbol] = time.time()
            self._councils_invoked += 1

            try:
                score = signal_data.get("score", 0)
                regime = signal_data.get("regime", "UNKNOWN")
                price = signal_data.get("close", signal_data.get("price", 0))

                context = {
                    "signal_score": score,
                    "signal_label": signal_data.get("label", ""),
                    "signal_regime": regime,
                    "signal_price": price,
                    "signal_volume": signal_data.get("volume", 0),
                    "signal_timestamp": signal_data.get("timestamp", ""),
                    "source": "council_gate",
                }

                # ── Tier 1: FastCouncil pre-screen (E4) ──────────────────
                if self.fast_council_enabled:
                    from app.council.fast_council import run_fast_council
                    features = signal_data.get("features", {})
                    fast_result = await run_fast_council(
                        symbol=symbol,
                        features=features,
                        context=context,
                    )
                    if fast_result.skip_deep:
                        self._fast_skipped += 1
                        if fast_result.veto:
                            self._councils_vetoed += 1
                            logger.info(
                                "⚡ FastCouncil VETO %s (%s) — skipping deep council",
                                symbol,
                                "; ".join(fast_result.veto_reasons),
                            )
                        else:
                            self._councils_held += 1
                            logger.debug(
                                "⚡ FastCouncil HOLD %s (conf=%.2f, %.1fms) — skipping deep council",
                                symbol,
                                fast_result.confidence,
                                fast_result.latency_ms,
                            )
                        return
                    logger.debug(
                        "⚡ FastCouncil PASS %s → %s (conf=%.2f, %.1fms) — escalating to full council",
                        symbol,
                        fast_result.direction,
                        fast_result.confidence,
                        fast_result.latency_ms,
                    )
                    # Enrich context with fast council result for full council agents
                    context["fast_council"] = fast_result.to_dict()

                # ── Tier 2: Full Council ──────────────────────────────────
                from app.council.runner import run_council

                logger.info(
                    "⚙ CouncilGate: invoking full council for %s "
                    "(signal=%.1f, regime=%s, price=$%.2f)",
                    symbol,
                    score,
                    regime,
                    price,
                )

                decision = await run_council(
                    symbol=symbol,
                    timeframe="1d",
                    context=context,
                )

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
                self._councils_passed += 1
                verdict_data = decision.to_dict()
                verdict_data["signal_data"] = signal_data
                verdict_data["price"] = price

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
            "gate_threshold": self.gate_threshold,
            "max_concurrent": self.max_concurrent,
            "cooldown_seconds": self.cooldown_seconds,
            "fast_council_enabled": self.fast_council_enabled,
            "signals_received": self._signals_received,
            "councils_invoked": self._councils_invoked,
            "councils_passed": self._councils_passed,
            "councils_vetoed": self._councils_vetoed,
            "councils_held": self._councils_held,
            "fast_skipped": self._fast_skipped,
            "pass_rate": (
                round(self._councils_passed / max(self._councils_invoked, 1), 3)
            ),
        }
