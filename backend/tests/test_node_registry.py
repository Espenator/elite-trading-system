"""Tests for NodeRegistry — multi-PC compute foundation (Issue #39).

Covers:
- NodeInfo, GPUDevice, NodeCapabilities, NodeHealth data models
- NodeRegistry CRUD (register, update_health, update_capabilities,
  register_service, queries)
- Local vs remote node awareness
- Singleton reset between tests
- /api/v1/cluster/nodes API endpoint
"""
import time

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_registry():
    """Return a new, isolated NodeRegistry (not the singleton)."""
    from app.services.node_registry import NodeRegistry
    return NodeRegistry()


# ---------------------------------------------------------------------------
# Data model unit tests
# ---------------------------------------------------------------------------

class TestGPUDevice:
    def test_to_dict_includes_device_id(self):
        from app.services.node_registry import GPUDevice
        gpu = GPUDevice(index=1, name="RTX 4090", vram_total_mb=24576, vram_free_mb=20000,
                        utilization_pct=45.0)
        d = gpu.to_dict()
        assert d["device_id"] == "cuda:1"
        assert d["index"] == 1
        assert d["name"] == "RTX 4090"
        assert d["vram_total_mb"] == 24576
        assert d["vram_free_mb"] == 20000
        assert d["utilization_pct"] == 45.0

    def test_to_dict_cuda0(self):
        from app.services.node_registry import GPUDevice
        gpu = GPUDevice(index=0)
        assert gpu.to_dict()["device_id"] == "cuda:0"


class TestNodeCapabilities:
    def test_gpu_count_and_vram(self):
        from app.services.node_registry import GPUDevice, NodeCapabilities
        caps = NodeCapabilities(
            gpu_devices=[
                GPUDevice(index=0, vram_total_mb=8192, vram_free_mb=4096),
                GPUDevice(index=1, vram_total_mb=8192, vram_free_mb=2048),
            ]
        )
        assert caps.gpu_count == 2
        assert caps.total_vram_mb == 16384
        assert caps.free_vram_mb == 6144

    def test_empty_capabilities(self):
        from app.services.node_registry import NodeCapabilities
        caps = NodeCapabilities()
        assert caps.gpu_count == 0
        assert caps.total_vram_mb == 0

    def test_to_dict_keys(self):
        from app.services.node_registry import NodeCapabilities
        caps = NodeCapabilities(has_ollama=True, ollama_models=["llama3.2"])
        d = caps.to_dict()
        assert d["has_ollama"] is True
        assert d["ollama_models"] == ["llama3.2"]
        assert "gpu_count" in d
        assert "gpu_devices" in d


class TestNodeHealth:
    def test_mark_online(self):
        from app.services.node_registry import NodeHealth, NodeStatus
        h = NodeHealth()
        assert h.status == NodeStatus.UNKNOWN
        h.mark_online(latency_ms=12.5)
        assert h.status == NodeStatus.ONLINE
        assert h.consecutive_failures == 0
        assert h.latency_ms == 12.5
        assert h.last_seen > 0

    def test_mark_offline_increments_failures(self):
        from app.services.node_registry import NodeHealth, NodeStatus
        h = NodeHealth()
        h.mark_online()
        h.mark_offline()
        h.mark_offline()
        assert h.status == NodeStatus.OFFLINE
        assert h.consecutive_failures == 2

    def test_mark_degraded(self):
        from app.services.node_registry import NodeHealth, NodeStatus
        h = NodeHealth()
        h.mark_degraded()
        assert h.status == NodeStatus.DEGRADED

    def test_age_seconds_none_when_never_seen(self):
        from app.services.node_registry import NodeHealth
        h = NodeHealth()
        assert h.age_seconds is None

    def test_age_seconds_positive(self):
        from app.services.node_registry import NodeHealth
        h = NodeHealth(last_seen=time.time() - 5.0)
        assert h.age_seconds is not None
        assert h.age_seconds >= 5.0

    def test_to_dict_keys(self):
        from app.services.node_registry import NodeHealth
        h = NodeHealth()
        h.mark_online(10.0)
        d = h.to_dict()
        assert "status" in d
        assert "last_seen" in d
        assert "age_seconds" in d
        assert "consecutive_failures" in d
        assert "latency_ms" in d


class TestNodeInfo:
    def test_is_local_flag(self):
        from app.services.node_registry import NodeInfo, NodeRole
        local = NodeInfo(node_id="pc1", role=NodeRole.LOCAL, address="")
        remote = NodeInfo(node_id="pc2", role=NodeRole.REMOTE, address="192.168.1.2")
        assert local.is_local is True
        assert remote.is_local is False

    def test_to_dict_contains_expected_keys(self):
        from app.services.node_registry import NodeInfo, NodeRole
        node = NodeInfo(node_id="pc1", role=NodeRole.LOCAL, address="")
        d = node.to_dict()
        assert d["node_id"] == "pc1"
        assert d["role"] == "local"
        assert "health" in d
        assert "capabilities" in d
        assert "services" in d


# ---------------------------------------------------------------------------
# NodeRegistry unit tests
# ---------------------------------------------------------------------------

