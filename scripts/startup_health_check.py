#!/usr/bin/env python3
"""
Full System Startup & Health Check — 7 phases.

Runs: environment check → backend startup → router verification →
      API smoke tests → signal pipeline → frontend wiring → background loops.
Writes reports/STARTUP-HEALTH-REPORT.md when done.

Usage (from repo root):
  python scripts/startup_health_check.py [--base-url http://localhost:8000] [--no-write]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import urllib.request
    import urllib.error
except ImportError:
    urllib = None  # type: ignore

# Base URL for backend (override with --base-url)
DEFAULT_BASE = os.environ.get("EMBODIER_BACKEND_URL", "http://localhost:8000")
REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "reports" / "STARTUP-HEALTH-REPORT.md"

# ---------------------------------------------------------------------------
# Common failure patterns (included in report and view)
# ---------------------------------------------------------------------------
FAILURE_PATTERNS = [
    {
        "symptom": "Backend /healthz timeouts or connection refused",
        "cause": "Backend not running, wrong port, or firewall",
        "remediation": "Start backend: cd backend && venv\\Scripts\\Activate.ps1 && uvicorn app.main:app --host 0.0.0.0 --port 8000",
    },
    {
        "symptom": "DuckDB check fails in /readyz or /api/v1/health",
        "cause": "DuckDB file locked, missing data dir, or schema not initialized",
        "remediation": "Ensure backend/data/ exists; restart backend; check no other process holds DuckDB.",
    },
    {
        "symptom": "Alpaca configured but connectivity error",
        "cause": "Invalid API keys, network block, or Alpaca API outage",
        "remediation": "Verify ALPACA_API_KEY and ALPACA_SECRET_KEY in backend/.env; use paper base URL for paper trading.",
    },
    {
        "symptom": "MessageBus or council_gate not_started in /health",
        "cause": "Lifespan startup failed or deferred services not yet started",
        "remediation": "Check backend logs for lifespan errors; increase DEFERRED_STARTUP_DELAY if heavy init fails.",
    },
    {
        "symptom": "Frontend loads but API calls 404 or CORS errors",
        "cause": "Wrong VITE_API_URL, backend not on expected port, or CORS origin not allowed",
        "remediation": "Set VITE_API_URL to backend URL (e.g. http://localhost:8000); ensure backend CORS includes frontend origin.",
    },
    {
        "symptom": "Brain gRPC or Ollama unavailable",
        "cause": "Brain service not running on PC2, or Ollama not running",
        "remediation": "Start brain_service on ProfitTrader; or set LLM_ENABLED=false to run without LLM.",
    },
    {
        "symptom": "Redis unavailable (when REDIS_URL set)",
        "cause": "Redis not running or wrong host/port",
        "remediation": "Start Redis or set REDIS_REQUIRED=false to allow local-only MessageBus.",
    },
    {
        "symptom": "Scouts or discovery agents crash repeatedly",
        "cause": "Missing API keys (UW, Finviz, etc.) or rate limits",
        "remediation": "Check SCOUTS_ENABLED and optional env vars; see logs for specific scout exceptions.",
    },
]


def _http_get(base: str, path: str, timeout: float = 10) -> tuple[int, str | None, dict | list | None]:
    """GET url and return (status_code, error_message, json_body)."""
    url = f"{base.rstrip('/')}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = None
            return (resp.status, None, body)
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace")) if e.fp else None
        except Exception:
            body = None
        return (e.code, str(e)[:200], body)
    except Exception as e:
        return (-1, str(e)[:200], None)


def phase1_environment(base: str, record: list) -> bool:
    """Phase 1: Environment check — Python, .env, key vars."""
    _ = base
    ok = True
    # Python
    v = sys.version_info
    py_ok = (v.major, v.minor) >= (3, 10)
    record.append({"check": "Python 3.10+", "status": "ok" if py_ok else "fail", "detail": f"{v.major}.{v.minor}"})
    if not py_ok:
        ok = False
    # .env
    env_path = REPO_ROOT / "backend" / ".env"
    env_exists = env_path.is_file()
    record.append({"check": "backend/.env exists", "status": "ok" if env_exists else "warn", "detail": str(env_path)})
    if not env_exists:
        ok = False
    # Alpaca keys (optional but recommended)
    alpaca_key = os.environ.get("ALPACA_API_KEY") or (env_path.read_text().split("ALPACA_API_KEY=")[-1].split("\n")[0].strip() if env_exists else "")
    alpaca_set = bool(alpaca_key and alpaca_key != "" and "your" not in alpaca_key.lower())
    record.append({"check": "Alpaca API key set", "status": "ok" if alpaca_set else "warn", "detail": "configured" if alpaca_set else "missing"})
    return ok


def phase2_backend_startup(base: str, record: list) -> bool:
    """Phase 2: Backend startup — /healthz."""
    status, err, body = _http_get(base, "/healthz", timeout=5)
    ok = status == 200
    record.append({
        "check": "Backend /healthz",
        "status": "ok" if ok else "fail",
        "detail": body.get("status", body) if isinstance(body, dict) else (err or f"HTTP {status}"),
    })
    return ok


def phase3_router_verification(base: str, record: list) -> bool:
    """Phase 3: Router verification — OpenAPI or key routes."""
    status, err, body = _http_get(base, "/openapi.json", timeout=8)
    if status != 200 or not isinstance(body, dict):
        record.append({"check": "OpenAPI /openapi.json", "status": "fail", "detail": err or f"HTTP {status}"})
        return False
    paths = list((body.get("paths") or {}).keys())
    record.append({
        "check": "Router verification",
        "status": "ok",
        "detail": f"{len(paths)} routes registered",
    })
    return True


def phase4_api_smoke(base: str, record: list) -> bool:
    """Phase 4: API smoke tests — health, status, signals."""
    ok = True
    for path, name in [
        ("/api/v1/health", "GET /api/v1/health"),
        ("/api/v1/status", "GET /api/v1/status"),
        ("/api/v1/signals/", "GET /api/v1/signals/"),
    ]:
        status, err, body = _http_get(base, path, timeout=6)
        if status != 200:
            record.append({"check": name, "status": "fail", "detail": err or f"HTTP {status}"})
            ok = False
        else:
            record.append({"check": name, "status": "ok", "detail": "200"})
    return ok


def phase5_signal_pipeline(base: str, record: list) -> bool:
    """Phase 5: Signal pipeline — MessageBus, council, signal engine from /api/v1/health."""
    status, err, body = _http_get(base, "/api/v1/health", timeout=8)
    if status != 200 or not isinstance(body, dict):
        record.append({"check": "Signal pipeline (health)", "status": "fail", "detail": err or "health endpoint failed"})
        return False
    msg_bus = body.get("message_bus") or {}
    council = body.get("council") or {}
    mb_ok = msg_bus.get("queue_depth") is not None or msg_bus.get("running") is not None
    # Pipeline is "ok" if council block is present (wired); no eval yet is fine after fresh start
    has_eval = council.get("last_eval_timestamp") is not None or council.get("last_eval_iso") is not None
    wired_no_error = council.get("error") is None and isinstance(council, dict)
    council_ok = has_eval or wired_no_error
    record.append({
        "check": "MessageBus",
        "status": "ok" if mb_ok else "warn",
        "detail": str(msg_bus)[:80],
    })
    record.append({
        "check": "Council (last eval)",
        "status": "ok" if council_ok else "warn",
        "detail": council.get("last_eval_iso") or str(council)[:60],
    })
    return mb_ok and council_ok


def phase6_frontend_wiring(base: str, record: list, frontend_url: str | None) -> bool:
    """Phase 6: Frontend wiring — optional GET to frontend."""
    if not frontend_url:
        record.append({"check": "Frontend URL", "status": "skip", "detail": "no URL provided"})
        return True
    status, err, _ = _http_get(frontend_url.rstrip("/"), "/", timeout=5)
    ok = status == 200
    record.append({
        "check": "Frontend reachable",
        "status": "ok" if ok else "warn",
        "detail": f"HTTP {status}" if status > 0 else (err or "unreachable"),
    })
    return ok


def phase7_background_loops(base: str, record: list) -> bool:
    """Phase 7: Background loops — /readyz and /api/v1/status."""
    status, err, body = _http_get(base, "/readyz", timeout=6)
    if status != 200:
        record.append({"check": "Readiness /readyz", "status": "fail", "detail": err or f"HTTP {status}"})
        return False
    checks = (body or {}).get("checks", {}) if isinstance(body, dict) else {}
    record.append({
        "check": "Readiness checks",
        "status": "ok",
        "detail": ", ".join(f"{k}={v}" for k, v in list(checks.items())[:6]),
    })
    status2, _, body2 = _http_get(base, "/api/v1/status", timeout=5)
    if status2 == 200 and isinstance(body2, dict):
        record.append({
            "check": "Background / status",
            "status": "ok",
            "detail": f"healthy={body2.get('healthy')}, activeAgents={body2.get('activeAgents', '?')}",
        })
    return True


def run_all_phases(base: str, frontend_url: str | None) -> dict:
    """Run all 7 phases and return structured result."""
    phases = [
        ("1_environment", "Environment check", phase1_environment),
        ("2_backend_startup", "Backend startup", phase2_backend_startup),
        ("3_router_verification", "Router verification", phase3_router_verification),
        ("4_api_smoke", "API smoke tests", phase4_api_smoke),
        ("5_signal_pipeline", "Signal pipeline", phase5_signal_pipeline),
        ("6_frontend_wiring", "Frontend wiring", phase6_frontend_wiring),
        ("7_background_loops", "Background loops", phase7_background_loops),
    ]
    results = {}
    overall_ok = True
    for key, label, fn in phases:
        record = []
        if key == "6_frontend_wiring":
            ok = fn(base, record, frontend_url)
        elif key == "2_backend_startup":
            ok = fn(base, record)
            if not ok:
                # Skip HTTP-dependent phases if backend is down
                for k, l, f in phases[2:]:
                    results[k] = {"label": l, "ok": False, "checks": [{"check": "(skipped)", "status": "skip", "detail": "backend not reachable"}]}
                results[key] = {"label": "Backend startup", "ok": False, "checks": record}
                return {"phases": results, "overall_ok": False, "failure_patterns": FAILURE_PATTERNS}
        else:
            ok = fn(base, record)
        results[key] = {"label": label, "ok": ok, "checks": record}
        if not ok:
            overall_ok = False
    return {"phases": results, "overall_ok": overall_ok, "failure_patterns": FAILURE_PATTERNS}


def render_markdown_report(data: dict, base: str) -> str:
    """Generate STARTUP-HEALTH-REPORT.md content."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Full System Startup & Health Report",
        "",
        "```",
        "═══════════════════════════════════════════════════════",
        "  EMBODIER TRADER — STARTUP HEALTH",
        f"  Date: {ts}",
        f"  Backend: {base}",
        "═══════════════════════════════════════════════════════",
        "```",
        "",
    ]
    overall = "✅ PASS" if data.get("overall_ok") else "❌ FAIL"
    lines.append(f"## Overall: {overall}")
    lines.append("")
    lines.append("## 7 Phases")
    lines.append("")
    for key, phase in (data.get("phases") or {}).items():
        label = phase.get("label", key)
        ok = phase.get("ok", False)
        icon = "✅" if ok else "❌"
        lines.append(f"### {icon} Phase {key.split('_')[0]}: {label}")
        lines.append("")
        for c in phase.get("checks", []):
            s = c.get("status", "?")
            d = c.get("detail", "")
            lines.append(f"- **{c.get('check', '?')}**: {s} — {d}")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Common Failure Patterns")
    lines.append("")
    lines.append("| Symptom | Cause | Remediation |")
    lines.append("|---------|--------|-------------|")
    for row in data.get("failure_patterns") or []:
        sym = (row.get("symptom") or "").replace("|", "\\|")
        cause = (row.get("cause") or "").replace("|", "\\|")
        rem = (row.get("remediation") or "").replace("|", "\\|")
        lines.append(f"| {sym} | {cause} | {rem} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Generated by `scripts/startup_health_check.py`. View in UI: System → Startup Health.*")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Full system startup health check (7 phases)")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="Backend base URL")
    parser.add_argument("--frontend-url", default=os.environ.get("EMBODIER_FRONTEND_URL", "http://localhost:5173"), help="Frontend URL for phase 6")
    parser.add_argument("--no-write", action="store_true", help="Do not write STARTUP-HEALTH-REPORT.md")
    args = parser.parse_args()
    if not urllib:
        print("ERROR: urllib not available", file=sys.stderr)
        return 1
    data = run_all_phases(args.base_url, args.frontend_url or None)
    report_path = REPORT_PATH
    if not args.no_write:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_markdown_report(data, args.base_url), encoding="utf-8")
        print(f"Report written: {report_path}")
    # Print summary
    print("\n" + "=" * 60)
    print("  STARTUP HEALTH — 7 PHASES")
    print("=" * 60)
    for key, phase in data.get("phases", {}).items():
        icon = "OK " if phase.get("ok") else "FAIL"
        print(f"  [{icon}] {phase.get('label', key)}")
    print("-" * 60)
    print(f"  Overall: {'PASS' if data.get('overall_ok') else 'FAIL'}")
    print("=" * 60 + "\n")
    return 0 if data.get("overall_ok") else 1


if __name__ == "__main__":
    sys.exit(main())
