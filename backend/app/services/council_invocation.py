"""Council invocation wiring.

Goal: enforce a single runtime path from signal.generated -> council.verdict.

- Canonical path: CouncilGate (invokes council, publishes council.verdict).
- Fallback path: optional, explicitly enabled by env flag, and safe by default:
  publishes non-executable verdicts for observability (execution_ready=False).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

SignalHandler = Callable[[Dict[str, Any]], Awaitable[None]]


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


async def setup_council_invocation(message_bus, *, llm_enabled: bool, council_enabled: bool):
    """Install exactly one council invoker.

    Returns:
        A dict with keys:
          - mode: "gate" | "fallback" | "disabled"
          - gate: CouncilGate instance when mode == "gate"
    """
    gate_enabled = (
        _truthy_env("COUNCIL_GATE_ENABLED", "true") and llm_enabled and council_enabled
    )

    if gate_enabled:
        from app.council.council_gate import CouncilGate

        gate = CouncilGate(
            message_bus=message_bus,
            gate_threshold=float(os.getenv("COUNCIL_GATE_THRESHOLD", "65.0")),
            max_concurrent=int(os.getenv("COUNCIL_MAX_CONCURRENT", "3")),
            cooldown_seconds=int(os.getenv("COUNCIL_COOLDOWN_SECS", "120")),
        )
        await gate.start()
        logger.info("✅ Council invocation: CouncilGate enabled (canonical path)")
        return {"mode": "gate", "gate": gate}

    # Gate disabled. Optional safe fallback.
    fallback_enabled = _truthy_env("COUNCIL_VERDICT_FALLBACK_ENABLED", "false")
    if not fallback_enabled:
        logger.warning(
            "⚠ Council invocation DISABLED (no CouncilGate; fallback off). "
            "No component will publish council.verdict from signal.generated."
        )
        return {"mode": "disabled", "gate": None}

    auto_execute = _truthy_env("AUTO_EXECUTE_TRADES", "false")
    if auto_execute:
        # Hard safety: never allow bypass path while live execution is enabled.
        logger.critical(
            "🛑 Refusing to enable COUNCIL_VERDICT_FALLBACK_ENABLED while AUTO_EXECUTE_TRADES=true. "
            "Disable AUTO_EXECUTE_TRADES or re-enable CouncilGate."
        )
        return {"mode": "disabled", "gate": None}

    allow_executable = _truthy_env("COUNCIL_FALLBACK_EXECUTION_READY", "false")
    if allow_executable:
        logger.critical(
            "🛑 COUNCIL_FALLBACK_EXECUTION_READY=true requested, but fallback is intended for observability only. "
            "Ignoring and forcing execution_ready=False."
        )
        allow_executable = False

    async def _signal_to_verdict_fallback(signal_data: Dict[str, Any]) -> None:
        """Observability-only bypass: emit a non-executable verdict for dashboards."""
        try:
            from app.core.score_semantics import (
                coerce_gate_threshold_0_100,
                coerce_signal_score_0_100,
                score_to_final_confidence_0_1,
            )

            score_f = coerce_signal_score_0_100(
                signal_data.get("score", 0),
                context="Signal->Verdict fallback",
            )
            gate_threshold = coerce_gate_threshold_0_100(
                os.getenv("COUNCIL_GATE_THRESHOLD", "65.0"),
                context="Signal->Verdict fallback",
            )
            if score_f < gate_threshold:
                return

            d = (signal_data.get("direction") or "").strip().lower()
            if d in ("buy", "long", "bullish", "up"):
                final_direction = "buy"
            elif d in ("sell", "short", "bearish", "down"):
                final_direction = "sell"
            else:
                final_direction = "hold"

            await message_bus.publish(
                "council.verdict",
                {
                    "symbol": signal_data.get("symbol", ""),
                    "final_direction": final_direction,
                    "final_confidence": score_to_final_confidence_0_1(
                        score_f, context="Signal->Verdict fallback"
                    ),
                    # Safety: by default, this MUST NOT be executable.
                    "execution_ready": bool(allow_executable),
                    "vetoed": not bool(allow_executable),
                    "votes": [],
                    "council_reasoning": (
                        "CouncilGate disabled — fallback verdict (observability-only)"
                    ),
                    "signal_data": signal_data,
                    "price": signal_data.get("close", signal_data.get("price", 0)),
                    "source": "council_fallback",
                },
            )
        except Exception:
            logger.exception("Signal->Verdict fallback failed")

    await message_bus.subscribe("signal.generated", _signal_to_verdict_fallback)
    logger.warning(
        "⚠ Council invocation: FALLBACK subscriber enabled (COUNCIL_VERDICT_FALLBACK_ENABLED=true). "
        "Publishing non-executable council.verdict for observability."
    )
    return {"mode": "fallback", "gate": None}