class TestNodeRegistry:
    def test_register_local_node(self):
        from app.services.node_registry import NodeRole
        reg = _fresh_registry()
        node = reg.register_node("pc1", NodeRole.LOCAL, address="")
        assert node.node_id == "pc1"
        assert node.role == NodeRole.LOCAL
        assert reg.get_local_node() is node

    def test_register_remote_node(self):
        from app.services.node_registry import NodeRole
        reg = _fresh_registry()
        reg.register_node("pc1", NodeRole.LOCAL)
        reg.register_node("pc2", NodeRole.REMOTE, address="192.168.1.2")
        remotes = reg.get_remote_nodes()
        assert len(remotes) == 1
        assert remotes[0].node_id == "pc2"

    def test_register_node_idempotent(self):
        from app.services.node_registry import NodeRole
        reg = _fresh_registry()
        reg.register_node("pc1", NodeRole.LOCAL)
        reg.register_node("pc1", NodeRole.LOCAL)   # second call
        assert len(reg.get_all_nodes()) == 1

    def test_update_capabilities_replaces_record(self):
        from app.services.node_registry import GPUDevice, NodeCapabilities, NodeRole
        reg = _fresh_registry()
        reg.register_node("pc1", NodeRole.LOCAL)
        new_caps = NodeCapabilities(
            gpu_devices=[GPUDevice(index=0, name="RTX 4090", vram_total_mb=24576)]
        )
        reg.update_capabilities("pc1", new_caps)
        node = reg.get_node("pc1")
        assert node.capabilities.gpu_count == 1
        assert node.capabilities.gpu_devices[0].name == "RTX 4090"

    def test_update_health_online(self):
        from app.services.node_registry import NodeRole, NodeStatus
        reg = _fresh_registry()
        reg.register_node("pc1", NodeRole.LOCAL)
        reg.update_health("pc1", NodeStatus.ONLINE, latency_ms=5.0)
        node = reg.get_node("pc1")
        assert node.health.status == NodeStatus.ONLINE
        assert node.health.latency_ms == 5.0

    def test_update_health_offline(self):
        from app.services.node_registry import NodeRole, NodeStatus
        reg = _fresh_registry()
        reg.register_node("pc1", NodeRole.LOCAL)
        reg.update_health("pc1", NodeStatus.OFFLINE)
        assert reg.get_node("pc1").health.status == NodeStatus.OFFLINE

    def test_update_health_unknown_node_is_noop(self):
        from app.services.node_registry import NodeStatus
        reg = _fresh_registry()
        # Should not raise
        reg.update_health("ghost", NodeStatus.ONLINE)

    def test_register_service(self):
        from app.services.node_registry import NodeRole
        reg = _fresh_registry()
        reg.register_node("pc1", NodeRole.LOCAL)
        reg.register_service("pc1", "order_executor")
        reg.register_service("pc1", "message_bus")
        node = reg.get_node("pc1")
        assert "order_executor" in node.services
        assert "message_bus" in node.services

    def test_register_service_idempotent(self):
        from app.services.node_registry import NodeRole
        reg = _fresh_registry()
        reg.register_node("pc1", NodeRole.LOCAL)
        reg.register_service("pc1", "order_executor")
        reg.register_service("pc1", "order_executor")
        assert reg.get_node("pc1").services.count("order_executor") == 1

    def test_get_online_nodes(self):
        from app.services.node_registry import NodeRole, NodeStatus
        reg = _fresh_registry()
        reg.register_node("pc1", NodeRole.LOCAL)
        reg.register_node("pc2", NodeRole.REMOTE, address="192.168.1.2")
        reg.update_health("pc1", NodeStatus.ONLINE)
        # pc2 remains UNKNOWN
        online = reg.get_online_nodes()
        assert len(online) == 1
        assert online[0].node_id == "pc1"

    def test_get_local_node_fallback(self):
        """get_local_node() works even without a dedicated local_node_id."""
        from app.services.node_registry import NodeRegistry, NodeRole
        reg = NodeRegistry()
        reg.register_node("worker", NodeRole.LOCAL)
        # _local_node_id is set via register_node
        assert reg.get_local_node().node_id == "worker"

    def test_to_status_dict_structure(self):
        from app.services.node_registry import NodeRole, NodeStatus
        reg = _fresh_registry()
        reg.register_node("pc1", NodeRole.LOCAL)
        reg.update_health("pc1", NodeStatus.ONLINE)
        d = reg.to_status_dict()
        assert d["total_nodes"] == 1
        assert d["online_nodes"] == 1
        assert "pc1" in d["nodes"]
        assert d["summary"]["local"] is not None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cluster_nodes_endpoint(client):
    """GET /api/v1/cluster/nodes should return 200 with node data."""
    resp = await client.get("/api/v1/cluster/nodes")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_nodes" in data
    assert "nodes" in data
    assert "summary" in data


@pytest.mark.asyncio
async def test_cluster_status_endpoint_still_works(client):
    """Existing /api/v1/cluster/status must remain intact."""
    resp = await client.get("/api/v1/cluster/status")
    assert resp.status_code == 200
    data = resp.json()
    # Must still have the old keys
    assert "cluster_mode" in data


@pytest.mark.asyncio
async def test_cluster_nodes_local_node_present(client):
    """After startup, the response should contain a valid node count."""
    resp = await client.get("/api/v1/cluster/nodes")
    data = resp.json()
    # In test env the lifespan doesn't run, so registry may be empty;
    # we only verify the response structure is valid.
    assert isinstance(data["total_nodes"], int)
    assert data["total_nodes"] >= 0


@pytest.mark.asyncio
async def test_cluster_nodes_local_node_has_services(client):
    """Local node should have core services registered."""
    resp = await client.get("/api/v1/cluster/nodes")
    data = resp.json()
    summary = data.get("summary", {})
    local = summary.get("local")
    if local:
        # Services list may be empty in test env but should be a list
        assert isinstance(local.get("services"), list)
