#!/usr/bin/env bash

# Elite Trading System - Linux/Unix Launcher
# Equivalent to start-embodier.ps1 for Windows

set -e

# Default values
SKIP_FRONTEND=false
BACKEND_PORT=0
FRONTEND_PORT=0
MAX_RESTARTS=3

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-frontend)
      SKIP_FRONTEND=true
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
      echo "  --skip-frontend      Skip starting the frontend (backend only)"
      echo "  --backend-port PORT  Backend port (default: from .env PORT or 8000)"
      echo "  --frontend-port PORT Frontend port (default: from .env FRONTEND_PORT or 3000)"
      echo "  --max-restarts N     Maximum restart attempts (default: 3)"
      echo "  -h, --help           Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend-v2"
LOG_DIR="$SCRIPT_DIR/logs"
ENV_FILE="$BACKEND_DIR/.env"

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

# Timestamped log helper
log() {
  local msg="$1"
  local color="${2:-}"
  local ts
  ts=$(date +"%H:%M:%S")

  case "$color" in
    red)     echo -e "  [\033[31m$ts\033[0m] \033[31m$msg\033[0m" ;;
    green)   echo -e "  [\033[32m$ts\033[0m] \033[32m$msg\033[0m" ;;
    yellow)  echo -e "  [\033[33m$ts\033[0m] \033[33m$msg\033[0m" ;;
    cyan)    echo -e "  [\033[36m$ts\033[0m] \033[36m$msg\033[0m" ;;
    gray)    echo -e "  [\033[90m$ts\033[0m] \033[90m$msg\033[0m" ;;
    *)       echo "  [$ts] $msg" ;;
  esac
}

