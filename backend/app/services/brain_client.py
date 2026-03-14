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

# Config: canonical BRAIN_SERVICE_URL (PC2) or BRAIN_HOST:BRAIN_PORT
try:
    from app.core.config import settings as _brain_settings
    BRAIN_ENABLED = _brain_settings.BRAIN_ENABLED
    _url = getattr(_brain_settings, "BRAIN_SERVICE_URL", "") or os.getenv("BRAIN_SERVICE_URL", "")
    if _url:
        _parts = _url.strip().rsplit(":", 1)
        BRAIN_HOST = _parts[0] if _parts else _brain_settings.BRAIN_HOST
        BRAIN_PORT = int(_parts[1]) if len(_parts) == 2 else _brain_settings.BRAIN_PORT
    else:
        BRAIN_HOST = _brain_settings.BRAIN_HOST
        BRAIN_PORT = _brain_settings.BRAIN_PORT
except Exception:
    BRAIN_ENABLED = os.getenv("BRAIN_ENABLED", "false").lower() == "true"
    _url = os.getenv("BRAIN_SERVICE_URL", "")
    if _url:
        _parts = _url.strip().rsplit(":", 1)
        BRAIN_HOST = _parts[0] if _parts else "localhost"
        BRAIN_PORT = int(_parts[1]) if len(_parts) == 2 else 50051
    else:
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


