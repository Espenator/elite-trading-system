"""
Embodier Trader -- PC2 (ProfitTrader) Multi-Process Launcher.

Starts 3 separate processes to fully utilize the RTX 4080:

  1. API Server    (port 8001) -- Lightweight FastAPI, no engine, never blocks
  2. GPU Worker    (background) -- PyTorch CUDA feature engineering + XGBoost scoring
  3. Brain Service (port 50051) -- Ollama gRPC for LLM inference

Frontend:
  4. Vite dev server (port 5173) -- proxied to local API server

Architecture:
  PC1 (ESPENMAIN) -> Redis Streams -> PC2 API Server -> WebSocket -> Dashboard
                                  -> GPU Worker -> PyTorch CUDA -> Results
  PC2 Brain gRPC <- API Server <- User requests

Usage:
  python start_pc2.py           # Start all
  python start_pc2.py --no-frontend  # Backend only
  python start_pc2.py --gpu-only     # Just GPU worker
"""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend-v2"
BRAIN = ROOT / "brain_service"

processes = []


# ── Ollama GPU optimization flags (set before any subprocess starts) ──
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")
os.environ.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
os.environ.setdefault("OLLAMA_NUM_GPU", "1")
os.environ.setdefault("OLLAMA_GPU_LAYERS", "50")


def banner():
    print(f"""
{CYAN}{BOLD}================================================================
  EMBODIER TRADER -- PC2 (ProfitTrader)
  Split Architecture with GPU Acceleration
================================================================
  Process 1: API Server     (port 8001)  -- FastAPI Lightweight
  Process 2: GPU Worker     (Redis queue) -- RTX 4080 CUDA
  Process 3: Brain Service  (port 50051) -- Ollama gRPC
  Process 4: Frontend       (port 5173)  -- Vite + React
================================================================{RESET}
""")


def start_process(name, cmd, cwd, env=None):
    """Start a subprocess and track it."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    print(f"  {GREEN}> Starting {name}...{RESET}")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=full_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append((name, proc))
        print(f"  {GREEN}[OK] {name} started (PID {proc.pid}){RESET}")
        return proc
    except Exception as e:
        print(f"  {RED}[FAIL] {name} failed: {e}{RESET}")
        return None


def cleanup(signum=None, frame=None):
    """Gracefully stop all processes."""
    print(f"\n{YELLOW}Shutting down all processes...{RESET}")
    for name, proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"  {GREEN}[OK] {name} stopped{RESET}")
        except Exception:
            proc.kill()
            print(f"  {YELLOW}[!] {name} force-killed{RESET}")
    sys.exit(0)


def main():
    banner()

    gpu_only = "--gpu-only" in sys.argv
    no_frontend = "--no-frontend" in sys.argv

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    python = sys.executable

    # ── 1. Remove stale PID file ──
    pid_file = BACKEND / ".." / ".embodier.pid"
    if pid_file.exists():
        pid_file.unlink()
        print(f"  {YELLOW}Removed stale PID file{RESET}")

    # ── Hardware-aware CPU affinity (i7-13700: P=0-15, E=16-23) ──
    def apply_affinity_to_proc(proc, core_type):
        """Set CPU affinity on a subprocess after it starts."""
        if proc is None:
            return
        try:
            import psutil
            p = psutil.Process(proc.pid)
            if core_type == "p_cores":
                p.cpu_affinity(list(range(0, 16)))
                p.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
            elif core_type == "e_cores":
                p.cpu_affinity(list(range(16, 24)))
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            print(f"    [{core_type}] PID {proc.pid}")
        except Exception as e:
            print(f"    [affinity skip] {e}")

    # ── Pre-warm Ollama models (reduce first-call latency from ~19s to ~2s) ──
    def prewarm_ollama():
        """Load primary model into GPU VRAM before brain_service starts."""
        import urllib.request
        import json as _json
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        primary_model = os.environ.get("BRAIN_OLLAMA_MODEL", "gemma3:12b")
        print(f"  {CYAN}Pre-warming {primary_model} into VRAM...{RESET}", end="", flush=True)
        try:
            req = urllib.request.Request(
                f"{ollama_url}/api/generate",
                data=_json.dumps({"model": primary_model, "prompt": "hello", "stream": False}).encode(),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=120)
            print(f" {GREEN}[OK]{RESET}")
        except Exception as e:
            print(f" {YELLOW}[skip: {e}]{RESET}")

    if gpu_only:
        # Just the GPU worker
        p = start_process("GPU Worker", [python, "gpu_worker.py"], BACKEND)
        apply_affinity_to_proc(p, "e_cores")
    else:
        # ── 1b. Pre-warm Ollama primary model ──
        prewarm_ollama()

        # ── 2. Brain Service (gRPC on 50051) -- P-cores (latency-sensitive) ──
        brain_server = BRAIN / "server.py"
        if brain_server.exists():
            p = start_process("Brain Service", [python, "server.py"], BRAIN)
            apply_affinity_to_proc(p, "p_cores")
            time.sleep(2)

        # ── 3. GPU Worker -- E-cores (background batch work) ──
        p = start_process("GPU Worker", [python, "gpu_worker.py"], BACKEND)
        apply_affinity_to_proc(p, "e_cores")
        time.sleep(1)

        # ── 4. API Server -- P-cores (latency-sensitive HTTP) ──
        p = start_process("API Server", [python, "api_server.py"], BACKEND)
        apply_affinity_to_proc(p, "p_cores")
        time.sleep(2)

        # ── 5. Frontend (Vite) ──
        if not no_frontend and FRONTEND.exists():
            npm = "npm.cmd" if sys.platform == "win32" else "npm"
            start_process("Frontend", [npm, "run", "dev"], FRONTEND)

    print(f"""
{BOLD}{GREEN}======================================================={RESET}
{BOLD}  All processes started!{RESET}

  {CYAN}Dashboard:  http://localhost:5173{RESET}
  {CYAN}API:        http://localhost:8001/health{RESET}
  {CYAN}Brain gRPC: localhost:50051{RESET}
  {CYAN}GPU Status: http://localhost:8001/api/v1/health{RESET}

  Press Ctrl+C to stop all processes.
{BOLD}{GREEN}======================================================={RESET}
""")

    # Monitor processes
    try:
        while True:
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"  {RED}[X] {name} exited (code {proc.returncode}){RESET}")
                    # Read any remaining output
                    out = proc.stdout.read()
                    if out:
                        for line in out.strip().split("\n")[-5:]:
                            print(f"    {line}")
            time.sleep(5)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
