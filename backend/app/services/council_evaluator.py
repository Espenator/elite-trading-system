"""Council Evaluator — bridges signal engine to council DAG.

Subscribes to signal.generated events and triggers full 17-agent council
evaluation when signal strength warrants it. The council decision then
gates order execution, replacing the direct signal→order flow.

Pipeline:
    market_data.bar → SignalEngine → signal.generated
        → CouncilEvaluator → council.verdict
            → OrderExecutor (listens to council.verdict)

Throttling:
    - Per-symbol cooldown (default 60s) prevents evaluation storms
    - Max concurrent evaluations capped (default 3)
    - Minimum signal score threshold (default 70)
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


class CouncilEvaluator:
    """Bridges signal engine to 17-agent council for intelligent trade gating."""

    def __init__(
        self,
        message_bus,
        min_signal_score: float = 70.0,
        cooldown_seconds: int = 60,
        max_concurrent: int = 3,
    ):
        self.message_bus = message_bus
        self.min_signal_score = min_signal_score
        self.cooldown_seconds = cooldown_seconds
        self.max_concurrent = max_concurrent

        self._running = False
        self._last_eval: Dict[str, float] = {}  # symbol -> timestamp
        self._active_evals: Set[str] = set()
        self._eval_count = 0
        self._skip_count = 0

    async def start(self) -> None:
        """Subscribe to signal events and begin evaluation loop."""
        self._running = True
        await self.message_bus.subscribe("signal.generated", self._on_signal)
        logger.info(
            "CouncilEvaluator started — min_score=%.0f, cooldown=%ds, max_concurrent=%d",
            self.min_signal_score,
            self.cooldown_seconds,
            self.max_concurrent,
        )

    async def stop(self) -> None:
        """Stop processing."""
        self._running = False
        await self.message_bus.unsubscribe("signal.generated", self._on_signal)
        logger.info(
            "CouncilEvaluator stopped — %d evaluations, %d skipped",
            self._eval_count,
            self._skip_count,
        )

    async def _on_signal(self, signal_data: Dict[str, Any]) -> None:
        """Handle a signal.generated event — decide whether to trigger council."""
        if not self._running:
            return

        symbol = signal_data.get("symbol", "")
        score = signal_data.get("score", 0)

        if not symbol:
            return

        # Gate 1: Signal score must meet threshold
        if score < self.min_signal_score:
            return

        # Gate 2: Per-symbol cooldown
        now = time.time()
        last = self._last_eval.get(symbol, 0)
        if now - last < self.cooldown_seconds:
            self._skip_count += 1
            logger.debug(
                "Council eval skipped for %s — cooldown (%ds remaining)",
                symbol,
                int(self.cooldown_seconds - (now - last)),
            )
            return

        # Gate 3: Max concurrent evaluations
        if len(self._active_evals) >= self.max_concurrent:
            self._skip_count += 1
            logger.debug(
                "Council eval skipped for %s — %d concurrent evals active",
                symbol,
                len(self._active_evals),
            )
            return

        # Launch council evaluation as background task
        self._last_eval[symbol] = now
        self._active_evals.add(symbol)
        asyncio.create_task(self._evaluate(symbol, signal_data))

    async def _evaluate(self, symbol: str, signal_data: Dict[str, Any]) -> None:
        """Run full 17-agent council evaluation for a symbol."""
        start = time.time()
        try:
            from app.council.runner import run_council

            logger.info(
                "Council evaluation triggered for %s (signal_score=%.1f)",
                symbol,
                signal_data.get("score", 0),
            )

            decision = await asyncio.wait_for(
                run_council(
                    symbol=symbol,
                    timeframe="1d",
                    context={
                        "trigger": "signal_engine",
                        "signal_score": signal_data.get("score", 0),
                        "signal_label": signal_data.get("label", ""),
                        "signal_price": signal_data.get("price", 0),
                    },
                ),
                timeout=30.0,  # Hard 30s timeout for full council
            )

            elapsed_ms = (time.time() - start) * 1000
            self._eval_count += 1

            logger.info(
                "Council verdict for %s: %s @ %.0f%% confidence "
                "(vetoed=%s, ready=%s, latency=%.0fms)",
                symbol,
                decision.final_direction.upper(),
                decision.final_confidence * 100,
                decision.vetoed,
                decision.execution_ready,
                elapsed_ms,
            )

            # Council verdict is already published to message bus by runner.py
            # OrderExecutor subscribes to council.verdict for execution decisions

        except asyncio.TimeoutError:
            logger.warning(
                "Council evaluation timed out for %s after 30s", symbol
            )
        except Exception as e:
            logger.error(
                "Council evaluation failed for %s: %s", symbol, e, exc_info=True
            )
        finally:
            self._active_evals.discard(symbol)

    def get_status(self) -> Dict[str, Any]:
        """Return evaluator status for monitoring."""
        return {
            "running": self._running,
            "evaluations_completed": self._eval_count,
            "evaluations_skipped": self._skip_count,
            "active_evaluations": list(self._active_evals),
            "min_signal_score": self.min_signal_score,
            "cooldown_seconds": self.cooldown_seconds,
            "max_concurrent": self.max_concurrent,
        }
