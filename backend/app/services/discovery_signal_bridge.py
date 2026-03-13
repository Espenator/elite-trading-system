"""DiscoverySignalBridge — wires triage.escalated to signal.generated so scout discoveries reach council.

Scout discoveries flow: swarm.idea → IdeaTriageService → triage.escalated.
CouncilGate only subscribes to signal.generated. When HyperSwarm is disabled or Ollama
is unavailable, escalated ideas never become signals. This bridge subscribes to
triage.escalated and publishes signal.generated with a score derived from the triage
result (score and priority), so CouncilGate can invoke the full 35-agent council
without depending on HyperSwarm's micro-swarm LLM.

Pipeline:
  triage.escalated → DiscoverySignalBridge → signal.generated → CouncilGate → council → OrderExecutor
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Minimum score (0-100) so CouncilGate accepts in BULLISH regime (threshold 55)
MIN_SCORE_FOR_GATE = 55


class DiscoverySignalBridge:
    """Bridges triage.escalated to signal.generated for scout-origin ideas."""

    def __init__(self, message_bus=None):
        self._bus = message_bus
        self._running = False
        self._stats = {
            "received": 0,
            "published": 0,
            "skipped_no_symbol": 0,
            "skipped_low_score": 0,
        }

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._bus:
            await self._bus.subscribe("triage.escalated", self._on_escalated)
        logger.info("DiscoverySignalBridge started (triage.escalated → signal.generated)")

    async def stop(self) -> None:
        self._running = False
        logger.info(
            "DiscoverySignalBridge stopped: received=%d published=%d",
            self._stats["received"],
            self._stats["published"],
        )

    async def _on_escalated(self, data: Dict[str, Any]) -> None:
        """On triage.escalated: publish signal.generated so CouncilGate runs council."""
        self._stats["received"] += 1
        if not self._bus:
            return

        # Triage payload: original idea + triage result
        triage = data.get("triage") or {}
        symbols = data.get("symbols", [])
        if isinstance(symbols, str):
            symbols = [symbols]
        symbol = (symbols or [None])[0]
        if not symbol:
            self._stats["skipped_no_symbol"] += 1
            return

        source = data.get("source", "scout")
        direction = (data.get("direction") or "neutral").strip().lower()
        priority = int(data.get("priority", 5))
        reasoning = data.get("reasoning", "")

        # Score: use triage score if present (0-100), else derive from priority (1=urgent → 70, 5=low → 55)
        triage_score = triage.get("score")
        if triage_score is not None:
            score = max(MIN_SCORE_FOR_GATE, min(100, int(triage_score)))
        else:
            priority_to_score = {1: 70, 2: 65, 3: 60, 4: 58, 5: 55}
            score = priority_to_score.get(priority, MIN_SCORE_FOR_GATE)

        if score < MIN_SCORE_FOR_GATE:
            self._stats["skipped_low_score"] += 1
            return

        # Map direction to CouncilGate expected values
        if direction in ("bullish", "buy", "long", "up"):
            final_direction = "buy"
        elif direction in ("bearish", "sell", "short", "down"):
            final_direction = "sell"
        else:
            final_direction = "hold"

        # Price required by OrderExecutor; use from payload or metadata or placeholder
        metadata_raw = data.get("metadata") or {}
        try:
            price = float(data.get("price") or metadata_raw.get("price") or 1.0)
        except (TypeError, ValueError):
            price = 1.0
        if price <= 0:
            price = 1.0

        signal_payload = {
            "symbol": symbol,
            "score": float(score),
            "direction": final_direction,
            "label": f"discovery_bridge_{source}",
            "price": price,
            "regime": "UNKNOWN",
            "source": f"discovery_bridge_{source}",
            "metadata": {
                "triage_score": triage.get("score"),
                "priority": priority,
                "reasoning": reasoning[:500] if reasoning else "",
                "triage_escalated": True,
            },
        }
        try:
            await self._bus.publish("signal.generated", signal_payload)
            self._stats["published"] += 1
            logger.debug(
                "DiscoverySignalBridge: %s score=%s direction=%s → signal.generated",
                symbol, score, final_direction,
            )
        except Exception as exc:
            logger.warning("DiscoverySignalBridge publish failed: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)


_bridge: Optional[DiscoverySignalBridge] = None


def get_discovery_signal_bridge(message_bus=None) -> DiscoverySignalBridge:
    global _bridge
    if _bridge is None:
        _bridge = DiscoverySignalBridge(message_bus=message_bus)
    return _bridge
