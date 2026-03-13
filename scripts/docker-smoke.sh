#!/usr/bin/env bash
# Run after: docker-compose up -d
# Waits for backend health then runs smoke checks.
set -e
BASE="${1:-http://localhost:8000}"
echo "=== Docker smoke test: $BASE ==="
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf "$BASE/healthz" >/dev/null 2>&1; then
    echo "  Backend up after ${i}0s"
    break
  fi
  if [ "$i" -eq 10 ]; then
    echo "  FAIL: Backend not ready"
    exit 1
  fi
  sleep 10
done
curl -sf "$BASE/health" >/dev/null && echo "  OK /health"
curl -sf "$BASE/api/v1/health" >/dev/null && echo "  OK /api/v1/health"
curl -sf "$BASE/api/v1/council/latest" >/dev/null && echo "  OK /api/v1/council/latest"
echo "  All smoke checks passed."
