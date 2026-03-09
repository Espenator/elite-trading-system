# Scripts Directory

This directory contains utility scripts for validating and verifying the Elite Trading System startup process.

## Preflight Validation (`preflight.py`)

**Purpose:** Validate environment before starting the system

**Usage:**
```bash
python scripts/preflight.py
```

**Checks:**
- ✓ Python 3.10+ installed
- ✓ Required Python packages (fastapi, uvicorn, duckdb, etc.)
- ✓ Node.js 18+ installed
- ✓ .env file exists in backend/
- ✓ DuckDB directory writable
- ✓ Ports 8000, 3000, 50051 available
- ⚠️ Required environment variables (Alpaca keys)
- ⚠️ Optional environment variables (Unusual Whales, Finviz, etc.)

**Exit codes:**
- 0: All checks passed
- 1: Critical failure (missing required dependency)

**When to use:**
- Before first startup
- After updating dependencies
- When troubleshooting startup issues
- In CI/CD pipelines

---

## Startup Verification (`verify-startup.py`)

**Purpose:** Verify that all critical backend endpoints are responding correctly

**Usage:**
```bash
# After starting the system
python scripts/verify-startup.py

# Test a different URL
python scripts/verify-startup.py --url http://localhost:8001

# Wait 10 seconds before checking
python scripts/verify-startup.py --wait 10
```

**Checks:**
- ✓ Liveness probe (/healthz)
- ✓ Readiness probe (/readyz)
- ✓ Health diagnostics (/health)
- ✓ Status API (/api/v1/status)
- ✓ Council status (/api/v1/council/status)
- ✓ API documentation (/docs)

**Exit codes:**
- 0: All checks passed
- 1: One or more checks failed

**When to use:**
- After starting the system
- In automated deployment pipelines
- When debugging API issues
- In Docker health checks

---

## Workflow

**Recommended startup workflow:**

```bash
# 1. Validate environment
python scripts/preflight.py

# 2. Start system (Windows)
.\start-embodier.ps1

# 3. Verify startup (after ~10 seconds)
python scripts/verify-startup.py
```

**Docker workflow:**

```bash
# 1. Validate environment
python scripts/preflight.py

# 2. Start with Docker
docker-compose up -d

# 3. Wait for startup and verify
python scripts/verify-startup.py --wait 30
```

---

## System Diagnostics (`doctor.py`)

**Purpose:** Comprehensive system health diagnostics CLI tool

**Usage:**
```bash
# Full diagnostic
python scripts/doctor.py

# Quick check (critical checks only)
python scripts/doctor.py --quick

# Export report to JSON
python scripts/doctor.py --export diagnostic-report.json
```

**Checks:**

### Environment (6 checks)
- ✓ Python 3.10+ installed
- ✓ Node.js 18+ installed
- ✓ Required Python packages
- ⚠ .env file exists
- ⚠ Alpaca API keys configured
- ✓ Optional API keys

### Infrastructure (3 checks)
- ✓ Port 8000, 3000, 50051 availability
- ✓ Database directory exists and writable
- ✓ Disk space (>20% free)

### Backend Services (3 checks)
- ✓ Backend liveness (/healthz)
- ✓ WebSocket health
- ✓ Brain service connectivity

**Exit codes:**
- 0: All checks passed
- 1: Critical failures
- 2: Warnings only (degraded mode)

**When to use:**
- After installation
- Before reporting bugs
- When troubleshooting issues
- In CI/CD pipelines
- For support ticket diagnostics

---

## Future Scripts (Planned)
- `check-env.py` — Deep validation of .env configuration
- `benchmark-startup.py` — Measure startup time and identify bottlenecks
- `smoke-test.py` — End-to-end smoke test of critical flows
