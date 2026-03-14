"""Hardware Profile -- detect and optimize for the local machine's hardware.

Designed for the two-PC architecture:
  PC1 (ESPENMAIN) -- orchestration/control, no GPU assumed
  PC2 (ProfitTrader) -- i7-13700 hybrid CPU + RTX 4080 16GB VRAM

Provides:
  - CPU topology detection (P-cores vs E-cores on Intel hybrid)
  - GPU detection and VRAM budgeting
  - Process affinity helpers (pin to P-cores or E-cores)
  - RAM allocation recommendations
  - Hardware profile summary for logging

Usage:
    from app.core.hardware_profile import get_hardware_profile, apply_affinity
    profile = get_hardware_profile()
    apply_affinity("p_cores")  # pin current process to performance cores
"""
import logging
import os
import platform
import socket
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


@dataclass
class CPUTopology:
    """CPU core topology for Intel hybrid (P-core + E-core) designs."""
    total_cores: int = 0
    total_threads: int = 0
    p_core_count: int = 0   # Performance cores
    e_core_count: int = 0   # Efficiency cores
    p_core_ids: List[int] = field(default_factory=list)  # Logical processor IDs
    e_core_ids: List[int] = field(default_factory=list)
    model_name: str = ""
    is_hybrid: bool = False


@dataclass
class GPUInfo:
    """GPU information from NVIDIA driver."""
    available: bool = False
    name: str = ""
    vram_total_mb: int = 0
    vram_free_mb: int = 0
    vram_used_mb: int = 0
    cuda_version: str = ""
    driver_version: str = ""
    compute_capability: Tuple[int, int] = (0, 0)
    cuda_cores: int = 0


@dataclass
class VRAMBudget:
    """VRAM allocation plan for PC2 RTX 4080."""
    total_mb: int = 0
    ollama_primary_mb: int = 0      # Main reasoning model
    ollama_secondary_mb: int = 0    # Lighter critic/fast model
    pytorch_mb: int = 0             # GPU worker tensors
    xgboost_mb: int = 0             # XGBoost CUDA histograms
    cuda_runtime_mb: int = 500      # CUDA context overhead
    safety_headroom_mb: int = 1000  # Never exceed total - headroom
    primary_model: str = ""
    secondary_model: str = ""


@dataclass
class HardwareProfile:
    """Complete hardware profile for the local machine."""
    hostname: str = ""
    pc_role: str = "unknown"        # "primary" (PC1) or "secondary" (PC2)
    os_name: str = ""
    cpu: CPUTopology = field(default_factory=CPUTopology)
    gpu: GPUInfo = field(default_factory=GPUInfo)
    vram_budget: VRAMBudget = field(default_factory=VRAMBudget)
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    python_version: str = ""

    def summary(self) -> str:
        """One-line summary for startup logging."""
        gpu_str = f"{self.gpu.name} ({self.gpu.vram_total_mb}MB)" if self.gpu.available else "None"
        cpu_str = f"{self.cpu.model_name} ({self.cpu.p_core_count}P+{self.cpu.e_core_count}E)" if self.cpu.is_hybrid else f"{self.cpu.model_name} ({self.cpu.total_cores}C/{self.cpu.total_threads}T)"
        return (
            f"[{self.hostname}] role={self.pc_role} | "
            f"CPU: {cpu_str} | GPU: {gpu_str} | "
            f"RAM: {self.ram_total_mb // 1024}GB"
        )

    def to_dict(self) -> dict:
        return {
            "hostname": self.hostname,
            "pc_role": self.pc_role,
            "cpu": {
                "model": self.cpu.model_name,
                "total_cores": self.cpu.total_cores,
                "total_threads": self.cpu.total_threads,
                "p_cores": self.cpu.p_core_count,
                "e_cores": self.cpu.e_core_count,
                "is_hybrid": self.cpu.is_hybrid,
            },
            "gpu": {
                "available": self.gpu.available,
                "name": self.gpu.name,
                "vram_total_mb": self.gpu.vram_total_mb,
                "vram_free_mb": self.gpu.vram_free_mb,
                "cuda_version": self.gpu.cuda_version,
            },
            "ram_total_mb": self.ram_total_mb,
        }


