"""PC Role Detection -- machine-aware service enablement.

Detects which machine we're running on (ESPENMAIN or ProfitTrader)
and enables/disables services accordingly. This is the single source
of truth for "what runs where" in the two-PC architecture.

Architecture:
  PC1 (ESPENMAIN) = Control Plane
    - Dashboard frontend
    - Health monitoring of PC2
    - Remote orchestration commands
    - Git/development
    - Log aggregation
    - Lightweight API proxy (optional)

  PC2 (ProfitTrader) = Execution Plane
    - FastAPI backend (full)
    - Council DAG runtime
    - brain_service gRPC (Ollama LLM)
    - Market data ingestion (Alpaca)
    - DuckDB trading data
    - GPU worker (PyTorch CUDA)
    - WebSocket event broadcasting
    - Trade execution router
    - Live Alpaca execution path

Usage:
    from app.core.pc_role import get_role, is_pc1, is_pc2, services_for_role
    role = get_role()  # "primary" or "secondary"
    if is_pc2():
        start_brain_service()
"""
import logging
import os
import socket
from dataclasses import dataclass, field
from typing import Dict, List, Set

log = logging.getLogger(__name__)

# Hostname -> role mapping
HOSTNAME_ROLES = {
    "espenmain": "primary",
    "espen-main": "primary",
    "profittrader": "secondary",
    "profit-trader": "secondary",
}

# IP -> role fallback (DHCP-reserved on AT&T BGW320-505)
IP_ROLES = {
    "192.168.1.105": "primary",
    "192.168.1.116": "secondary",
}


@dataclass
class PCRole:
    """Machine role and network identity."""
    hostname: str = ""
    role: str = "primary"           # "primary" (PC1) or "secondary" (PC2)
    friendly_name: str = ""         # "ESPENMAIN" or "ProfitTrader"
    lan_ip: str = ""
    peer_ip: str = ""               # The other PC's IP
    peer_hostname: str = ""

    @property
    def is_primary(self) -> bool:
        return self.role == "primary"

    @property
    def is_secondary(self) -> bool:
        return self.role == "secondary"


# Service manifest: what runs on each role
# True = must run, False = must not run, None = optional
SERVICE_MANIFEST: Dict[str, Dict[str, bool]] = {
    # ── Core Backend ──
    "fastapi_backend": {"primary": True, "secondary": True},
    "uvicorn_workers": {"primary": True, "secondary": True},

    # ── Data & Trading (PC2 primary, PC1 fallback) ──
    "alpaca_stream": {"primary": True, "secondary": True},
    "signal_engine": {"primary": True, "secondary": True},
    "council_gate": {"primary": True, "secondary": True},
    "order_executor": {"primary": True, "secondary": True},
    "position_manager": {"primary": True, "secondary": True},
    "outcome_tracker": {"primary": True, "secondary": True},

    # ── GPU / ML (PC2 only) ──
    "brain_service": {"primary": False, "secondary": True},
    "gpu_worker": {"primary": False, "secondary": True},
    "ollama": {"primary": False, "secondary": True},
    "cuda_xgboost": {"primary": False, "secondary": True},

    # ── Heavy Analytics (PC2 preferred) ──
    "turbo_scanner": {"primary": True, "secondary": True},
    "autonomous_scouts": {"primary": True, "secondary": True},
    "data_swarm": {"primary": True, "secondary": False},
    "backfill_orchestrator": {"primary": True, "secondary": False},

    # ── Distributed Council ──
    "council_coordinator_dispatch": {"primary": True, "secondary": False},
    "council_coordinator_worker": {"primary": False, "secondary": True},

    # ── Frontend ──
    "frontend_vite": {"primary": True, "secondary": True},

    # ── Monitoring ──
    "health_monitor": {"primary": True, "secondary": True},
    "remote_health_checker": {"primary": True, "secondary": False},
    "gpu_telemetry": {"primary": False, "secondary": True},

    # ── WebSocket ──
    "websocket_manager": {"primary": True, "secondary": True},
}

