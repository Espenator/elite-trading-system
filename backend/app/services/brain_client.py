"""PC1 gRPC client for Brain Service (PC2).

Provides LLM inference via gRPC with circuit breaker pattern.
When BRAIN_ENABLED=false (default), returns stub low-confidence responses.

Usage:
    from app.services.brain_client import get_brain_client
    client = get_brain_client()
    result = await client.infer("AAPL", "1d", features_json, "bullish")
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Config from environment
BRAIN_ENABLED = os.getenv("BRAIN_ENABLED", "false").lower() == "true"
BRAIN_HOST = os.getenv("BRAIN_HOST", "localhost")
BRAIN_PORT = int(os.getenv("BRAIN_PORT", "50051"))
BRAIN_CONNECT_TIMEOUT = int(os.getenv("BRAIN_CONNECT_TIMEOUT", "5"))
BRAIN_REQUEST_TIMEOUT = int(os.getenv("BRAIN_REQUEST_TIMEOUT", "15"))

# Circuit breaker settings
CB_FAILURE_THRESHOLD = 3
CB_RECOVERY_TIMEOUT = 60  # seconds


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for gRPC calls with latency-aware auto-disable.

    ETBI enhancement: tracks consecutive slow responses (>800ms) and
    opens the circuit after 3 consecutive slow calls to prevent
    latency degradation from cascading through the council pipeline.
    """

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    failure_threshold: int = CB_FAILURE_THRESHOLD
    recovery_timeout: float = CB_RECOVERY_TIMEOUT

    # Latency-based auto-disable (ETBI guardrail)
    latency_threshold_ms: float = 800.0  # trigger after this latency
    consecutive_slow: int = 0
    slow_threshold: int = 3  # open circuit after N consecutive slow calls
    recent_latencies: list = None  # rolling window for telemetry

    def __post_init__(self):
        if self.recent_latencies is None:
            self.recent_latencies = []

    def record_success(self, latency_ms: float = 0.0):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self._track_latency(latency_ms)

        # Latency check: even successful calls can be too slow
        if latency_ms > self.latency_threshold_ms:
            self.consecutive_slow += 1
            if self.consecutive_slow >= self.slow_threshold:
                self.state = CircuitState.OPEN
                self.last_failure_time = time.time()
                logger.warning(
                    "Circuit breaker OPEN: %d consecutive calls >%.0fms (last=%.0fms)",
                    self.consecutive_slow, self.latency_threshold_ms, latency_ms,
                )
        else:
            self.consecutive_slow = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.consecutive_slow = 0  # reset slow counter on hard failure
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPEN after %d failures", self.failure_count
            )

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.consecutive_slow = 0
                logger.info("Circuit breaker HALF_OPEN — testing recovery")
                return True
            return False
        return True  # HALF_OPEN: allow one attempt

    def _track_latency(self, latency_ms: float):
        """Track recent latencies for telemetry (rolling window of 50)."""
        self.recent_latencies.append(latency_ms)
        if len(self.recent_latencies) > 50:
            self.recent_latencies = self.recent_latencies[-50:]

    @property
    def avg_latency_ms(self) -> float:
        if not self.recent_latencies:
            return 0.0
        return sum(self.recent_latencies) / len(self.recent_latencies)

    @property
    def p95_latency_ms(self) -> float:
        if not self.recent_latencies:
            return 0.0
        sorted_lat = sorted(self.recent_latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]


def _stub_infer_response() -> Dict[str, Any]:
    """Stub response when brain is disabled or unavailable."""
    return {
        "summary": "Brain service disabled or unavailable",
        "confidence": 0.1,
        "risk_flags": ["brain_disabled"],
        "reasoning_bullets": ["LLM hypothesis not available"],
        "error": "",
    }


def _stub_critic_response() -> Dict[str, Any]:
    """Stub response for critic when brain is disabled."""
    return {
        "analysis": "Brain service disabled or unavailable",
        "lessons": [],
        "performance_score": 0.0,
        "error": "",
    }