# ── CPU Topology Detection ──────────────────────────────────────

# Intel 13th-gen (Raptor Lake) P-core/E-core layout:
# i7-13700: 8P (16T) + 8E (8T) = 16C/24T
# P-cores = logical CPUs 0-15 (hyperthreaded pairs)
# E-cores = logical CPUs 16-23 (single-threaded)
KNOWN_HYBRID_CPUS = {
    "13th Gen Intel(R) Core(TM) i7-13700": {
        "p_cores": 8, "e_cores": 8, "p_threads": 16, "e_threads": 8,
        "p_core_ids": list(range(0, 16)),   # 0-15 (8 P-cores x 2 threads)
        "e_core_ids": list(range(16, 24)),  # 16-23 (8 E-cores x 1 thread)
    },
    "13th Gen Intel(R) Core(TM) i7-13700K": {
        "p_cores": 8, "e_cores": 8, "p_threads": 16, "e_threads": 8,
        "p_core_ids": list(range(0, 16)),
        "e_core_ids": list(range(16, 24)),
    },
    "13th Gen Intel(R) Core(TM) i9-13900K": {
        "p_cores": 8, "e_cores": 16, "p_threads": 16, "e_threads": 16,
        "p_core_ids": list(range(0, 16)),
        "e_core_ids": list(range(16, 32)),
    },
}


def _detect_cpu() -> CPUTopology:
    """Detect CPU topology including hybrid P/E core layout."""
    topo = CPUTopology()

    try:
        import psutil
        topo.total_cores = psutil.cpu_count(logical=False) or 0
        topo.total_threads = psutil.cpu_count(logical=True) or 0
    except ImportError:
        topo.total_cores = os.cpu_count() or 0
        topo.total_threads = topo.total_cores

    # Get CPU model name
    if sys.platform == "win32":
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "cpu", "get", "Name", "/value"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if line.startswith("Name="):
                    topo.model_name = line.split("=", 1)[1].strip()
                    break
        except Exception:
            topo.model_name = platform.processor() or "Unknown"
    else:
        topo.model_name = platform.processor() or "Unknown"

    # Check known hybrid CPU table
    for cpu_name, layout in KNOWN_HYBRID_CPUS.items():
        if cpu_name in topo.model_name:
            topo.is_hybrid = True
            topo.p_core_count = layout["p_cores"]
            topo.e_core_count = layout["e_cores"]
            topo.p_core_ids = layout["p_core_ids"]
            topo.e_core_ids = layout["e_core_ids"]
            log.info("Hybrid CPU detected: %s (%dP+%dE cores)",
                     cpu_name, topo.p_core_count, topo.e_core_count)
            break

    if not topo.is_hybrid:
        # Non-hybrid: all cores are equal
        topo.p_core_count = topo.total_cores
        topo.p_core_ids = list(range(topo.total_threads))

    return topo


def _detect_gpu() -> GPUInfo:
    """Detect NVIDIA GPU via PyTorch CUDA or nvidia-smi."""
    info = GPUInfo()

    # Try PyTorch first (most reliable)
    try:
        import torch
        if torch.cuda.is_available():
            info.available = True
            info.name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info.vram_total_mb = props.total_memory // (1024 * 1024)
            info.vram_free_mb = info.vram_total_mb  # approximate
            info.cuda_version = torch.version.cuda or ""
            info.compute_capability = (props.major, props.minor)
            info.cuda_cores = props.multi_processor_count * 128  # approximate
            try:
                free, total = torch.cuda.mem_get_info(0)
                info.vram_free_mb = free // (1024 * 1024)
                info.vram_used_mb = (total - free) // (1024 * 1024)
            except Exception:
                pass
            return info
    except ImportError:
        pass

    # Fallback: nvidia-smi
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,memory.used,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 5:
                info.available = True
                info.name = parts[0]
                info.vram_total_mb = int(parts[1])
                info.vram_free_mb = int(parts[2])
                info.vram_used_mb = int(parts[3])
                info.driver_version = parts[4]
    except Exception:
        pass

    return info


