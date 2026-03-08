"""NodeRegistry — Shared registry for multi-PC node and service awareness.

Provides a single source of truth for every compute node that participates
in the trading system (local PC, remote PC2, future workers).  Other
services (NodeDiscovery, LLMDispatcher, GPUTelemetryDaemon, cluster API)
read and write this registry instead of keeping their own isolated state.

Data model (top-down):

    NodeRegistry
    └── NodeInfo (one per node)
        ├── role: NodeRole (local | remote)
        ├── capabilities: NodeCapabilities
        │   ├── gpu_devices: List[GPUDevice]  # cuda:0, cuda:1, …
        │   ├── has_ollama / ollama_models
        │   └── has_brain_service / cpu_count
        ├── health: NodeHealth
        │   ├── status: NodeStatus
        │   ├── last_seen, consecutive_failures, latency_ms
        └── services: List[str]  # services running on this node

Part of #39 — E1 foundational layer.
"""
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeRole(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class GPUDevice:
    """One physical GPU device on a node (maps to cuda:N)."""

    index: int = 0                    # cuda:0, cuda:1, …
    name: str = ""
    vram_total_mb: int = 0
    vram_free_mb: int = 0
    utilization_pct: float = 0.0
    temperature_c: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "device_id": f"cuda:{self.index}",
            "name": self.name,
            "vram_total_mb": self.vram_total_mb,
            "vram_free_mb": self.vram_free_mb,
            "utilization_pct": self.utilization_pct,
            "temperature_c": self.temperature_c,
        }


@dataclass
class NodeCapabilities:
    """Static + semi-static capabilities of a node."""

    gpu_devices: List[GPUDevice] = field(default_factory=list)
    has_ollama: bool = False
    ollama_models: List[str] = field(default_factory=list)
    has_brain_service: bool = False
    cpu_count: int = 0

    @property
    def gpu_count(self) -> int:
        return len(self.gpu_devices)

    @property
    def total_vram_mb(self) -> int:
        return sum(g.vram_total_mb for g in self.gpu_devices)

    @property
    def free_vram_mb(self) -> int:
        return sum(g.vram_free_mb for g in self.gpu_devices)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gpu_count": self.gpu_count,
            "gpu_devices": [g.to_dict() for g in self.gpu_devices],
            "total_vram_mb": self.total_vram_mb,
            "free_vram_mb": self.free_vram_mb,
            "has_ollama": self.has_ollama,
            "ollama_models": self.ollama_models,
            "has_brain_service": self.has_brain_service,
            "cpu_count": self.cpu_count,
        }


@dataclass
class NodeHealth:
    """Runtime health state of a node."""

    status: NodeStatus = NodeStatus.UNKNOWN
    last_seen: float = 0.0             # Unix timestamp of last successful contact
    consecutive_failures: int = 0
    latency_ms: float = 0.0

    def mark_online(self, latency_ms: float = 0.0) -> None:
        self.status = NodeStatus.ONLINE
        self.last_seen = time.time()
        self.consecutive_failures = 0
        self.latency_ms = latency_ms

    def mark_offline(self) -> None:
        self.consecutive_failures += 1
        if self.status != NodeStatus.OFFLINE:
            self.status = NodeStatus.OFFLINE

    def mark_degraded(self) -> None:
        self.status = NodeStatus.DEGRADED
        self.last_seen = time.time()

    @property
    def age_seconds(self) -> Optional[float]:
        """Seconds since last successful contact, or None if never seen."""
        if self.last_seen == 0.0:
            return None
        return round(time.time() - self.last_seen, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "last_seen": self.last_seen or None,
            "age_seconds": self.age_seconds,
            "consecutive_failures": self.consecutive_failures,
            "latency_ms": round(self.latency_ms, 1),
        }


