#!/usr/bin/env python3
"""
lstm_bridge_service.py - Elite LSTM -> OpenClaw Redis Bridge
Apex Predator Convergence: Fusion Layer

Standalone async daemon that continuously polls the Embodier Trader
FastAPI backend for real-time LSTM predictions, publishes structured JSON
to the Redis Blackboard channel `signals.ml_predictions`, and injects
them into the ApexOrchestrator's ToT prompt context.

Architecture:
    Elite FastAPI (PC2 GPU) --httpx--> lstm_bridge_service --aioredis--> Redis
                                                           --blackboard--> ApexOrchestrator

Runs on PC1 (ESPENMAIN) alongside the OpenClaw swarm.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

try:
    import aioredis
except ImportError:
    aioredis = None

from ..streaming.streaming_engine import (
    Blackboard,
    BlackboardMessage,
    Topic,
    get_blackboard,
)

logger = logging.getLogger(__name__)

# ============================================================

from ..config import ELITE_API_URL, ELITE_API_PREFIX
# Configuration
# ============================================================
ELITE_BASE_URL = ELITE_API_URL  # From config.py, uses ELITE_API_URL env var
ELITE_SIGNALS_ENDPOINT = f"{ELITE_BASE_URL}{ELITE_API_PREFIX}/openclaw/signals/latest"
ELITE_ACTIVE_ENDPOINT = f"{ELITE_BASE_URL}{ELITE_API_PREFIX}/openclaw/signals/active"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_CHANNEL = "signals.ml_predictions"  # Channel for LSTM predictions
OPENCLAW_BRIDGE_TOKEN = os.getenv("OPENCLAW_BRIDGE_TOKEN", "")

POLL_INTERVAL_SECONDS = 30
MAX_BACKOFF_SECONDS = 300
INITIAL_BACKOFF_SECONDS = 2
HTTPX_TIMEOUT = 15.0

# JSON Schema for Redis payload
PREDICTION_SCHEMA_KEYS = {
    "source", "ticker", "predicted_direction",
    "confidence_score", "timestamp",
}


def _validate_prediction(payload: Dict) -> bool:
    """Validate payload against the strict JSON schema."""
    if not isinstance(payload, dict):
        return False
    for key in PREDICTION_SCHEMA_KEYS:
        if key not in payload:
            return False
    if payload.get("source") != "elite_lstm":
        return False
    if not isinstance(payload.get("confidence_score"), (int, float)):
        return False
    if not 0.0 <= payload["confidence_score"] <= 1.0:
        return False
    if payload.get("predicted_direction") not in ("up", "down", "hold"):
        return False
    return True


def _build_prediction_payload(signal: Dict) -> Dict:
    """Transform Elite API signal into Redis-schema-compliant payload."""
    prob_up = float(signal.get("prob_up", 0.5))
    if prob_up > 0.6:
        direction = "up"
    elif prob_up < 0.4:
        direction = "down"
    else:
        direction = "hold"

    return {
        "source": "elite_lstm",
        "ticker": signal.get("symbol", "UNKNOWN"),
        "predicted_direction": direction,
        "confidence_score": round(prob_up, 4),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


class LSTMBridgeService:
    """
    Async daemon bridging Embodier Trader LSTM predictions
    to the OpenClaw swarm via Redis pub/sub and the local Blackboard.
    """

    def __init__(self, blackboard: Optional[Blackboard] = None):
        self.bb = blackboard or get_blackboard()
        self._client: Optional[httpx.AsyncClient] = None
        self._redis: Optional[Any] = None
        self._backoff = INITIAL_BACKOFF_SECONDS
        self._running = False
        self._stats = {
            "polls": 0,
            "predictions_published": 0,
            "redis_publishes": 0,
            "blackboard_publishes": 0,
            "api_errors": 0,
            "redis_errors": 0,
            "last_poll": None,
            "last_prediction_count": 0,
        }
        self._latest_predictions: List[Dict] = []
        logger.info("[LSTMBridge] Initialized - Elite LSTM -> OpenClaw bridge")

    # ----------------------------------------------------------
    # Connection Management
    # ----------------------------------------------------------
    async def _ensure_http_client(self) -> httpx.AsyncClient:
        """Lazy-init httpx client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(HTTPX_TIMEOUT),
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                ),
                            headers={
                "Accept": "application/json",
                "X-OpenClaw-Token": OPENCLAW_BRIDGE_TOKEN,
            },
            )
        return self._client

    async def _ensure_redis(self) -> Optional[Any]:
        """Lazy-init aioredis connection."""
        if aioredis is None:
            return None
        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
                logger.info(f"[LSTMBridge] Redis connected: {REDIS_URL}")
            except Exception as e:
                logger.warning(f"[LSTMBridge] Redis connection failed: {e}")
                self._redis = None
        return self._redis

    # ----------------------------------------------------------
    # Elite API Polling with Exponential Backoff
    # ----------------------------------------------------------
    async def _poll_elite_signals(self) -> Optional[List[Dict]]:
        """
        Poll the Elite FastAPI /api/v1/signals/ endpoint.
        Returns list of signal dicts or None on failure.
        Implements exponential backoff on consecutive failures.
        """
        client = await self._ensure_http_client()
        try:
            resp = await client.get(ELITE_SIGNALS_ENDPOINT)
            resp.raise_for_status()
            data = resp.json()

            # Reset backoff on success
            self._backoff = INITIAL_BACKOFF_SECONDS
            self._stats["polls"] += 1
            self._stats["last_poll"] = datetime.now().isoformat()

            # Parse response: {as_of: "...", signals: [...]}
            signals = data.get("signals", [])
            if isinstance(signals, list):
                return signals
            return []

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[LSTMBridge] Elite API HTTP {e.response.status_code}: "
                f"{e.response.text[:200]}"
            )
            self._stats["api_errors"] += 1
            return None

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(
                f"[LSTMBridge] Elite API unreachable: {type(e).__name__}. "
                f"Backoff: {self._backoff}s"
            )
            self._stats["api_errors"] += 1
            return None

        except Exception as e:
            logger.error(f"[LSTMBridge] Unexpected poll error: {e}")
            self._stats["api_errors"] += 1
            return None

    # ----------------------------------------------------------
    # Redis Publishing
    # ----------------------------------------------------------
    async def _publish_to_redis(self, prediction: Dict) -> bool:
        """Publish a single prediction to Redis channel."""
        redis = await self._ensure_redis()
        if redis is None:
            return False

        if not _validate_prediction(prediction):
            logger.warning(f"[LSTMBridge] Invalid prediction schema: {prediction}")
            return False

        try:
            await redis.publish(
                REDIS_CHANNEL,
                json.dumps(prediction),
            )
            self._stats["redis_publishes"] += 1
            return True
        except Exception as e:
            logger.error(f"[LSTMBridge] Redis publish error: {e}")
            self._stats["redis_errors"] += 1
            self._redis = None  # Force reconnect
            return False

    # ----------------------------------------------------------
    # Blackboard Publishing
    # ----------------------------------------------------------
    async def _publish_to_blackboard(self, predictions: List[Dict]) -> None:
        """
        Publish all predictions as a single BlackboardMessage to
        Topic.ALPHA_SIGNALS so the ApexOrchestrator can ingest them.
        Also publishes individual ML_PREDICTIONS topic messages.
        """
        if not predictions:
            return

        # Batch payload for the orchestrator
        batch_payload = {
            "source": "elite_lstm_bridge",
            "signal_type": "ml_predictions",
            "prediction_count": len(predictions),
            "predictions": predictions,
            "polled_at": datetime.now().isoformat(),
        }

        await self.bb.publish(BlackboardMessage(
            topic=Topic.ALPHA_SIGNALS,
            payload=batch_payload,
            source_agent="lstm_bridge_service",
            priority=2,
            ttl_seconds=120,
        ))
        self._stats["blackboard_publishes"] += 1

        logger.info(
            f"[LSTMBridge] Published {len(predictions)} LSTM predictions "
            f"to blackboard"
        )

    # ----------------------------------------------------------
    # Main Polling Loop
    # ----------------------------------------------------------
    async def run(self) -> None:
        """
        Main event loop: poll -> transform -> publish (Redis + Blackboard).
        Survives FastAPI restarts via exponential backoff.
        """
        self._running = True
        logger.info(
            f"[LSTMBridge] Starting polling loop. "
            f"Elite endpoint: {ELITE_SIGNALS_ENDPOINT} | "
            f"Redis channel: {REDIS_CHANNEL} | "
            f"Interval: {POLL_INTERVAL_SECONDS}s"
        )

        while self._running:
            try:
                raw_signals = await self._poll_elite_signals()

                if raw_signals is None:
                    # API failure: exponential backoff
                    await asyncio.sleep(self._backoff)
                    self._backoff = min(
                        self._backoff * 2, MAX_BACKOFF_SECONDS
                    )
                    continue

                if not raw_signals:
                    logger.debug("[LSTMBridge] No signals from Elite API")
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
                    continue

                # Transform each signal into Redis-schema payload
                predictions = []
                for signal in raw_signals:
                    pred = _build_prediction_payload(signal)
                    if _validate_prediction(pred):
                        predictions.append(pred)

                self._latest_predictions = predictions
                self._stats["predictions_published"] += len(predictions)
                self._stats["last_prediction_count"] = len(predictions)

                # Publish to Redis (each prediction individually)
                for pred in predictions:
                    await self._publish_to_redis(pred)

                # Publish batch to Blackboard for ApexOrchestrator
                await self._publish_to_blackboard(predictions)

                # Heartbeat
                await self.bb.heartbeat("lstm_bridge_service")

                await asyncio.sleep(POLL_INTERVAL_SECONDS)

            except asyncio.CancelledError:
                logger.info("[LSTMBridge] Shutting down gracefully")
                break
            except Exception as e:
                logger.error(f"[LSTMBridge] Loop error: {e}")
                await asyncio.sleep(10)

        await self._cleanup()

    async def _cleanup(self) -> None:
        """Close connections on shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._redis:
            await self._redis.close()
        logger.info("[LSTMBridge] Shutdown complete")

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------
    def get_latest_predictions(self) -> List[Dict]:
        """Return the most recent batch of LSTM predictions."""
        return list(self._latest_predictions)

    def get_predictions_as_prompt_context(self) -> str:
        """
        Format latest predictions as a string suitable for injection
        into the ApexOrchestrator's ToT LLM prompt.
        """
        if not self._latest_predictions:
            return "LSTM PREDICTIONS: No predictions available from Elite system."

        lines = ["LSTM PREDICTIONS (from Embodier Trader PyTorch model):"]
        for p in self._latest_predictions:
            lines.append(
                f"  {p['ticker']}: direction={p['predicted_direction']} "
                f"confidence={p['confidence_score']:.2%}"
            )
        lines.append(
            f"  (polled at {self._stats.get('last_poll', 'unknown')})"
        )
        return "\n".join(lines)

    def get_status(self) -> Dict:
        """Return bridge diagnostics."""
        return {
            "service": "lstm_bridge_service",
            "elite_endpoint": ELITE_SIGNALS_ENDPOINT,
            "redis_channel": REDIS_CHANNEL,
            "redis_connected": self._redis is not None,
            "running": self._running,
            "stats": dict(self._stats),
            "latest_prediction_count": len(self._latest_predictions),
        }

    def stop(self) -> None:
        """Signal the polling loop to stop."""
        self._running = False


# ============================================================
# Module-level singleton + CLI entry point
# ============================================================
_bridge_instance: Optional[LSTMBridgeService] = None


def get_lstm_bridge() -> LSTMBridgeService:
    """Get or create the global LSTMBridgeService singleton."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = LSTMBridgeService()
    return _bridge_instance


async def main():
    """CLI entry point for standalone daemon mode."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    bridge = get_lstm_bridge()
    logger.info("=" * 60)
    logger.info("OpenClaw LSTM Bridge Service")
    logger.info("Elite API: %s", ELITE_SIGNALS_ENDPOINT)
    logger.info("Redis Channel: %s", REDIS_CHANNEL)
    logger.info("Poll Interval: %ds", POLL_INTERVAL_SECONDS)
    logger.info("=" * 60)
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())
