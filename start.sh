#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# Elite Trading System — One-Command Launcher
# Usage:  ./start.sh [docker|local|stop]
# ═══════════════════════════════════════════════════════════════
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

banner() {
  echo -e "${CYAN}"
  echo "  ╔═══════════════════════════════════════════════╗"
  echo "  ║   ELITE TRADING SYSTEM — Embodier.ai          ║"
  echo "  ║   AI-Powered 17-Agent Council Trading          ║"
  echo "  ╚═══════════════════════════════════════════════╝"
  echo -e "${NC}"
}

check_env() {
  if [ ! -f backend/.env ]; then
    echo -e "${YELLOW}No backend/.env found — copying from .env.example${NC}"
    cp backend/.env.example backend/.env
    echo -e "${YELLOW}Edit backend/.env with your API keys before live trading.${NC}"
  fi
}

# ── Docker Mode (recommended) ────────────────────────────────
start_docker() {
  echo -e "${GREEN}Starting with Docker Compose...${NC}"
  check_env
  docker compose up --build -d
  echo ""
  echo -e "${GREEN}Services starting:${NC}"
  echo -e "  Backend API:  ${CYAN}http://localhost:8000${NC}"
  echo -e "  Frontend UI:  ${CYAN}http://localhost:3000${NC}"
  echo -e "  API Docs:     ${CYAN}http://localhost:8000/docs${NC}"
  echo ""
  echo -e "${YELLOW}Waiting for backend health check...${NC}"
  for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
      echo -e "${GREEN}Backend is healthy!${NC}"
      echo -e "\nOpen ${CYAN}http://localhost:3000${NC} in your browser."
      return 0
    fi
    sleep 2
  done
  echo -e "${YELLOW}Backend still starting — check: docker compose logs -f${NC}"
}

stop_docker() {
  echo -e "${YELLOW}Stopping Docker services...${NC}"
  docker compose down
  echo -e "${GREEN}Stopped.${NC}"
}

# ── Local Dev Mode ────────────────────────────────────────────
start_local() {
  echo -e "${GREEN}Starting in local development mode...${NC}"
  check_env

  # Backend
  echo -e "${CYAN}[1/2] Starting backend on port 8000...${NC}"
  cd "$ROOT_DIR/backend"
  if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
  else
    VENV_DIR=$([ -d "venv" ] && echo "venv" || echo ".venv")
    source "$VENV_DIR/bin/activate"
  fi
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
  BACKEND_PID=$!
  echo "$BACKEND_PID" > "$ROOT_DIR/.backend.pid"
  cd "$ROOT_DIR"

  # Frontend
  echo -e "${CYAN}[2/2] Starting frontend on port 3000...${NC}"
  cd "$ROOT_DIR/frontend-v2"
  if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
  fi
  npm run dev &
  FRONTEND_PID=$!
  echo "$FRONTEND_PID" > "$ROOT_DIR/.frontend.pid"
  cd "$ROOT_DIR"

  echo ""
  echo -e "${GREEN}Both services starting:${NC}"
  echo -e "  Backend API:  ${CYAN}http://localhost:8000${NC}  (PID: $BACKEND_PID)"
  echo -e "  Frontend UI:  ${CYAN}http://localhost:3000${NC}  (PID: $FRONTEND_PID)"
  echo -e "  API Docs:     ${CYAN}http://localhost:8000/docs${NC}"
  echo ""
  echo -e "Stop with: ${YELLOW}./start.sh stop${NC}"
  echo ""

  # Wait for either to exit
  wait
}

stop_local() {
  echo -e "${YELLOW}Stopping local services...${NC}"
  if [ -f "$ROOT_DIR/.backend.pid" ]; then
    kill "$(cat "$ROOT_DIR/.backend.pid")" 2>/dev/null || true
    rm -f "$ROOT_DIR/.backend.pid"
  fi
  if [ -f "$ROOT_DIR/.frontend.pid" ]; then
    kill "$(cat "$ROOT_DIR/.frontend.pid")" 2>/dev/null || true
    rm -f "$ROOT_DIR/.frontend.pid"
  fi
  # Also kill any stray processes on the ports
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
  lsof -ti:3000 | xargs kill -9 2>/dev/null || true
  echo -e "${GREEN}Stopped.${NC}"
}

# ── Main ──────────────────────────────────────────────────────
banner

case "${1:-docker}" in
  docker)
    start_docker
    ;;
  local)
    start_local
    ;;
  stop)
    stop_local
    stop_docker 2>/dev/null || true
    ;;
  *)
    echo "Usage: ./start.sh [docker|local|stop]"
    echo ""
    echo "  docker  — Run with Docker Compose (recommended, no port battles)"
    echo "  local   — Run backend + frontend directly (dev mode)"
    echo "  stop    — Stop all services"
    exit 1
    ;;
esac
