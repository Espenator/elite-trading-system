"""Council Gate — bridges SignalEngine → Council → OrderExecutor.

Subscribes to signal.generated on the MessageBus.  When a signal arrives
with score >= gate_threshold the full 13-agent council is invoked.
If the council verdict is execution_ready the signal is re-published as
council.verdict which the OrderExecutor listens on.

This replaces the old direct signal → order path with an intelligent
agent-council-controlled decision layer.

Pipeline (tiered):
  AlpacaStream → MessageBus → SignalEngine → **CouncilGate** → FastCouncil
                                                              ↓ (escalate)
                                                         DeepCouncil → OrderExecutor
  market_data.bar → signal.generated → fast pre-screen → council evaluation
                                                       → council.verdict → order

When ``enable_fast_path=True`` (default) and a signal score is between
``fast_threshold`` and ``gate_threshold``, the fast council pre-screens the
signal first.  If the fast council returns ``escalate=True`` the full deep
council runs.  Signals that score >= ``gate_threshold`` bypass the fast path
and go directly to the deep council (they are already high-confidence).

If ``enable_fast_path=False``, or if the fast path is unavailable, behaviour
falls back to the original single-tier deep evaluation for all signals above
``gate_threshold``.
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
        Minimum signal score to trigger the deep council (default 65).
        Signals at or above this score go straight to the deep council.
    fast_threshold : float
        Minimum signal score to trigger the fast pre-screening council
        (default 45).  Signals between ``fast_threshold`` and
        ``gate_threshold`` are evaluated by the fast council first; only
        those that ``escalate=True`` proceed to the deep council.
        Has no effect when ``enable_fast_path=False``.
    enable_fast_path : bool
        When ``True`` (default), the tiered fast→deep council evaluation is
        used.  When ``False``, all signals at or above ``gate_threshold``
        bypass the fast path and go directly to the deep council (backward-
        compatible behaviour).
    max_concurrent : int
        Maximum concurrent council evaluations to prevent overload.
    cooldown_seconds : int
        Per-symbol cooldown between council evaluations.
    """

    def __init__(
        self,
        message_bus,
        gate_threshold: float = 65.0,
        fast_threshold: float = 45.0,
        enable_fast_path: bool = True,
        max_concurrent: int = 3,
        cooldown_seconds: int = 120,
    ):
        self.message_bus = message_bus
        self.gate_threshold = gate_threshold
        self.fast_threshold = fast_threshold
        self.enable_fast_path = enable_fast_path
        self.max_concurrent = max_concurrent
        self.cooldown_seconds = cooldown_seconds

        self._running = False
        self._start_time: Optional[float] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._symbol_last_eval: Dict[str, float] = {}
        self._signals_received = 0
        self._councils_invoked = 0
        self._councils_passed = 0
        self._councils_vetoed = 0
        self._councils_held = 0
        # Fast-path specific counters
        self._fast_screened = 0    # fast council ran
        self._fast_held = 0        # fast council held (did not escalate)
        self._fast_escalated = 0   # fast council escalated to deep

    async def start(self) -> None:
        """Subscribe to signal.generated and begin gating."""
        self._running = True
        self._start_time = time.time()
        await self.message_bus.subscribe("signal.generated", self._on_signal)
        logger.info(
            "CouncilGate started — threshold=%.0f, fast_threshold=%.0f, "
            "fast_path=%s, max_concurrent=%d, cooldown=%ds",
            self.gate_threshold,
            self.fast_threshold,
            self.enable_fast_path,
            self.max_concurrent,
            self.cooldown_seconds,
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

        # Gate 2: Minimum score check
        # Fast path: score >= fast_threshold AND < gate_threshold → fast pre-screen
        # Direct deep path: score >= gate_threshold
        if score < (
            self.fast_threshold if self.enable_fast_path else self.gate_threshold
        ):
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

        # Route to appropriate evaluation path
        if self.enable_fast_path and score < self.gate_threshold:
            # Fast-pre-screen path: score in [fast_threshold, gate_threshold)
            asyncio.create_task(self._evaluate_tiered(symbol, signal_data))
        else:
            # Direct deep path: score >= gate_threshold (or fast path disabled)
            asyncio.create_task(self._evaluate_with_council(symbol, signal_data))

    async def _evaluate_with_council(
        self, symbol: str, signal_data: Dict[str, Any]
    ) -> None:
        """Run the full deep council for the symbol (direct path, no fast pre-screen).

        Used when ``enable_fast_path=False`` or when the signal score is at or
        above ``gate_threshold`` (already high-confidence, no need to pre-screen).
        """
        async with self._semaphore:
            self._symbol_last_eval[symbol] = time.time()
            self._councils_invoked += 1

            try:
                from app.council.runner import run_council

                score = signal_data.get("score", 0)
                regime = signal_data.get("regime", "UNKNOWN")
                price = signal_data.get("close", signal_data.get("price", 0))

                logger.info(
                    "⚙ CouncilGate: invoking council for %s "
                    "(signal=%.1f, regime=%s, price=$%.2f)",
                    symbol,
                    score,
                    regime,
                    price,
                )

                context = {
                    "signal_score": score,
                    "signal_label": signal_data.get("label", ""),
                    "signal_regime": regime,
                    "signal_price": price,
                    "signal_volume": signal_data.get("volume", 0),
                    "signal_timestamp": signal_data.get("timestamp", ""),
                    "source": "council_gate",
                }

                decision = await run_council(
                    symbol=symbol,
                    timeframe="1d",
                    context=context,
                )

                await self._process_decision(symbol, score, signal_data, price, decision)

            except Exception as e:
                logger.exception(
                    "CouncilGate evaluation failed for %s: %s", symbol, e
                )

    async def _evaluate_tiered(
        self, symbol: str, signal_data: Dict[str, Any]
    ) -> None:
        """Run the fast pre-screen, then escalate to the deep council if warranted.

        This method handles signals with scores in the range
        ``[fast_threshold, gate_threshold)``.  The fast council runs first; if
        it escalates the signal, the full deep council is invoked.

        Args:
            symbol:      Ticker symbol being evaluated.
            signal_data: Raw signal dict from the MessageBus.
        """
        async with self._semaphore:
            self._symbol_last_eval[symbol] = time.time()
            self._fast_screened += 1

            try:
                from app.council.fast_council import run_fast_council

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
                    "source": "council_gate_fast",
                }

                logger.info(
                    "⚡ CouncilGate: fast pre-screen for %s "
                    "(signal=%.1f, regime=%s, price=$%.2f)",
                    symbol,
                    score,
                    regime,
                    price,
                )

                fast_result = await run_fast_council(
                    symbol=symbol,
                    timeframe="1d",
                    context=context,
                )

                if not fast_result.escalate:
                    # Fast path dropped the signal — no deep council needed
                    self._fast_held += 1
                    if fast_result.vetoed:
                        logger.info(
                            "⛔ Fast council VETOED %s: %s (%.0fms)",
                            symbol,
                            "; ".join(fast_result.veto_reasons),
                            fast_result.latency_ms,
                        )
                    else:
                        logger.info(
                            "⏸ Fast council HOLD %s: %s (%.0fms)",
                            symbol,
                            fast_result.reasoning,
                            fast_result.latency_ms,
                        )
                    return

                # Fast council escalated — run full deep council
                self._fast_escalated += 1
                self._councils_invoked += 1
                logger.info(
                    "⚙ CouncilGate: fast council ESCALATED %s → deep council "
                    "(%s @ %.0f%%, %.0fms)",
                    symbol,
                    fast_result.direction.upper(),
                    fast_result.confidence * 100,
                    fast_result.latency_ms,
                )

                from app.council.runner import run_council

                # Carry fast-council intelligence into the deep council context
                context["source"] = "council_gate"
                context["fast_council_result"] = fast_result.to_dict()

                decision = await run_council(
                    symbol=symbol,
                    timeframe="1d",
                    context=context,
                )

                await self._process_decision(symbol, score, signal_data, price, decision)

            except Exception as exc:
                logger.exception(
                    "CouncilGate tiered evaluation failed for %s: %s", symbol, exc
                )

    async def _process_decision(
        self,
        symbol: str,
        score: float,
        signal_data: Dict[str, Any],
        price: float,
        decision,
    ) -> None:
        """Handle the outcome of a council decision (deep path, shared logic).

        Increments counters, logs the result, and publishes ``council.verdict``
        when the decision is execution-ready.

        Args:
            symbol:      Ticker symbol.
            score:       Original signal score.
            signal_data: Raw signal dict.
            price:       Reference price from the signal.
            decision:    :class:`~app.council.schemas.DecisionPacket` from the council.
        """
        if decision.vetoed:
            self._councils_vetoed += 1
            logger.info(
                "⛔ Council VETOED %s: %s",
                symbol,
                "; ".join(decision.veto_reasons),
            )
            return

        if decision.final_direction == "hold":
            self._councils_held += 1
            logger.info(
                "⏸ Council HOLD on %s (confidence=%.0f%%)",
                symbol,
                decision.final_confidence * 100,
            )
            return

        if not decision.execution_ready:
            self._councils_held += 1
            logger.info(
                "⏸ Council not execution-ready for %s "
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
            "✅ Council APPROVED %s: %s @ %.0f%% confidence "
            "(votes=%d, signal=%.1f, tier=%s)",
            symbol,
            decision.final_direction.upper(),
            decision.final_confidence * 100,
            len(decision.votes),
            score,
            decision.council_tier,
        )

        # Trigger weight learning from this decision
        try:
            from app.council.weight_learner import get_weight_learner
            learner = get_weight_learner()
            learner.record_decision(decision)
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        """Return gate status for monitoring."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "uptime_seconds": round(uptime, 1),
            "gate_threshold": self.gate_threshold,
            "fast_threshold": self.fast_threshold,
            "enable_fast_path": self.enable_fast_path,
            "max_concurrent": self.max_concurrent,
            "cooldown_seconds": self.cooldown_seconds,
            "signals_received": self._signals_received,
            "councils_invoked": self._councils_invoked,
            "councils_passed": self._councils_passed,
            "councils_vetoed": self._councils_vetoed,
            "councils_held": self._councils_held,
            "fast_screened": self._fast_screened,
            "fast_held": self._fast_held,
            "fast_escalated": self._fast_escalated,
            "pass_rate": (
                round(self._councils_passed / max(self._councils_invoked, 1), 3)
            ),
            "fast_escalation_rate": (
                round(self._fast_escalated / max(self._fast_screened, 1), 3)
            ),
        }