class BrainClient:
    """gRPC client for Brain Service with circuit breaker.

    When BRAIN_ENABLED=false, all methods return stub responses.
    When BRAIN_ENABLED=true, connects to brain_service via gRPC.
    """

    def __init__(
        self,
        host: str = BRAIN_HOST,
        port: int = BRAIN_PORT,
        enabled: bool = BRAIN_ENABLED,
    ):
        self.host = host
        self.port = port
        self.enabled = enabled
        self._channel = None
        self._stub = None
        self._circuit = CircuitBreaker()

    def _ensure_channel(self):
        """Lazy-init gRPC channel and stub."""
        if self._channel is not None:
            return
        try:
            import grpc

            target = f"{self.host}:{self.port}"
            self._channel = grpc.aio.insecure_channel(
                target,
                options=[
                    ("grpc.connect_timeout_ms", BRAIN_CONNECT_TIMEOUT * 1000),
                    ("grpc.keepalive_time_ms", 30000),
                ],
            )
            import sys
            from pathlib import Path

            proto_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "brain_service"
                / "proto"
            )
            if str(proto_dir) not in sys.path:
                sys.path.insert(0, str(proto_dir))
            from proto import brain_pb2_grpc

            self._stub = brain_pb2_grpc.BrainServiceStub(self._channel)
            logger.info("Brain gRPC channel created: %s", target)
        except Exception as e:
            logger.warning("Failed to create brain gRPC channel: %s", e)
            self._channel = None
            self._stub = None

    async def infer(
        self,
        symbol: str,
        timeframe: str = "1d",
        feature_json: str = "{}",
        regime: str = "unknown",
        context: str = "",
    ) -> Dict[str, Any]:
        """Request LLM inference from Brain Service.

        Returns dict with: summary, confidence, risk_flags, reasoning_bullets, error
        """
        if not self.enabled:
            return _stub_infer_response()

        if not self._circuit.can_execute():
            logger.debug("Brain circuit breaker OPEN — returning stub")
            return {**_stub_infer_response(), "error": "circuit_breaker_open"}

        try:
            self._ensure_channel()
            if self._stub is None:
                self._circuit.record_failure()
                return {**_stub_infer_response(), "error": "grpc_not_connected"}

            import sys
            from pathlib import Path

            proto_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "brain_service"
                / "proto"
            )
            if str(proto_dir) not in sys.path:
                sys.path.insert(0, str(proto_dir))
            from proto import brain_pb2

            request = brain_pb2.InferRequest(
                symbol=symbol,
                timeframe=timeframe,
                feature_json=feature_json,
                regime=regime,
                context=context,
            )
            _t0 = time.monotonic()
            response = await asyncio.wait_for(
                self._stub.InferCandidateContext(request),
                timeout=BRAIN_REQUEST_TIMEOUT,
            )
            latency_ms = (time.monotonic() - _t0) * 1000
            self._circuit.record_success(latency_ms=latency_ms)
            logger.debug("Brain infer %s: %.0fms", symbol, latency_ms)
            return {
                "summary": response.summary,
                "confidence": response.confidence,
                "risk_flags": list(response.risk_flags),
                "reasoning_bullets": list(response.reasoning_bullets),
                "error": response.error,
                "latency_ms": round(latency_ms, 1),
            }
        except asyncio.TimeoutError:
            logger.warning("Brain infer timed out after %ds", BRAIN_REQUEST_TIMEOUT)
            self._circuit.record_failure()
            return {**_stub_infer_response(), "error": "timeout"}
        except Exception as e:
            logger.warning("Brain infer error: %s", e)
            self._circuit.record_failure()
            return {**_stub_infer_response(), "error": str(e)}

    async def critic(
        self,
        trade_id: str,
        symbol: str,
        entry_context: str = "",
        outcome_json: str = "{}",
    ) -> Dict[str, Any]:
        """Request post-trade critic analysis from Brain Service."""
        if not self.enabled:
            return _stub_critic_response()

        if not self._circuit.can_execute():
            return {**_stub_critic_response(), "error": "circuit_breaker_open"}

        try:
            self._ensure_channel()
            if self._stub is None:
                self._circuit.record_failure()
                return {**_stub_critic_response(), "error": "grpc_not_connected"}

            import sys
            from pathlib import Path

            proto_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "brain_service"
                / "proto"
            )
            if str(proto_dir) not in sys.path:
                sys.path.insert(0, str(proto_dir))
            from proto import brain_pb2

            request = brain_pb2.CriticRequest(
                trade_id=trade_id,
                symbol=symbol,
                entry_context=entry_context,
                outcome_json=outcome_json,
            )
            response = await asyncio.wait_for(
                self._stub.CriticPostmortem(request),
                timeout=BRAIN_REQUEST_TIMEOUT,
            )
            self._circuit.record_success()
            return {
                "analysis": response.analysis,
                "lessons": list(response.lessons),
                "performance_score": response.performance_score,
                "error": response.error,
            }
        except asyncio.TimeoutError:
            self._circuit.record_failure()
            return {**_stub_critic_response(), "error": "timeout"}
        except Exception as e:
            logger.warning("Brain critic error: %s", e)
            self._circuit.record_failure()
            return {**_stub_critic_response(), "error": str(e)}

    async def close(self):
        """Close the gRPC channel."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None

    def get_status(self) -> Dict[str, Any]:
        """Return client status for health checks."""
        return {
            "enabled": self.enabled,
            "host": self.host,
            "port": self.port,
            "circuit_state": self._circuit.state.value,
            "failure_count": self._circuit.failure_count,
        }


_brain_client: Optional[BrainClient] = None


def get_brain_client() -> BrainClient:
    """Get or create the singleton BrainClient."""
    global _brain_client
    if _brain_client is None:
        _brain_client = BrainClient()
    return _brain_client
