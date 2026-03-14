#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "[Embodier] Starting backend on port 8001..."
cd "$ROOT/backend"
python run_server.py &
BACKEND_PID=$!

echo "[Embodier] Waiting for backend..."
for i in $(seq 1 30); do
  if curl -s http://localhost:8001/api/v1/system/health-check > /dev/null 2>&1; then
    echo "[Embodier] Backend ready!"
    break
  fi
  sleep 2
done

echo "[Embodier] Starting frontend on port 5173..."
cd "$ROOT/frontend-v2"
npm run dev &
FRONTEND_PID=$!

sleep 5
echo "[Embodier] Opening browser..."
open http://localhost:5173/dashboard 2>/dev/null || xdg-open http://localhost:5173/dashboard 2>/dev/null || true

echo ""
echo "======================================"
echo " Embodier Trader is running!"
echo " Frontend: http://localhost:5173"
echo " Backend:  http://localhost:8001"
echo "======================================"
echo " Press Ctrl+C to stop..."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
