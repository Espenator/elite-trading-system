#!/usr/bin/env bash
# Embodier Trader v4.0.0 — Linux/Unix launcher
# Cross-platform equivalent of start-embodier.ps1

set -e
set -o pipefail

# Parse arguments
SKIP_FRONTEND=0
BACKEND_PORT=0
FRONTEND_PORT=0
MAX_RESTARTS=3

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-frontend)
            SKIP_FRONTEND=1
            shift
            ;;
        --backend-port)
            BACKEND_PORT="$2"
            shift 2
            ;;
        --frontend-port)
            FRONTEND_PORT="$2"
            shift 2
            ;;
        --max-restarts)
            MAX_RESTARTS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-frontend       Start backend only (no frontend)"
            echo "  --backend-port PORT   Override backend port (default: 8000 or from .env)"
            echo "  --frontend-port PORT  Override frontend port (default: 3000 or from .env)"
            echo "  --max-restarts N      Maximum restart attempts (default: 3)"
            echo "  -h, --help           Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Determine script root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend-v2"
LOG_DIR="$ROOT/logs"
ENV_FILE="$BACKEND_DIR/.env"

# Ensure logs directory
mkdir -p "$LOG_DIR"

# Timestamped log helper
log() {
    local msg="$1"
    local color="$2"
    local ts=$(date +%H:%M:%S)

    case "$color" in
        red)     echo -e "\033[0;31m  [$ts] $msg\033[0m" ;;
        green)   echo -e "\033[0;32m  [$ts] $msg\033[0m" ;;
        yellow)  echo -e "\033[0;33m  [$ts] $msg\033[0m" ;;
        cyan)    echo -e "\033[0;36m  [$ts] $msg\033[0m" ;;
        gray)    echo -e "\033[0;90m  [$ts] $msg\033[0m" ;;
        *)       echo "  [$ts] $msg" ;;
    esac
}

