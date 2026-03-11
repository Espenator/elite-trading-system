#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  Embodier Trader — ESPENMAIN (PC1) Launcher
#  Starts backend API + frontend dev server for the primary node
#  Brain service (gRPC) runs on ProfitTrader (PC2: 192.168.1.116)
# ═══════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend-v2"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/.espenmain.pids"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║                                                      ║"
    echo "  ║    ███████╗███╗   ███╗██████╗  ██████╗ ██████╗       ║"
    echo "  ║    ██╔════╝████╗ ████║██╔══██╗██╔═══██╗██╔══██╗      ║"
    echo "  ║    █████╗  ██╔████╔██║██████╔╝██║   ██║██║  ██║      ║"
    echo "  ║    ██╔══╝  ██║╚██╔╝██║██╔══██╗██║   ██║██║  ██║      ║"
    echo "  ║    ███████╗██║ ╚═╝ ██║██████╔╝╚██████╔╝██████╔╝      ║"
    echo "  ║    ╚══════╝╚═╝     ╚═╝╚═════╝  ╚═════╝ ╚═════╝       ║"
    echo "  ║                                                      ║"
    echo "  ║           E M B O D I E R   T R A D E R              ║"
    echo "  ║         ─────────────────────────────────             ║"
    echo "  ║         ESPENMAIN  •  PC1  •  Primary Node           ║"
    echo "  ║                                                      ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

stop_services() {
    echo -e "${YELLOW}Stopping running services...${NC}"
    if [ -f "$PID_FILE" ]; then
        while IFS= read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
                echo -e "  Stopped PID $pid"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    # Also kill any orphaned processes on our ports
    for port in 8000 5173 5174; do
        pid=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}Services stopped.${NC}"
}

start_services() {
    banner

    mkdir -p "$LOG_DIR"
    mkdir -p "$SCRIPT_DIR/data"
    > "$PID_FILE"

    # ── Backend ───────────────────────────────────────
    echo -e "${BOLD}[1/2] Starting Backend API (port 8000)...${NC}"
    cd "$BACKEND_DIR"
    source venv/bin/activate 2>/dev/null || {
        echo -e "${YELLOW}  Creating Python venv...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt -q
    }

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
        > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" >> "$PID_FILE"
    echo -e "${GREEN}  Backend started (PID: $BACKEND_PID)${NC}"
    echo -e "  API:     http://localhost:8000"
    echo -e "  Swagger: http://localhost:8000/docs"
    echo ""

    # Wait for backend to be ready
    echo -e "  Waiting for backend..."
    for i in $(seq 1 30); do
        if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
            echo -e "${GREEN}  Backend is ready!${NC}"
            break
        fi
        sleep 1
    done

    # ── Frontend ──────────────────────────────────────
    echo -e "${BOLD}[2/2] Starting Frontend (port 5173)...${NC}"
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}  Installing npm dependencies...${NC}"
        npm install -q
    fi

    npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" >> "$PID_FILE"
    echo -e "${GREEN}  Frontend started (PID: $FRONTEND_PID)${NC}"
    echo -e "  UI:      http://localhost:5173"
    echo ""

    # ── Status ────────────────────────────────────────
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  ESPENMAIN (PC1) is ONLINE${NC}"
    echo -e ""
    echo -e "  Backend API:   ${GREEN}http://localhost:8000${NC}"
    echo -e "  Swagger Docs:  ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "  Frontend UI:   ${GREEN}http://localhost:5173${NC}"
    echo -e "  Brain (PC2):   ${YELLOW}192.168.1.116:50051${NC}"
    echo -e ""
    echo -e "  Logs:  $LOG_DIR/"
    echo -e "  Stop:  $0 stop"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
}

status() {
    echo -e "${BOLD}Embodier Trader — ESPENMAIN Status${NC}"
    echo ""
    # Check backend
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        echo -e "  Backend API:  ${GREEN}RUNNING${NC} (port 8000)"
    else
        echo -e "  Backend API:  ${RED}STOPPED${NC}"
    fi
    # Check frontend
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "  Frontend UI:  ${GREEN}RUNNING${NC} (port 5173)"
    else
        echo -e "  Frontend UI:  ${RED}STOPPED${NC}"
    fi
    # Check PC2 brain service
    if nc -z 192.168.1.116 50051 2>/dev/null; then
        echo -e "  Brain (PC2):  ${GREEN}CONNECTED${NC} (192.168.1.116:50051)"
    else
        echo -e "  Brain (PC2):  ${YELLOW}OFFLINE${NC} (192.168.1.116:50051)"
    fi
    echo ""
}

case "${1:-start}" in
    start)
        stop_services 2>/dev/null || true
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        start_services
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