def _stub_infer_response(tag: str = "brain_disabled") -> Dict[str, Any]:
    """Stub response when brain is disabled or unavailable. Always low-confidence and tagged."""
    return {
        "summary": "Brain service disabled or unavailable",
        "confidence": 0.1,
        "risk_flags": [tag],
        "reasoning_bullets": ["LLM hypothesis not available"],
        "error": "",
        "degraded_mode": True,
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
        """Lazy-init gRPC channel and stub.

        Uses the persistent singleton channel from brain_channel.py
        when available, creating it on first call with keepalive options
        for long-lived connections to PC2.
        """
        if self._channel is not None:
            return
        try:
            import grpc

            # Try reusing the persistent singleton from brain_channel
            try:
                from app.core.brain_channel import _channel as _singleton_ch
                if _singleton_ch is not None:
                    self._channel = _singleton_ch
                    logger.debug("Reusing persistent brain_channel singleton")
                else:
                    raise ValueError("not yet initialized")
            except (ImportError, ValueError):
                # Create channel with enhanced keepalive options
                target = f"{self.host}:{self.port}"
                self._channel = grpc.aio.insecure_channel(
                    target,
                    options=[
                        ("grpc.connect_timeout_ms", BRAIN_CONNECT_TIMEOUT * 1000),
                        ("grpc.keepalive_time_ms", 30_000),
                        ("grpc.keepalive_timeout_ms", 10_000),
                        ("grpc.keepalive_permit_without_calls", True),
                        ("grpc.http2.max_pings_without_data", 0),
                    ],
                )
                # Store into brain_channel module for sharing
                try:
                    import app.core.brain_channel as _bc_mod
                    _bc_mod._channel = self._channel
                except Exception:
                    pass
                logger.info("Brain gRPC persistent channel created: %s", target)

            import sys
            from pathlib import Path

            brain_service_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "brain_service"
            )
            proto_dir = brain_service_dir / "proto"
            # Need both: brain_service/ for "from proto import ..."
            # and proto/ for internal "import brain_pb2" in generated stubs
            if str(brain_service_dir) not in sys.path:
                sys.path.insert(0, str(brain_service_dir))
            if str(proto_dir) not in sys.path:
                sys.path.insert(0, str(proto_dir))
            from proto import brain_pb2_grpc

            self._stub = brain_pb2_grpc.BrainServiceStub(self._channel)
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
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Request LLM inference from Brain Service.

        Args:
            timeout: Per-call timeout override in seconds. Defaults to BRAIN_REQUEST_TIMEOUT.

        Returns dict with: summary, confidence, risk_flags, reasoning_bullets, error
        """
        if not self.enabled:
            return _stub_infer_response()

        if not self._circuit.can_execute():
            logger.debug("Brain circuit breaker OPEN — returning stub")
            return {**_stub_infer_response("circuit_breaker_open"), "error": "circuit_breaker_open"}

        try:
            self._ensure_channel()
            if self._stub is None:
                self._circuit.record_failure()
                return {**_stub_infer_response("grpc_not_connected"), "error": "grpc_not_connected"}

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
            _timeout = timeout if timeout is not None else BRAIN_REQUEST_TIMEOUT
            response = await asyncio.wait_for(
                self._stub.InferCandidateContext(request),
                timeout=_timeout,
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
            _timeout = timeout if timeout is not None else BRAIN_REQUEST_TIMEOUT
            logger.warning("Brain infer timed out after %.1fs", _timeout)
            self._circuit.record_failure()
            return {**_stub_infer_response("timeout"), "error": "timeout"}
        except Exception as e:
            logger.warning("Brain infer error: %s", e)
            self._circuit.record_failure()
            return {**_stub_infer_response("unreachable"), "error": str(e)}

    async def critic(
        self,
        trade_id: str,
        symbol: str,
        entry_context: str = "",
        outcome_json: str = "{}",
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Request post-trade critic analysis from Brain Service.

        Args:
            timeout: Per-call timeout override in seconds. Defaults to BRAIN_REQUEST_TIMEOUT.
        """
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
            _timeout = timeout if timeout is not None else BRAIN_REQUEST_TIMEOUT
            response = await asyncio.wait_for(
                self._stub.CriticPostmortem(request),
                timeout=_timeout,
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

    # ── Level 3A: Distributed Council Stage ─────────────────────────────

    async def run_council_stage(
        self,
        symbol: str,
        timeframe: str = "1d",
        feature_json: str = "{}",
        context_json: str = "{}",
        stage: int = 1,
        agent_types: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Run a council stage on PC2 via gRPC.

        Returns dict with votes list and stage_latency_ms.
        Falls back to empty votes if brain is unavailable.
        """
        if not self.enabled:
            return {"votes": [], "error": "brain_disabled"}

        if not self._circuit.can_execute():
            return {"votes": [], "error": "circuit_breaker_open"}

        try:
            self._ensure_channel()
            if self._stub is None:
                self._circuit.record_failure()
                return {"votes": [], "error": "grpc_not_connected"}

            import sys
            from pathlib import Path
            proto_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "brain_service" / "proto"
            )
            if str(proto_dir) not in sys.path:
                sys.path.insert(0, str(proto_dir))
            from proto import brain_pb2

            request = brain_pb2.CouncilStageRequest(
                symbol=symbol,
                timeframe=timeframe,
                feature_json=feature_json,
                context_json=context_json,
                stage=stage,
                agent_types=agent_types or [],
            )
            _t0 = time.monotonic()
            response = await asyncio.wait_for(
                self._stub.RunCouncilStage(request),
                timeout=BRAIN_REQUEST_TIMEOUT,
            )
            latency_ms = (time.monotonic() - _t0) * 1000
            self._circuit.record_success(latency_ms=latency_ms)

            import json
            votes = []
            for v in response.votes:
                votes.append({
                    "agent_name": v.agent_name,
                    "direction": v.direction,
                    "confidence": v.confidence,
                    "reasoning": v.reasoning,
                    "veto": v.veto,
                    "veto_reason": v.veto_reason,
                    "metadata": json.loads(v.metadata_json) if v.metadata_json else {},
                })

            logger.info(
                "Distributed stage %d for %s: %d votes, %.0fms",
                stage, symbol, len(votes), latency_ms,
            )
            return {
                "votes": votes,
                "stage_latency_ms": response.stage_latency_ms,
                "latency_ms": round(latency_ms, 1),
            }
        except asyncio.TimeoutError:
            self._circuit.record_failure()
            return {"votes": [], "error": "timeout"}
        except Exception as e:
            logger.warning("Brain run_council_stage error: %s", e)
            self._circuit.record_failure()
            return {"votes": [], "error": str(e)}

    # ── Level 3C: Universe Scanner ──────────────────────────────────────

    async def scan_universe(
        self,
        symbols: list,
        regime: str = "UNKNOWN",
        min_score: float = 55.0,
    ) -> Dict[str, Any]:
        """Request PC2 to scan symbols for trading opportunities.

        Returns dict with candidates list and scan_latency_ms.
        """
        if not self.enabled:
            return {"candidates": [], "error": "brain_disabled"}

        if not self._circuit.can_execute():
            return {"candidates": [], "error": "circuit_breaker_open"}

        try:
            self._ensure_channel()
            if self._stub is None:
                self._circuit.record_failure()
                return {"candidates": [], "error": "grpc_not_connected"}

            import sys
            from pathlib import Path
            proto_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "brain_service" / "proto"
            )
            if str(proto_dir) not in sys.path:
                sys.path.insert(0, str(proto_dir))
            from proto import brain_pb2

            request = brain_pb2.ScanRequest(
                symbols=symbols,
                regime=regime,
                min_score=min_score,
            )
            _t0 = time.monotonic()
            response = await asyncio.wait_for(
                self._stub.ScanUniverse(request),
                timeout=60,  # Scanning can take longer
            )
            latency_ms = (time.monotonic() - _t0) * 1000
            self._circuit.record_success(latency_ms=latency_ms)

            candidates = []
            for c in response.candidates:
                candidates.append({
                    "symbol": c.symbol,
                    "signal_score": c.signal_score,
                    "direction": c.direction,
                    "label": c.label,
                    "volume_surge": c.volume_surge,
                })

            logger.info(
                "Universe scan: %d/%d candidates in %.0fms",
                len(candidates), response.symbols_scanned, latency_ms,
            )
            return {
                "candidates": candidates,
                "symbols_scanned": response.symbols_scanned,
                "scan_latency_ms": response.scan_latency_ms,
                "latency_ms": round(latency_ms, 1),
            }
        except asyncio.TimeoutError:
            self._circuit.record_failure()
            return {"candidates": [], "error": "timeout"}
        except Exception as e:
            logger.warning("Brain scan_universe error: %s", e)
            self._circuit.record_failure()
            return {"candidates": [], "error": str(e)}

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
            "distributed_rpcs": [
                "run_council_stage", "scan_universe",
            ],
        }


_brain_client: Optional[BrainClient] = None


def get_brain_client() -> BrainClient:
    """Get or create the singleton BrainClient."""
    global _brain_client
    if _brain_client is None:
        _brain_client = BrainClient()
    return _brain_client
