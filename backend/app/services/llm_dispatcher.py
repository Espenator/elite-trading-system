"""LLM Dispatcher — Telemetry-aware intelligent workload distribution.

The "Brain Router" that sits between Council Agents and Ollama, making
routing decisions based on real-time GPU telemetry, model pinning, and
node health.

Decision logic:
    1. Check model pinning — if the requested model is pinned to a node, prefer it
    2. Check task affinity — if the task has a preferred node, prefer it
    3. Check telemetry — route to the node with lowest GPU utilization
    4. Check model residency — prefer the node where the model is already loaded
    5. Fallback — round-robin via OllamaNodePool

Graceful Degradation:
    - Detects PC2 death via missed heartbeats on cluster.telemetry
    - Redirects all traffic back to PC1's Ollama
    - Auto-downgrades heavy tasks to fallback model (e.g., DeepSeek-14B → Llama-8B)
    - Auto-recovers when PC2 broadcasts telemetry again

Part of #39 — E1.3 + E1.4
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node state
# ---------------------------------------------------------------------------

class NodeState(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"  # High utilization or partial errors
    OFFLINE = "offline"


@dataclass
class NodeHealth:
    """Tracks health and heartbeat state for one Ollama node."""
    url: str
    state: NodeState = NodeState.ONLINE
    last_heartbeat: float = 0.0
    missed_heartbeats: int = 0
    gpu_utilization_pct: float = 0.0
    vram_free_mb: int = 0
    vram_total_mb: int = 0
    loaded_models: List[str] = field(default_factory=list)
    total_requests: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    _latencies: List[float] = field(default_factory=list)

    def record_latency(self, ms: float) -> None:
        self._latencies.append(ms)
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-100:]
        self.avg_latency_ms = sum(self._latencies) / len(self._latencies)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "state": self.state.value,
            "last_heartbeat_age_s": (
                round(time.time() - self.last_heartbeat, 1)
                if self.last_heartbeat else None
            ),
            "missed_heartbeats": self.missed_heartbeats,
            "gpu_utilization_pct": self.gpu_utilization_pct,
            "vram_free_mb": self.vram_free_mb,
            "vram_total_mb": self.vram_total_mb,
            "loaded_models": self.loaded_models,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
        }


@dataclass
class DispatchDecision:
    """Result of a dispatch decision for logging/telemetry."""
    target_url: str
    model: str
    original_model: str  # Before any degradation
    reason: str
    degraded: bool = False  # True if model was downgraded
    task: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_url": self.target_url,
            "model": self.model,
            "original_model": self.original_model,
            "reason": self.reason,
            "degraded": self.degraded,
            "task": self.task,
        }


# ---------------------------------------------------------------------------
# LLM Dispatcher
# ---------------------------------------------------------------------------

class LLMDispatcher:
    """Telemetry-aware LLM request dispatcher with graceful degradation.

    Maintains per-node health state, consumes GPU telemetry events,
    and makes intelligent routing decisions.
    """

    def __init__(self):
        self._nodes: Dict[str, NodeHealth] = {}
        self._heartbeat_timeout: int = 3
        self._gpu_util_threshold: float = 85.0
        self._fallback_model: str = "llama3.2"
        self._enabled: bool = True

        # Stats
        self._total_dispatches: int = 0
        self._total_degradations: int = 0
        self._total_failovers: int = 0

        self._load_config()
        self._init_nodes()

    def _load_config(self) -> None:
        try:
            from app.core.config import settings
            self._heartbeat_timeout = settings.LLM_DISPATCHER_HEARTBEAT_TIMEOUT
            self._gpu_util_threshold = settings.LLM_DISPATCHER_GPU_UTIL_THRESHOLD
            self._fallback_model = settings.LLM_DISPATCHER_FALLBACK_MODEL
            self._enabled = settings.LLM_DISPATCHER_ENABLED
        except Exception:
            import os
            self._heartbeat_timeout = int(os.getenv("LLM_DISPATCHER_HEARTBEAT_TIMEOUT", "3"))
            self._gpu_util_threshold = float(os.getenv("LLM_DISPATCHER_GPU_UTIL_THRESHOLD", "85.0"))
            self._fallback_model = os.getenv("LLM_DISPATCHER_FALLBACK_MODEL", "llama3.2")
            self._enabled = os.getenv("LLM_DISPATCHER_ENABLED", "true").lower() == "true"

    def _init_nodes(self) -> None:
        """Initialize node health tracking from OllamaNodePool."""
        try:
            from app.services.ollama_node_pool import get_ollama_pool
            pool = get_ollama_pool()
            for url in pool.urls:
                self._nodes[url] = NodeHealth(
                    url=url,
                    state=NodeState.ONLINE,
                    last_heartbeat=time.time(),
                )
        except Exception:
            pass

    # -- Telemetry ingestion --------------------------------------------------

    def ingest_telemetry(self, telemetry: Dict[str, Any]) -> None:
        """Ingest a telemetry event from cluster.telemetry topic.

        Updates node health state based on GPU stats and loaded models.
        Called by the MessageBus subscriber in main.py.
        """
        node_url = telemetry.get("node_url", "")
        if not node_url:
            return

        node_url = node_url.rstrip("/")
        if node_url not in self._nodes:
            self._nodes[node_url] = NodeHealth(url=node_url)

        node = self._nodes[node_url]
        node.last_heartbeat = time.time()
        node.missed_heartbeats = 0

        # Update GPU stats
        gpu = telemetry.get("gpu")
        if gpu:
            node.gpu_utilization_pct = gpu.get("gpu_utilization_pct", 0.0)
            node.vram_free_mb = gpu.get("vram_free_mb", 0)
            node.vram_total_mb = gpu.get("vram_total_mb", 0)

        # Update loaded models
        loaded = telemetry.get("loaded_models", [])
        node.loaded_models = [m.get("model", "") for m in loaded]

        # State transitions
        was_offline = node.state == NodeState.OFFLINE
        if node.gpu_utilization_pct > self._gpu_util_threshold:
            node.state = NodeState.DEGRADED
        else:
            node.state = NodeState.ONLINE

        if was_offline:
            logger.info(
                "LLMDispatcher: node %s recovered → %s (GPU %.1f%%, VRAM %dMB free)",
                node_url, node.state.value,
                node.gpu_utilization_pct, node.vram_free_mb,
            )

    def check_heartbeats(self) -> None:
        """Check all nodes for missed heartbeats. Call periodically.

        Marks nodes OFFLINE after ``heartbeat_timeout`` missed intervals.
        """
        now = time.time()
        try:
            from app.core.config import settings
            interval = settings.GPU_TELEMETRY_INTERVAL
        except Exception:
            interval = 3.0

        for node in self._nodes.values():
            if node.last_heartbeat == 0.0:
                continue  # Never received a heartbeat yet

            age = now - node.last_heartbeat
            expected_beats = age / interval if interval > 0 else 0
            missed = int(expected_beats) - 1  # Allow 1 grace period

            if missed > node.missed_heartbeats:
                node.missed_heartbeats = missed

            if node.missed_heartbeats >= self._heartbeat_timeout:
                if node.state != NodeState.OFFLINE:
                    logger.warning(
                        "LLMDispatcher: node %s → OFFLINE (%d missed heartbeats)",
                        node.url, node.missed_heartbeats,
                    )
                    node.state = NodeState.OFFLINE
                    self._total_failovers += 1

    # -- Dispatch logic -------------------------------------------------------

    def dispatch(
        self,
        model: str = "",
        task: str = "",
    ) -> DispatchDecision:
        """Determine the best node + model for an inference request.

        Decision priority:
            1. Task affinity → preferred node for this task type
            2. Model pinning → preferred node for this model
            3. Model residency → node where model is already loaded in VRAM
            4. GPU utilization → route to least-loaded healthy node
            5. Fallback → first available healthy node

        Graceful degradation: if the target node is OFFLINE, downgrade
        the model and reroute to an available node.
        """
        if not self._enabled:
            # Dispatcher disabled — use default behavior
            url = self._get_any_healthy_url()
            return DispatchDecision(
                target_url=url or "",
                model=model,
                original_model=model,
                reason="dispatcher_disabled",
                task=task,
            )

        self.check_heartbeats()
        self._total_dispatches += 1

        original_model = model

        # 1. Check task affinity
        target_url, reason = self._resolve_by_task(task)

        # 2. Check model pinning (if task didn't resolve)
        if not target_url and model:
            target_url, reason = self._resolve_by_model_pin(model)

        # 3. Check model residency (is it already loaded somewhere?)
        if not target_url and model:
            target_url, reason = self._resolve_by_residency(model)

        # 4. Route by GPU utilization
        if not target_url:
            target_url, reason = self._resolve_by_utilization()

        # 5. Fallback to any healthy node
        if not target_url:
            target_url = self._get_any_healthy_url()
            reason = "fallback_any_healthy"

        # No healthy nodes at all — last resort
        if not target_url:
            target_url = self._get_any_url()
            reason = "last_resort_all_unhealthy"

        # -- Graceful degradation --
        degraded = False
        node = self._nodes.get(target_url)
        if node and node.state == NodeState.OFFLINE:
            # Target is offline — reroute to healthy node and downgrade model
            healthy_url = self._get_any_healthy_url()
            if healthy_url and healthy_url != target_url:
                old_model = model
                model = self._fallback_model
                target_url = healthy_url
                degraded = True
                self._total_degradations += 1
                reason = f"degraded_{reason}"
                logger.info(
                    "LLMDispatcher: degraded %s → %s (node offline, rerouted to %s)",
                    old_model, model, target_url,
                )

        return DispatchDecision(
            target_url=target_url or "",
            model=model or self._fallback_model,
            original_model=original_model,
            reason=reason,
            degraded=degraded,
            task=task,
        )

    # -- Resolution strategies ------------------------------------------------

    def _resolve_by_task(self, task: str) -> Tuple[str, str]:
        """Resolve target URL by task affinity from ModelPinningRegistry."""
        if not task:
            return "", ""
        try:
            from app.services.model_pinning import get_model_pinning
            registry = get_model_pinning()
            node_role = registry.get_node_for_task(task)
            if node_role is not None:
                url = registry.get_node_url(node_role)
                if url and self._is_healthy(url):
                    return url, f"task_affinity_{node_role.value}"
        except Exception:
            pass
        return "", ""

    def _resolve_by_model_pin(self, model: str) -> Tuple[str, str]:
        """Resolve target URL by model pinning."""
        try:
            from app.services.model_pinning import get_model_pinning
            registry = get_model_pinning()
            node_role = registry.get_node_for_model(model)
            if node_role is not None:
                url = registry.get_node_url(node_role)
                if url and self._is_healthy(url):
                    return url, f"model_pin_{node_role.value}"
        except Exception:
            pass
        return "", ""

    def _resolve_by_residency(self, model: str) -> Tuple[str, str]:
        """Prefer the node where the model is already loaded in VRAM."""
        for url, node in self._nodes.items():
            if node.state == NodeState.OFFLINE:
                continue
            for loaded in node.loaded_models:
                if model in loaded or loaded in model:
                    return url, "model_resident"
        return "", ""

    def _resolve_by_utilization(self) -> Tuple[str, str]:
        """Route to the healthy node with lowest GPU utilization."""
        candidates = [
            (url, node) for url, node in self._nodes.items()
            if node.state != NodeState.OFFLINE
        ]
        if not candidates:
            return "", ""

        # Sort by GPU utilization (ascending)
        candidates.sort(key=lambda x: x[1].gpu_utilization_pct)
        best_url, best_node = candidates[0]
        return best_url, f"lowest_gpu_util_{best_node.gpu_utilization_pct:.0f}pct"

    # -- Helpers --------------------------------------------------------------

    def _is_healthy(self, url: str) -> bool:
        """Check if a node is healthy (ONLINE or DEGRADED)."""
        url = url.rstrip("/")
        node = self._nodes.get(url)
        if node is None:
            return True  # Unknown node — assume healthy
        return node.state != NodeState.OFFLINE

    def _get_any_healthy_url(self) -> Optional[str]:
        """Get any healthy node URL."""
        for url, node in self._nodes.items():
            if node.state != NodeState.OFFLINE:
                return url
        return None

    def _get_any_url(self) -> Optional[str]:
        """Get any node URL (even unhealthy — last resort)."""
        if self._nodes:
            return next(iter(self._nodes))
        return None

    def register_node(self, url: str) -> None:
        """Register a new node (e.g., from NodeDiscovery)."""
        url = url.rstrip("/")
        if url not in self._nodes:
            self._nodes[url] = NodeHealth(
                url=url,
                state=NodeState.ONLINE,
                last_heartbeat=time.time(),
            )
            logger.info("LLMDispatcher: registered node %s", url)

    def report_success(self, url: str, latency_ms: float = 0.0) -> None:
        """Report a successful inference to update node stats."""
        url = url.rstrip("/")
        node = self._nodes.get(url)
        if node:
            node.total_requests += 1
            node.record_latency(latency_ms)

    def report_error(self, url: str) -> None:
        """Report a failed inference to update node stats."""
        url = url.rstrip("/")
        node = self._nodes.get(url)
        if node:
            node.total_requests += 1
            node.total_errors += 1

    def get_status(self) -> Dict[str, Any]:
        """Return dispatcher status for monitoring."""
        return {
            "enabled": self._enabled,
            "heartbeat_timeout": self._heartbeat_timeout,
            "gpu_util_threshold": self._gpu_util_threshold,
            "fallback_model": self._fallback_model,
            "total_dispatches": self._total_dispatches,
            "total_degradations": self._total_degradations,
            "total_failovers": self._total_failovers,
            "nodes": {
                url: node.to_dict()
                for url, node in self._nodes.items()
            },
        }


# ── Module-level singleton ────────────────────────────────────────────────
_dispatcher: Optional[LLMDispatcher] = None


def get_llm_dispatcher() -> LLMDispatcher:
    """Get or create the singleton LLMDispatcher."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = LLMDispatcher()
    return _dispatcher