def _compute_vram_budget(gpu: GPUInfo) -> VRAMBudget:
    """Compute VRAM allocation plan for available GPU.

    Strategy for RTX 4080 (16GB):
      - Primary model: gemma3:12b (8.1GB) for hypothesis/deep reasoning
      - Secondary model: qwen3:8b (5.2GB) for critic/fast tasks
      - PyTorch tensors: ~1GB for GPU feature engineering
      - XGBoost: ~0.5GB for CUDA histogram method
      - CUDA runtime: ~0.5GB overhead
      - Safety headroom: 1GB
      Total: ~16.3GB -- tight but workable with model swapping

    If VRAM > 20GB (e.g., RTX 4090 24GB):
      - Primary model: qwen2.5:32b (19GB) -- loads alongside smaller workloads
    """
    budget = VRAMBudget(total_mb=gpu.vram_total_mb)

    if not gpu.available:
        return budget

    vram = gpu.vram_total_mb

    if vram >= 20000:
        # 20GB+ (RTX 4090, A5000, etc.)
        budget.primary_model = "qwen2.5:32b"
        budget.ollama_primary_mb = 19000
        budget.secondary_model = "qwen3:8b"
        budget.ollama_secondary_mb = 5200
        budget.pytorch_mb = 1000
        budget.xgboost_mb = 500
    elif vram >= 14000:
        # 14-20GB (RTX 4080 16GB, RTX 4080 Super)
        budget.primary_model = "gemma3:12b"
        budget.ollama_primary_mb = 8100
        budget.secondary_model = "qwen3:8b"
        budget.ollama_secondary_mb = 5200
        budget.pytorch_mb = 1000
        budget.xgboost_mb = 500
    elif vram >= 8000:
        # 8-14GB (RTX 4070, RTX 3070)
        budget.primary_model = "qwen3:8b"
        budget.ollama_primary_mb = 5200
        budget.secondary_model = "phi4-mini"
        budget.ollama_secondary_mb = 2500
        budget.pytorch_mb = 500
        budget.xgboost_mb = 256
    else:
        # < 8GB (RTX 3060 6GB, etc.)
        budget.primary_model = "phi4-mini"
        budget.ollama_primary_mb = 2500
        budget.secondary_model = ""
        budget.ollama_secondary_mb = 0
        budget.pytorch_mb = 256
        budget.xgboost_mb = 128

    return budget