@dataclass
class NodeInfo:
    """Complete record for one compute node."""

    node_id: str
    role: NodeRole
    address: str                       # "host" or "" for local
    capabilities: NodeCapabilities = field(default_factory=NodeCapabilities)
    health: NodeHealth = field(default_factory=NodeHealth)
    services: List[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)

    @property
    def is_local(self) -> bool:
        return self.role == NodeRole.LOCAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "address": self.address or "local",
            "registered_at": self.registered_at,
            "health": self.health.to_dict(),
            "capabilities": self.capabilities.to_dict(),
            "services": self.services,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class NodeRegistry:
    """Central registry for all compute nodes.

    Thread-safe for asyncio (single-threaded event loop).  All mutations are
    synchronous to avoid lock contention — callers in async code do not need
    to await.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, NodeInfo] = {}
        self._local_node_id: Optional[str] = None

    # -- Registration --------------------------------------------------------

    def register_node(
        self,
        node_id: str,
        role: NodeRole,
        address: str = "",
        capabilities: Optional[NodeCapabilities] = None,
    ) -> NodeInfo:
        """Register or update a node.

        If the node already exists, its capabilities and role are updated but
        health history and services are preserved.
        """
        if node_id in self._nodes:
            node = self._nodes[node_id]
            node.role = role
            node.address = address
            if capabilities is not None:
                node.capabilities = capabilities
            logger.debug("NodeRegistry: updated node %s (%s)", node_id, role.value)
            return node

        node = NodeInfo(
            node_id=node_id,
            role=role,
            address=address,
            capabilities=capabilities or NodeCapabilities(),
        )
        self._nodes[node_id] = node

        if role == NodeRole.LOCAL:
            self._local_node_id = node_id

        logger.info(
            "NodeRegistry: registered node %s (%s, address=%r)",
            node_id, role.value, address or "local",
        )
        return node

    # -- Health --------------------------------------------------------------

    def update_health(
        self,
        node_id: str,
        status: NodeStatus,
        latency_ms: float = 0.0,
    ) -> None:
        """Update health state for a node."""
        node = self._nodes.get(node_id)
        if node is None:
            logger.debug("NodeRegistry.update_health: unknown node %s", node_id)
            return

        if status == NodeStatus.ONLINE:
            node.health.mark_online(latency_ms)
        elif status == NodeStatus.OFFLINE:
            node.health.mark_offline()
        elif status == NodeStatus.DEGRADED:
            node.health.mark_degraded()
        else:
            node.health.status = status

    # -- Capabilities --------------------------------------------------------

    def update_capabilities(
        self,
        node_id: str,
        capabilities: NodeCapabilities,
    ) -> None:
        """Replace a node's capability record."""
        node = self._nodes.get(node_id)
        if node is None:
            logger.debug("NodeRegistry.update_capabilities: unknown node %s", node_id)
            return
        node.capabilities = capabilities

    # -- Services ------------------------------------------------------------

    def register_service(self, node_id: str, service_name: str) -> None:
        """Record that *service_name* is running on *node_id*."""
        node = self._nodes.get(node_id)
        if node is None:
            logger.debug("NodeRegistry.register_service: unknown node %s", node_id)
            return
        if service_name not in node.services:
            node.services.append(service_name)

    # -- Queries -------------------------------------------------------------

    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        return self._nodes.get(node_id)

    def get_local_node(self) -> Optional[NodeInfo]:
        if self._local_node_id:
            return self._nodes.get(self._local_node_id)
        return next(
            (n for n in self._nodes.values() if n.role == NodeRole.LOCAL),
            None,
        )

    def get_remote_nodes(self) -> List[NodeInfo]:
        return [n for n in self._nodes.values() if n.role == NodeRole.REMOTE]

    def get_online_nodes(self) -> List[NodeInfo]:
        return [
            n for n in self._nodes.values()
            if n.health.status == NodeStatus.ONLINE
        ]

    def get_all_nodes(self) -> List[NodeInfo]:
        return list(self._nodes.values())

    # -- Serialisation -------------------------------------------------------

    def to_status_dict(self) -> Dict[str, Any]:
        """Serialise registry state for the cluster/nodes API endpoint."""
        local = self.get_local_node()
        remotes = self.get_remote_nodes()
        online = self.get_online_nodes()

        return {
            "total_nodes": len(self._nodes),
            "online_nodes": len(online),
            "local_node_id": self._local_node_id,
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "summary": {
                "local": local.to_dict() if local else None,
                "remote_count": len(remotes),
                "remote_nodes": [n.node_id for n in remotes],
            },
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_registry: Optional[NodeRegistry] = None


def get_node_registry() -> NodeRegistry:
    """Return the process-wide NodeRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
    return _registry
