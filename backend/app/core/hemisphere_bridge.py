"""Hemisphere Bridge — PC-1 (Left Brain) ↔ PC-2 (Right Brain) communication.

PC-1 "Left Hemisphere": Analytical — runs FastAPI, council DAG, order execution
PC-2 "Right Hemisphere": Intuition — runs Ollama LLMs, ML training, brain_service

The bridge provides:
  - Heartbeat monitoring (PC-2 health)
  - Intuition requests (PC-1 → PC-2: "what does the LLM think?")
  - Decision forwarding (PC-1 → PC-2: "here's what we decided")
  - Outcome forwarding (PC-1 → PC-2: "here's what happened")

Communication flows through gRPC (brain_service) for LLM inference
and HTTP for Ollama health/model management.

Usage:
    from app.core.hemisphere_bridge import get_hemisphere_bridge
    bridge = get_hemisphere_bridge()
    await bridge.start()
    intuition = await bridge.request_intuition("AAPL", context={...})
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class HemisphereBridge:
    """Manages communication between PC-1 (analytical) and PC-2 (intuition).

    Parameters
    ----------
    pc2_host : str
        PC-2 hostname/IP.
    brain_port : int
        gRPC brain_service port on PC-2.
    ollama_port : int
        Ollama API port on PC-2.
    heartbeat_interval : float
        Seconds between heartbeat checks.
    """

    def __init__(
        self,
        pc2_host: Optional[str] = None,
        brain_port: int = 50051,
        ollama_port: int = 11434,
        heartbeat_interval: float = 30.0,
    ):
        self.pc2_host = pc2_host or os.getenv("BRAIN_HOST", "localhost")
        self.brain_port = int(os.getenv("BRAIN_PORT", str(brain_port)))
        self.ollama_port = int(os.getenv("OLLAMA_PORT", str(ollama_port)))
        self.heartbeat_interval = heartbeat_interval

        # State
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._pc2_healthy = False
        self._last_heartbeat: float = 0.0
        self._heartbeat_failures: int = 0

        # Metrics
        self._intuition_requests: int = 0
        self._decisions_forwarded: int = 0
        self._outcomes_forwarded: int = 0
        self._start_time: Optional[float] = None

        # MessageBus subscription
        self._bus = None

    async def start(self) -> None:
        """Start the hemisphere bridge with heartbeat monitoring."""
        self._running = True
        self._start_time = time.time()

        # Initial health check
        self._pc2_healthy = await self._ping_pc2()

        # Start heartbeat loop
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Subscribe to MessageBus events for forwarding
        try:
            from app.core.message_bus import get_message_bus
            self._bus = get_message_bus()

            # Forward council decisions to PC-2
            await self._bus.subscribe(
                "council.evaluation_complete", self._on_decision
            )
            # Forward trade outcomes to PC-2
            await self._bus.subscribe("trade.resolved", self._on_outcome)

            logger.info(
                "HemisphereBridge started: PC-2=%s (brain=%d, ollama=%d) healthy=%s",
                self.pc2_host, self.brain_port, self.ollama_port, self._pc2_healthy,
            )
        except Exception as e:
            logger.warning("HemisphereBridge MessageBus wiring failed: %s", e)

    async def stop(self) -> None:
        """Stop the bridge and cancel heartbeat."""
        self._running = False
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._bus:
            try:
                await self._bus.unsubscribe(
                    "council.evaluation_complete", self._on_decision
                )
                await self._bus.unsubscribe("trade.resolved", self._on_outcome)
            except Exception:
                pass

        logger.info("HemisphereBridge stopped")

    async def request_intuition(
        self, symbol: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Request intuition from PC-2's LLM (brain_service or Ollama).

        Falls back to local LLM router if PC-2 is unavailable.
        """
        self._intuition_requests += 1

        if not self._pc2_healthy:
            return await self._local_fallback_intuition(symbol, context)

        try:
            from app.services.brain_client import get_brain_client
            client = get_brain_client()

            prompt = self._build_intuition_prompt(symbol, context or {})
            result = await client.generate(prompt)

            return {
                "symbol": symbol,
                "intuition": result.get("text", ""),
                "source": "pc2_brain_service",
                "latency_ms": result.get("latency_ms", 0),
                "pc2_healthy": True,
            }
        except Exception as e:
            logger.debug("PC-2 intuition request failed: %s", e)
            return await self._local_fallback_intuition(symbol, context)

    async def _local_fallback_intuition(
        self, symbol: str, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fall back to local LLM router when PC-2 is unavailable."""
        try:
            from app.core.llm_router import get_llm_router
            router = get_llm_router()

            prompt = self._build_intuition_prompt(symbol, context or {})
            response = await router.route(
                prompt=prompt,
                complexity="medium",
                system_prompt=(
                    "You are a trading intuition engine. Analyze the context and "
                    "provide a brief directional bias (bullish/bearish/neutral) "
                    "with key reasons. Be concise."
                ),
                max_tokens=256,
            )

            return {
                "symbol": symbol,
                "intuition": response.text,
                "source": f"local_fallback_{response.tier.value}",
                "latency_ms": response.latency_ms,
                "pc2_healthy": False,
            }
        except Exception as e:
            logger.debug("Local fallback intuition failed: %s", e)
            return {
                "symbol": symbol,
                "intuition": "",
                "source": "unavailable",
                "error": str(e),
                "pc2_healthy": False,
            }

    def _build_intuition_prompt(self, symbol: str, context: Dict[str, Any]) -> str:
        """Build an intuition prompt from symbol and context."""
        parts = [f"Analyze {symbol} for a trading decision."]
        if context.get("regime"):
            parts.append(f"Current regime: {context['regime']}")
        if context.get("signal_score"):
            parts.append(f"Signal score: {context['signal_score']}")
        if context.get("signal_price"):
            parts.append(f"Price: ${context['signal_price']}")
        if context.get("prior_votes"):
            parts.append(f"Prior agent votes: {context['prior_votes']}")
        parts.append("What is your directional intuition and key reasoning?")
        return "\n".join(parts)

    async def _on_decision(self, decision_data: Dict[str, Any]) -> None:
        """Forward council decision to PC-2 for learning."""
        self._decisions_forwarded += 1
        if not self._pc2_healthy:
            return

        try:
            # Forward via gRPC brain_service if available
            from app.services.brain_client import get_brain_client
            client = get_brain_client()
            await client.forward_decision(decision_data)
        except Exception as e:
            logger.debug("Decision forwarding to PC-2 failed: %s", e)

    async def _on_outcome(self, outcome_data: Dict[str, Any]) -> None:
        """Forward trade outcome to PC-2 for learning."""
        self._outcomes_forwarded += 1
        if not self._pc2_healthy:
            return

        try:
            from app.services.brain_client import get_brain_client
            client = get_brain_client()
            await client.forward_outcome(outcome_data)
        except Exception as e:
            logger.debug("Outcome forwarding to PC-2 failed: %s", e)

    async def _heartbeat_loop(self) -> None:
        """Periodically check PC-2 health."""
        while self._running:
            try:
                self._pc2_healthy = await self._ping_pc2()
                self._last_heartbeat = time.time()

                if self._pc2_healthy:
                    self._heartbeat_failures = 0
                else:
                    self._heartbeat_failures += 1
                    if self._heartbeat_failures % 10 == 1:
                        logger.warning(
                            "PC-2 heartbeat failed (%d consecutive)",
                            self._heartbeat_failures,
                        )
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("Heartbeat error: %s", e)
                self._pc2_healthy = False
                self._heartbeat_failures += 1

            await asyncio.sleep(self.heartbeat_interval)

    async def _ping_pc2(self) -> bool:
        """Ping PC-2 Ollama API to check if it's alive."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"http://{self.pc2_host}:{self.ollama_port}/api/tags"
                )
                return resp.status_code == 200
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """Return bridge status for health endpoint."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "running": self._running,
            "pc2_host": self.pc2_host,
            "pc2_healthy": self._pc2_healthy,
            "heartbeat_failures": self._heartbeat_failures,
            "last_heartbeat": (
                datetime.fromtimestamp(self._last_heartbeat, tz=timezone.utc).isoformat()
                if self._last_heartbeat
                else None
            ),
            "intuition_requests": self._intuition_requests,
            "decisions_forwarded": self._decisions_forwarded,
            "outcomes_forwarded": self._outcomes_forwarded,
            "uptime_seconds": round(uptime, 1),
        }


# Module-level singleton
_bridge_instance: Optional[HemisphereBridge] = None


def get_hemisphere_bridge() -> HemisphereBridge:
    """Get or create the global HemisphereBridge singleton."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = HemisphereBridge()
    return _bridge_instance