def _get_ram_info() -> Tuple[int, int]:
    """Get total and available RAM in MB."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return mem.total // (1024 * 1024), mem.available // (1024 * 1024)
    except ImportError:
        return 0, 0


# ── Singleton Profile ────────────────────────────────────────────

_profile: Optional[HardwareProfile] = None


def get_hardware_profile() -> HardwareProfile:
    """Get or create the hardware profile for this machine (singleton)."""
    global _profile
    if _profile is not None:
        return _profile

    hostname = socket.gethostname()
    pc_role = os.getenv("PC_ROLE", "primary")

    # Auto-detect role from hostname if not explicitly set
    if pc_role == "primary" and hostname.lower() in ("profittrader", "profit-trader"):
        pc_role = "secondary"
    elif pc_role == "primary" and hostname.lower() in ("espenmain", "espen-main"):
        pc_role = "primary"

    cpu = _detect_cpu()
    gpu = _detect_gpu()
    vram_budget = _compute_vram_budget(gpu)
    ram_total, ram_avail = _get_ram_info()

    _profile = HardwareProfile(
        hostname=hostname,
        pc_role=pc_role,
        os_name=f"{platform.system()} {platform.release()}",
        cpu=cpu,
        gpu=gpu,
        vram_budget=vram_budget,
        ram_total_mb=ram_total,
        ram_available_mb=ram_avail,
        python_version=platform.python_version(),
    )

    log.info("Hardware profile: %s", _profile.summary())
    return _profile


# ── CPU Affinity Helpers ─────────────────────────────────────────

def apply_affinity(core_type: str = "p_cores", pid: int = 0) -> bool:
    """Set CPU affinity for a process.

    Args:
        core_type: "p_cores" for latency-sensitive, "e_cores" for background
        pid: Process ID (0 = current process)

    Returns:
        True if affinity was set successfully

    Usage for PC2 (i7-13700):
        P-cores (0-15): FastAPI, council runner, brain_service, WebSocket
        E-cores (16-23): DuckDB analytics, retraining, postmortems, scheduler
    """
    profile = get_hardware_profile()
    if not profile.cpu.is_hybrid:
        log.debug("Non-hybrid CPU -- affinity not applicable")
        return False

    if core_type == "p_cores":
        core_ids = profile.cpu.p_core_ids
    elif core_type == "e_cores":
        core_ids = profile.cpu.e_core_ids
    elif core_type == "all":
        core_ids = profile.cpu.p_core_ids + profile.cpu.e_core_ids
    else:
        log.warning("Unknown core_type: %s", core_type)
        return False

    if not core_ids:
        return False

    try:
        import psutil
        p = psutil.Process(pid or os.getpid())
        p.cpu_affinity(core_ids)
        log.info("CPU affinity set to %s (cores %s) for PID %d",
                 core_type, f"{core_ids[0]}-{core_ids[-1]}", p.pid)
        return True
    except ImportError:
        log.debug("psutil not available -- cannot set CPU affinity")
        return False
    except Exception as e:
        log.warning("Failed to set CPU affinity: %s", e)
        return False


def set_process_priority(priority: str = "high", pid: int = 0) -> bool:
    """Set process priority on Windows.

    Args:
        priority: "realtime", "high", "above_normal", "normal", "below_normal", "idle"
        pid: Process ID (0 = current process)
    """
    if sys.platform != "win32":
        try:
            import psutil
            p = psutil.Process(pid or os.getpid())
            nice_map = {"high": -10, "above_normal": -5, "normal": 0,
                        "below_normal": 5, "idle": 19}
            p.nice(nice_map.get(priority, 0))
            return True
        except Exception:
            return False

    try:
        import psutil
        p = psutil.Process(pid or os.getpid())
        priority_map = {
            "realtime": psutil.REALTIME_PRIORITY_CLASS,
            "high": psutil.HIGH_PRIORITY_CLASS,
            "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
            "normal": psutil.NORMAL_PRIORITY_CLASS,
            "below_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS,
            "idle": psutil.IDLE_PRIORITY_CLASS,
        }
        cls = priority_map.get(priority, psutil.NORMAL_PRIORITY_CLASS)
        p.nice(cls)
        log.info("Process priority set to %s for PID %d", priority, p.pid)
        return True
    except ImportError:
        log.debug("psutil not available -- cannot set priority")
        return False
    except Exception as e:
        log.warning("Failed to set process priority: %s", e)
        return False


# ── RAM Allocation Recommendations ───────────────────────────────

def get_ram_allocation(profile: Optional[HardwareProfile] = None) -> Dict[str, int]:
    """Recommended RAM allocation in MB for PC2 services.

    For 32GB RAM (ProfitTrader):
      Python main process:   ~2GB (FastAPI + services)
      DuckDB:                ~4GB (WAL + query buffers)
      Ollama:                ~12GB (model weights in RAM, overflow from VRAM)
      GPU Worker (PyTorch):  ~2GB (tensor staging)
      Brain Service:         ~1GB (gRPC server + buffers)
      OS + System:           ~4GB
      Headroom:              ~7GB
    """
    if profile is None:
        profile = get_hardware_profile()

    ram = profile.ram_total_mb
    if ram >= 28000:
        # 32GB
        return {
            "python_main": 2048,
            "duckdb": 4096,
            "ollama": 12288,
            "gpu_worker": 2048,
            "brain_service": 1024,
            "os_system": 4096,
            "headroom": ram - 25600,
        }
    elif ram >= 14000:
        # 16GB
        return {
            "python_main": 1536,
            "duckdb": 2048,
            "ollama": 6144,
            "gpu_worker": 1024,
            "brain_service": 512,
            "os_system": 3072,
            "headroom": ram - 14336,
        }
    else:
        # 8GB or less
        return {
            "python_main": 1024,
            "duckdb": 1024,
            "ollama": 2048,
            "gpu_worker": 512,
            "brain_service": 256,
            "os_system": 2048,
            "headroom": max(0, ram - 6912),
        }