# Process -> CPU affinity mapping for PC2 (i7-13700: P=0-15, E=16-23)
PC2_AFFINITY_MAP = {
    # Latency-sensitive -> P-cores
    "fastapi_backend": "p_cores",
    "council_gate": "p_cores",
    "signal_engine": "p_cores",
    "brain_service": "p_cores",
    "websocket_manager": "p_cores",
    "order_executor": "p_cores",
    "alpaca_stream": "p_cores",

    # Background work -> E-cores
    "gpu_worker": "e_cores",
    "turbo_scanner": "e_cores",
    "autonomous_scouts": "e_cores",
    "backfill_orchestrator": "e_cores",
    "outcome_tracker": "e_cores",
    "health_monitor": "e_cores",
}

# Process -> priority mapping for PC2
PC2_PRIORITY_MAP = {
    "fastapi_backend": "high",
    "brain_service": "above_normal",
    "council_gate": "above_normal",
    "signal_engine": "above_normal",
    "order_executor": "high",
    "websocket_manager": "above_normal",
    "gpu_worker": "normal",
    "turbo_scanner": "below_normal",
    "autonomous_scouts": "below_normal",
    "health_monitor": "below_normal",
}


# ── Detection ────────────────────────────────────────────────────

_role: PCRole = None


def _detect_lan_ip() -> str:
    """Get the machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("192.168.1.1", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def get_role() -> PCRole:
    """Detect and return the PC role (singleton)."""
    global _role
    if _role is not None:
        return _role

    hostname = socket.gethostname().lower()
    lan_ip = _detect_lan_ip()

    # Priority: env var > hostname table > IP table > default
    env_role = os.getenv("PC_ROLE", "").lower()

    if env_role in ("primary", "secondary"):
        role = env_role
    elif hostname in HOSTNAME_ROLES:
        role = HOSTNAME_ROLES[hostname]
    elif lan_ip in IP_ROLES:
        role = IP_ROLES[lan_ip]
    else:
        role = "primary"  # safe default

    if role == "primary":
        friendly = "ESPENMAIN"
        peer_ip = "192.168.1.116"
        peer_hostname = "ProfitTrader"
    else:
        friendly = "ProfitTrader"
        peer_ip = "192.168.1.105"
        peer_hostname = "ESPENMAIN"

    _role = PCRole(
        hostname=socket.gethostname(),
        role=role,
        friendly_name=friendly,
        lan_ip=lan_ip,
        peer_ip=peer_ip,
        peer_hostname=peer_hostname,
    )

    log.info("PC Role: %s (%s) at %s | Peer: %s at %s",
             _role.friendly_name, _role.role, _role.lan_ip,
             _role.peer_hostname, _role.peer_ip)

    return _role


def is_pc1() -> bool:
    """Are we running on ESPENMAIN (control plane)?"""
    return get_role().is_primary


def is_pc2() -> bool:
    """Are we running on ProfitTrader (execution plane)?"""
    return get_role().is_secondary


def should_run_service(service_name: str) -> bool:
    """Check if a service should run on this machine."""
    role = get_role()
    manifest = SERVICE_MANIFEST.get(service_name)
    if manifest is None:
        return True  # unknown service -> run everywhere
    return manifest.get(role.role, True)


def services_for_role(role: str = None) -> Dict[str, bool]:
    """Get all services and whether they should run for a role."""
    if role is None:
        role = get_role().role
    return {
        svc: manifest.get(role, True)
        for svc, manifest in SERVICE_MANIFEST.items()
    }


def get_affinity(service_name: str) -> str:
    """Get CPU affinity recommendation for a service on PC2."""
    if not is_pc2():
        return "all"
    return PC2_AFFINITY_MAP.get(service_name, "all")


def get_priority(service_name: str) -> str:
    """Get process priority recommendation for a service on PC2."""
    if not is_pc2():
        return "normal"
    return PC2_PRIORITY_MAP.get(service_name, "normal")