# Read value from .env file
get_env_value() {
    local key="$1"
    local default="$2"

    if [[ -f "$ENV_FILE" ]]; then
        local value=$(grep "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '\r' | sed 's/^["'\'']\(.*\)["'\'']$/\1/')
        if [[ -n "$value" ]]; then
            echo "$value"
            return
        fi
    fi
    echo "$default"
}

# Pre-flight: Validate Python and Node
test_prerequisites() {
    local ok=1

    # Check Python
    if command -v python3 &> /dev/null; then
        local py_version=$(python3 --version 2>&1 | awk '{print $2}')
        local py_major=$(echo "$py_version" | cut -d. -f1)
        local py_minor=$(echo "$py_version" | cut -d. -f2)

        if [[ "$py_major" -lt 3 ]] || [[ "$py_major" -eq 3 && "$py_minor" -lt 10 ]]; then
            log "Python $py_version found but 3.10+ required" red
            ok=0
        else
            log "Python $py_version" green
        fi
    else
        log "Python3 not found. Install Python 3.10+ from https://python.org/downloads" red
        ok=0
    fi

    # Check Node.js (only if not skipping frontend)
    if [[ $SKIP_FRONTEND -eq 0 ]]; then
        if command -v node &> /dev/null; then
            local node_version=$(node --version 2>&1 | sed 's/v//')
            local node_major=$(echo "$node_version" | cut -d. -f1)

            if [[ "$node_major" -lt 18 ]]; then
                log "Node.js v$node_version found but v18+ required" red
                ok=0
            else
                log "Node.js v$node_version" green
            fi
        else
            log "Node.js not found. Install Node.js 18+ from https://nodejs.org" red
            ok=0
        fi
    fi

    if [[ $ok -eq 0 ]]; then
        log "Pre-flight check FAILED - install missing tools and retry" red
        return 1
    fi
    return 0
}

# Resolve ports from .env or defaults
if [[ $BACKEND_PORT -eq 0 ]]; then
    BACKEND_PORT=$(get_env_value "PORT" "8000")
fi
if [[ $FRONTEND_PORT -eq 0 ]]; then
    FRONTEND_PORT=$(get_env_value "FRONTEND_PORT" "3000")
fi

# Banner
echo ""
echo -e "\033[0;36m  ============================================\033[0m"
echo -e "\033[0;36m   EMBODIER TRADER  v4.0.0\033[0m"
echo -e "\033[0;36m   Backend :$BACKEND_PORT  |  Frontend :$FRONTEND_PORT\033[0m"
echo -e "\033[0;36m  ============================================\033[0m"
echo ""

# Pre-flight checks
if ! test_prerequisites; then
    echo ""
    echo -e "\033[0;33m  Press Enter to exit...\033[0m"
    read -r
    exit 1
fi

# Validate/create .env file
if [[ ! -f "$ENV_FILE" ]]; then
    local env_example="$BACKEND_DIR/.env.example"
    if [[ -f "$env_example" ]]; then
        cp "$env_example" "$ENV_FILE"
        log "Created .env from .env.example - EDIT backend/.env with your API keys!" yellow
    fi
fi

# Validate Alpaca keys
if [[ -f "$ENV_FILE" ]]; then
    local alpaca_key=$(get_env_value "ALPACA_API_KEY" "")
    if [[ -z "$alpaca_key" ]] || [[ "$alpaca_key" =~ ^your- ]]; then
        log "WARNING: ALPACA_API_KEY is not set or still a placeholder!" yellow
        log "Edit $ENV_FILE with your real Alpaca API keys." yellow
        log "Backend will start but market data will be unavailable." yellow
    fi
fi

# Kill processes on ports
kill_port_processes() {
    local port="$1"

    # Try lsof first (macOS, some Linux)
    if command -v lsof &> /dev/null; then
        local pids=$(lsof -ti ":$port" 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            for pid in $pids; do
                local proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
                log "Killing PID $pid ($proc_name) on port $port" yellow
                kill -9 "$pid" 2>/dev/null || true
            done
        fi
    # Fallback to fuser (Linux)
    elif command -v fuser &> /dev/null; then
        local pids=$(fuser "$port/tcp" 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            for pid in $pids; do
                local proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
                log "Killing PID $pid ($proc_name) on port $port" yellow
                kill -9 "$pid" 2>/dev/null || true
            done
        fi
    fi
}

log "Checking for stale processes..." cyan
kill_port_processes "$BACKEND_PORT"
kill_port_processes "$FRONTEND_PORT"

# DuckDB lock file cleanup
DUCKDB_FILE="$BACKEND_DIR/data/analytics.duckdb"
DUCKDB_WAL="$DUCKDB_FILE.wal"
DUCKDB_TMP="$DUCKDB_FILE.tmp"

for lock_file in "$DUCKDB_WAL" "$DUCKDB_TMP"; do
    if [[ -f "$lock_file" ]]; then
        rm -f "$lock_file" 2>/dev/null || true
        log "Removed stale lock: $(basename "$lock_file")" yellow
    fi
done

sleep 1

# Ensure Python venv exists
cd "$BACKEND_DIR"
if [[ ! -d "venv" ]]; then
    log "Creating Python virtual environment..." cyan
    python3 -m venv venv
    if [[ $? -ne 0 ]]; then
        log "Failed to create venv. Is Python 3.10+ installed?" red
        log "Download from https://python.org/downloads" yellow
        exit 1
    fi
fi

# Use venv python directly
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"
VENV_PIP="$BACKEND_DIR/venv/bin/pip"

if [[ ! -f "$VENV_PYTHON" ]]; then
    log "venv/bin/python not found - recreating venv..." yellow
    rm -rf venv
    python3 -m venv venv
fi

# Check if FastAPI is installed
need_install=0
if ! "$VENV_PYTHON" -c "import fastapi" 2>/dev/null; then
    need_install=1
fi

if [[ $need_install -eq 1 ]]; then
    log "Installing Python dependencies..." cyan
    "$VENV_PIP" install -r requirements.txt --quiet
    if [[ $? -ne 0 ]]; then
        log "pip install failed - trying with verbose output:" red
        "$VENV_PIP" install -r requirements.txt 2>&1 | tail -20
        exit 1
    fi
    log "Python dependencies installed" green
fi

# Start backend as background process
BACKEND_LOG="$LOG_DIR/backend.log"
BACKEND_ERR="$LOG_DIR/backend-error.log"

# Clear log files
> "$BACKEND_LOG"
> "$BACKEND_ERR"

# Set UTF-8 environment
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# Start backend in background
"$VENV_PYTHON" -u start_server.py > "$BACKEND_LOG" 2> "$BACKEND_ERR" &
BACKEND_PID=$!

if [[ -z "$BACKEND_PID" ]]; then
    log "Failed to start backend process" red
    exit 1
fi

log "Backend PID: $BACKEND_PID" gray

# Cleanup function for Ctrl+C
cleanup() {
    echo ""
    log "Shutting down..." yellow

    # Kill backend
    if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi

    # Kill frontend
    if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi

    # Kill by port (more reliable)
    kill_port_processes "$BACKEND_PORT"
    kill_port_processes "$FRONTEND_PORT"

    # Clean DuckDB locks
    for lock_file in "$DUCKDB_WAL" "$DUCKDB_TMP"; do
        [[ -f "$lock_file" ]] && rm -f "$lock_file" 2>/dev/null || true
    done

    log "Stopped." green
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for backend liveness (90s timeout)
log "Waiting for backend..." cyan
healthy=0
tcp_up=0

for i in $(seq 1 90); do
    sleep 1

    # Check if port is open
    if [[ $tcp_up -eq 0 ]]; then
        if nc -z 127.0.0.1 "$BACKEND_PORT" 2>/dev/null || \
           (exec 3<>/dev/tcp/127.0.0.1/"$BACKEND_PORT") 2>/dev/null; then
            tcp_up=1
            log "Port $BACKEND_PORT open" gray
            [[ -n "${BASH_VERSION}" ]] && exec 3>&- 2>/dev/null || true
        fi
    fi

    # HTTP health check
    if [[ $tcp_up -eq 1 ]]; then
        if curl -s -f "http://localhost:$BACKEND_PORT/healthz" > /dev/null 2>&1; then
            healthy=1
            break
        fi
    fi

    echo -n "."
done

echo ""

if [[ $healthy -eq 1 ]]; then
    log "Backend   http://localhost:$BACKEND_PORT" green
    log "API Docs  http://localhost:$BACKEND_PORT/docs" gray
else
    log "Backend failed to become healthy." yellow
    log "--- Last 50 lines of backend.log ---" yellow
    if [[ -f "$BACKEND_LOG" ]]; then
        tail -50 "$BACKEND_LOG" | sed 's/^/  /' || true
    fi
    if [[ -f "$BACKEND_ERR" ]]; then
        log "--- Last 50 lines of backend-error.log ---" yellow
        tail -50 "$BACKEND_ERR" | sed 's/^/  /' || true
    fi
    log "------------------------------------" yellow
fi

# Start frontend (unless skipped)
FRONTEND_PID=""
if [[ $SKIP_FRONTEND -eq 0 ]]; then
    cd "$FRONTEND_DIR"

    if [[ ! -d "node_modules" ]]; then
        log "Installing frontend dependencies..." cyan
        npm install --silent
        if [[ $? -ne 0 ]]; then
            log "npm install failed - trying with verbose output:" red
            npm install 2>&1 | tail -20
        else
            log "Frontend dependencies installed" green
        fi
    fi

    FRONTEND_LOG="$LOG_DIR/frontend.log"
    FRONTEND_ERR="$LOG_DIR/frontend-error.log"

    # Clear logs
    > "$FRONTEND_LOG"
    > "$FRONTEND_ERR"

    export VITE_BACKEND_URL="http://localhost:$BACKEND_PORT"

    # Start frontend in background
    npx vite --port "$FRONTEND_PORT" --host > "$FRONTEND_LOG" 2> "$FRONTEND_ERR" &
    FRONTEND_PID=$!

    sleep 3
    log "Frontend  http://localhost:$FRONTEND_PORT" green

    # Try to open browser (works on most Linux with xdg-open, macOS with open)
    sleep 2
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:$FRONTEND_PORT" 2>/dev/null || true
    elif command -v open &> /dev/null; then
        open "http://localhost:$FRONTEND_PORT" 2>/dev/null || true
    fi
fi

# Running banner
echo ""
echo -e "\033[0;32m  RUNNING  |  Press Ctrl+C to stop\033[0m"
echo -e "\033[0;90m  Backend PID:  $BACKEND_PID\033[0m"
if [[ -n "$FRONTEND_PID" ]]; then
    echo -e "\033[0;90m  Frontend PID: $FRONTEND_PID\033[0m"
fi
echo -e "\033[0;90m  Logs: $LOG_DIR\033[0m"
echo ""

# Monitor loop - check if backend is still alive
consecutive_fails=0
while true; do
    sleep 10

    alive=0
    if curl -s -f "http://localhost:$BACKEND_PORT/healthz" > /dev/null 2>&1; then
        alive=1
        consecutive_fails=0
    fi

    if [[ $alive -eq 0 ]]; then
        consecutive_fails=$((consecutive_fails + 1))
        if [[ $consecutive_fails -ge 3 ]]; then
            log "Backend unresponsive (3 consecutive failures). See logs/backend.log" red
            break
        fi
    fi
done

# Cleanup will be called by trap
cleanup