# Read value from .env file
get_env_value() {
  local key="$1"
  local default="$2"

  if [[ -f "$ENV_FILE" ]]; then
    local value
    value=$(grep "^$key=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '\r\n' | xargs)
    if [[ -n "$value" ]]; then
      echo "$value"
      return
    fi
  fi
  echo "$default"
}

# Pre-flight check: validate Python and Node.js
test_prerequisites() {
  local ok=true

  # Check Python
  if command -v python3 &> /dev/null; then
    local py_version
    py_version=$(python3 --version 2>&1 | awk '{print $2}')
    local py_major py_minor
    py_major=$(echo "$py_version" | cut -d. -f1)
    py_minor=$(echo "$py_version" | cut -d. -f2)

    if [[ $py_major -lt 3 ]] || [[ $py_major -eq 3 && $py_minor -lt 10 ]]; then
      log "Python $py_version found but 3.10+ required" red
      ok=false
    else
      log "Python $py_version" green
    fi
  else
    log "Python3 not found. Install Python 3.10+ from https://python.org/downloads" red
    ok=false
  fi

  # Check Node.js (unless frontend is skipped)
  if [[ "$SKIP_FRONTEND" == false ]]; then
    if command -v node &> /dev/null; then
      local node_version
      node_version=$(node --version 2>&1 | sed 's/v//')
      local node_major
      node_major=$(echo "$node_version" | cut -d. -f1)

      if [[ $node_major -lt 18 ]]; then
        log "Node.js v$node_version found but v18+ required" red
        ok=false
      else
        log "Node.js v$node_version" green
      fi
    else
      log "Node.js not found. Install Node.js 18+ from https://nodejs.org" red
      ok=false
    fi
  fi

  if [[ "$ok" == false ]]; then
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
echo -e "  \033[36m============================================\033[0m"
echo -e "  \033[36m EMBODIER TRADER  v4.0.0\033[0m"
echo -e "  \033[36m Backend :$BACKEND_PORT  |  Frontend :$FRONTEND_PORT\033[0m"
echo -e "  \033[36m============================================\033[0m"
echo ""

# Pre-flight checks
if ! test_prerequisites; then
  echo ""
  echo -e "  \033[33mPress Enter to exit...\033[0m"
  read -r
  exit 1
fi

# Create .env from .env.example if it doesn't exist
if [[ ! -f "$ENV_FILE" ]]; then
  local env_example="$BACKEND_DIR/.env.example"
  if [[ -f "$env_example" ]]; then
    cp "$env_example" "$ENV_FILE"
    log "Created .env from .env.example - EDIT backend/.env with your API keys!" yellow
  fi
else
  log ".env found" gray
fi

# Validate .env has real Alpaca keys (not placeholders)
if [[ -f "$ENV_FILE" ]]; then
  local alpaca_key
  alpaca_key=$(get_env_value "ALPACA_API_KEY" "")
  if [[ -z "$alpaca_key" ]] || [[ "$alpaca_key" =~ ^your- ]]; then
    log "WARNING: ALPACA_API_KEY is not set or still a placeholder!" yellow
    log "Edit $ENV_FILE with your real Alpaca API keys." yellow
    log "Backend will start but market data will be unavailable." yellow
  fi
fi

# Kill processes on specific ports
kill_port_processes() {
  local port="$1"

  # Try lsof first (more reliable)
  if command -v lsof &> /dev/null; then
    local pids
    pids=$(lsof -ti ":$port" 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
      for pid in $pids; do
        local proc_name
        proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        log "Killing PID $pid ($proc_name) on port $port" yellow
        kill -9 "$pid" 2>/dev/null || true
      done
    fi
  # Fallback to fuser if lsof not available
  elif command -v fuser &> /dev/null; then
    fuser -k -n tcp "$port" 2>/dev/null || true
  fi
}

log "Checking for stale processes..." cyan
kill_port_processes "$BACKEND_PORT"
kill_port_processes "$FRONTEND_PORT"

# DuckDB lock file cleanup
DUCKDB_FILE="$BACKEND_DIR/data/analytics.duckdb"
DUCKDB_WAL="$DUCKDB_FILE.wal"
DUCKDB_TMP="$DUCKDB_FILE.tmp"

if [[ -f "$DUCKDB_WAL" ]]; then
  rm -f "$DUCKDB_WAL" 2>/dev/null || true
  log "Removed stale lock: analytics.duckdb.wal" yellow
fi
if [[ -f "$DUCKDB_TMP" ]]; then
  rm -f "$DUCKDB_TMP" 2>/dev/null || true
  log "Removed stale lock: analytics.duckdb.tmp" yellow
fi

sleep 1

# Ensure Python virtual environment exists
cd "$BACKEND_DIR"

if [[ ! -d "venv" ]]; then
  log "Creating Python virtual environment..." cyan
  python3 -m venv venv
  if [[ $? -ne 0 ]]; then
    log "Failed to create venv. Is Python 3.10+ installed?" red
    exit 1
  fi
fi

# Activate venv and get python/pip paths
VENV_PYTHON="$BACKEND_DIR/venv/bin/python"
VENV_PIP="$BACKEND_DIR/venv/bin/pip"

if [[ ! -f "$VENV_PYTHON" ]]; then
  log "venv/bin/python not found - recreating venv..." yellow
  rm -rf venv
  python3 -m venv venv
fi

# Check if fastapi is installed
NEED_INSTALL=false
if ! "$VENV_PYTHON" -c "import fastapi" &>/dev/null; then
  NEED_INSTALL=true
fi

if [[ "$NEED_INSTALL" == true ]]; then
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
BACKEND_LOG_FILE="$LOG_DIR/backend.log"
BACKEND_ERR_FILE="$LOG_DIR/backend-error.log"

# Clear log files
> "$BACKEND_LOG_FILE"
> "$BACKEND_ERR_FILE"

# Start backend with UTF-8 encoding
log "Starting backend..." cyan
"$VENV_PYTHON" -u start_server.py > "$BACKEND_LOG_FILE" 2> "$BACKEND_ERR_FILE" &
BACKEND_PID=$!

if [[ -z "$BACKEND_PID" ]]; then
  log "Failed to start backend process" red
  exit 1
fi
log "Backend PID: $BACKEND_PID" gray

# Wait for backend to become healthy (90s timeout)
log "Waiting for backend..." cyan
HEALTHY=false
TCP_UP=false

for i in $(seq 1 90); do
  sleep 1

  # Check if process is still running
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    log "Backend process died unexpectedly" red
    break
  fi

  # Check TCP port first
  if [[ "$TCP_UP" == false ]]; then
    if command -v nc &> /dev/null; then
      if nc -z 127.0.0.1 "$BACKEND_PORT" 2>/dev/null; then
        TCP_UP=true
        log "Port $BACKEND_PORT open" gray
      fi
    elif command -v timeout &> /dev/null; then
      if timeout 1 bash -c "cat < /dev/null > /dev/tcp/127.0.0.1/$BACKEND_PORT" 2>/dev/null; then
        TCP_UP=true
        log "Port $BACKEND_PORT open" gray
      fi
    fi
  fi

  # Check HTTP health endpoint
  if [[ "$TCP_UP" == true ]]; then
    if command -v curl &> /dev/null; then
      if curl -sf "http://localhost:$BACKEND_PORT/healthz" >/dev/null 2>&1; then
        HEALTHY=true
        break
      fi
    elif command -v wget &> /dev/null; then
      if wget -q -O /dev/null "http://localhost:$BACKEND_PORT/healthz" 2>/dev/null; then
        HEALTHY=true
        break
      fi
    fi
  fi

  printf "."
done
echo ""

if [[ "$HEALTHY" == true ]]; then
  log "Backend   http://localhost:$BACKEND_PORT" green
  log "API Docs  http://localhost:$BACKEND_PORT/docs" gray
else
  log "Backend failed to become healthy." yellow
  log "--- Last 50 lines of backend.log ---" yellow
  if [[ -f "$BACKEND_LOG_FILE" ]]; then
    tail -50 "$BACKEND_LOG_FILE" | while IFS= read -r line; do
      echo -e "  \033[90m$line\033[0m"
    done
  fi
  if [[ -f "$BACKEND_ERR_FILE" ]]; then
    log "--- Last 50 lines of backend-error.log ---" yellow
    tail -50 "$BACKEND_ERR_FILE" | while IFS= read -r line; do
      echo -e "  \033[90m$line\033[0m"
    done
  fi
  log "------------------------------------" yellow
fi

# Start frontend (unless skipped)
FRONTEND_PID=""
if [[ "$SKIP_FRONTEND" == false ]]; then
  cd "$FRONTEND_DIR"

  if [[ ! -d "node_modules" ]]; then
    log "Installing frontend dependencies..." cyan
    npm install --quiet
    if [[ $? -ne 0 ]]; then
      log "npm install failed - trying with verbose output:" red
      npm install 2>&1 | tail -20
    else
      log "Frontend dependencies installed" green
    fi
  fi

  FRONTEND_LOG_FILE="$LOG_DIR/frontend.log"
  FRONTEND_ERR_FILE="$LOG_DIR/frontend-error.log"

  # Clear frontend logs
  > "$FRONTEND_LOG_FILE"
  > "$FRONTEND_ERR_FILE"

  # Set environment variable for Vite
  export VITE_BACKEND_URL="http://localhost:$BACKEND_PORT"

  # Start frontend
  log "Starting frontend..." cyan
  npx vite --port "$FRONTEND_PORT" --host > "$FRONTEND_LOG_FILE" 2> "$FRONTEND_ERR_FILE" &
  FRONTEND_PID=$!

  sleep 3
  log "Frontend  http://localhost:$FRONTEND_PORT" green

  # Try to open browser if in desktop environment
  sleep 2
  if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:$FRONTEND_PORT" 2>/dev/null || true
  elif command -v open &> /dev/null; then
    open "http://localhost:$FRONTEND_PORT" 2>/dev/null || true
  fi
fi

# Running banner
echo ""
echo -e "  \033[32mRUNNING  |  Press Ctrl+C to stop\033[0m"
echo -e "  \033[90mBackend PID:  $BACKEND_PID\033[0m"
if [[ -n "$FRONTEND_PID" ]]; then
  echo -e "  \033[90mFrontend PID: $FRONTEND_PID\033[0m"
fi
echo -e "  \033[90mLogs: $LOG_DIR\033[0m"
echo ""

# Cleanup function for graceful shutdown
cleanup() {
  echo ""
  log "Shutting down..." yellow

  # Kill backend
  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  kill_port_processes "$BACKEND_PORT"

  # Kill frontend
  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  kill_port_processes "$FRONTEND_PORT"

  # Remove DuckDB lock files
  rm -f "$DUCKDB_WAL" "$DUCKDB_TMP" 2>/dev/null || true

  log "Stopped." green
  exit 0
}

# Trap Ctrl+C and other termination signals
trap cleanup INT TERM EXIT

# Monitor loop - check if backend is still healthy
CONSECUTIVE_FAILS=0
while true; do
  sleep 10

  # Check if backend process is still running
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    log "Backend process terminated" red
    break
  fi

  # Check HTTP health
  ALIVE=false
  if command -v curl &> /dev/null; then
    if curl -sf "http://localhost:$BACKEND_PORT/healthz" >/dev/null 2>&1; then
      ALIVE=true
      CONSECUTIVE_FAILS=0
    fi
  elif command -v wget &> /dev/null; then
    if wget -q -O /dev/null "http://localhost:$BACKEND_PORT/healthz" 2>/dev/null; then
      ALIVE=true
      CONSECUTIVE_FAILS=0
    fi
  fi

  if [[ "$ALIVE" == false ]]; then
    CONSECUTIVE_FAILS=$((CONSECUTIVE_FAILS + 1))
    if [[ $CONSECUTIVE_FAILS -ge 3 ]]; then
      log "Backend unresponsive (3 consecutive failures). See logs/backend.log" red
      break
    fi
  fi
done

# If we exit the loop, cleanup will be called automatically via trap
