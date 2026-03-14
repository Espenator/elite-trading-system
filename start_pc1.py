"""
Embodier Trader -- PC1 (ESPENMAIN) Control Plane Launcher.

Starts the control plane services:
  1. Backend API (port 8001) -- full monolith with all services
  2. Frontend    (port 5173) -- Vite React dashboard
  3. Remote Health Monitor   -- watches PC2 status

PC1 responsibilities:
  - Dashboard / frontend / command console
  - Full backend with signal engine, council gate, order executor
  - Health monitoring of PC2
  - DuckDB analytics
  - Data swarm (Alpaca, UW, FinViz collectors)
  - Log aggregation

Usage:
  python start_pc1.py              # Start all
  python start_pc1.py --no-frontend  # Backend only
"""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend-v2"

processes = []


def start_process(name, cmd, cwd, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    print(f"  > Starting {name}...")
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(cwd), env=full_env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        processes.append((name, proc))
        print(f"  [OK] {name} started (PID {proc.pid})")
        return proc
    except Exception as e:
        print(f"  [FAIL] {name} failed: {e}")
        return None


def cleanup(signum=None, frame=None):
    print("\nShutting down all processes...")
    for name, proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"  [OK] {name} stopped")
        except Exception:
            proc.kill()
            print(f"  [!] {name} force-killed")
    sys.exit(0)


def main():
    print("""
================================================================
  EMBODIER TRADER -- PC1 (ESPENMAIN)
  Control Plane -- Orchestration & Monitoring
================================================================
  Process 1: Backend API   (port 8001) -- Full monolith
  Process 2: Frontend      (port 5173) -- Vite + React
  Process 3: Health Monitor            -- Watches PC2
================================================================
""")

    no_frontend = "--no-frontend" in sys.argv
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    python = sys.executable

    # Remove stale PID file
    pid_file = ROOT / ".embodier.pid"
    if pid_file.exists():
        pid_file.unlink()

    # 1. Backend API (full monolith)
    start_process("Backend API", [python, "run_server.py"], BACKEND, env={
        "PC_ROLE": "primary",
    })
    time.sleep(3)

    # 2. Frontend
    if not no_frontend and FRONTEND.exists():
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        start_process("Frontend", [npm, "run", "dev"], FRONTEND)

    print(f"""
=======================================================
  All processes started!

  Dashboard:  http://localhost:5173
  API:        http://localhost:8001/health
  PC2 Status: http://localhost:8001/api/v1/cluster/pc2

  Press Ctrl+C to stop all processes.
=======================================================
""")

    # Monitor processes
    try:
        while True:
            for name, proc in list(processes):
                if proc.poll() is not None:
                    print(f"  [X] {name} exited (code {proc.returncode})")
                    out = proc.stdout.read()
                    if out:
                        for line in out.strip().split("\n")[-5:]:
                            print(f"    {line}")
            time.sleep(5)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
