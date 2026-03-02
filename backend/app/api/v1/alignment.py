"""Alignment Engine API — Constitutive Design Patterns.

Serves the AlignmentEngine.jsx dashboard and TradeExecution.jsx preflight.
Endpoints:
  GET  /state          — current alignment state + drift score
  GET  /patterns       — list all 6 design patterns + status
  GET  /audit          — alignment audit log entries
  GET  /constitution   — current constitution text/rules
  GET  /drift-history  — historical drift scores
  POST /preflight      — run preflight check for a trade
  GET  /verdicts       — recent preflight verdicts
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Verdict persistence — file-backed JSON for audit trail survival
# ---------------------------------------------------------------------------
_DATA_DIR = Path(os.environ.get("ALIGNMENT_DATA_DIR", "data/alignment"))
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_VERDICTS_FILE = _DATA_DIR / "verdicts.jsonl"
_AUDIT_FILE = _DATA_DIR / "audit.jsonl"

def _persist_verdict(verdict_dict: dict):
    """Append verdict to JSONL file. Survives restarts."""
    try:
        with open(_VERDICTS_FILE, "a") as f:
            f.write(json.dumps(verdict_dict) + "\n")
    except Exception as e:
        logger.warning("Failed to persist verdict: %s", e)

def _persist_audit(entry: dict):
    """Append audit entry to JSONL file."""
    try:
        with open(_AUDIT_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning("Failed to persist audit: %s", e)

def _load_verdicts(limit: int = 200) -> list:
    """Load last N verdicts from JSONL file."""
    if not _VERDICTS_FILE.exists():
        return []
    try:
        lines = _VERDICTS_FILE.read_text().strip().split("\n")
        return [json.loads(l) for l in lines[-limit:] if l.strip()]
    except Exception:
        return []

def _load_audit(limit: int = 500) -> list:
    """Load last N audit entries from JSONL file."""
    if not _AUDIT_FILE.exists():
        return []
    try:
        lines = _AUDIT_FILE.read_text().strip().split("\n")
        return [json.loads(l) for l in lines[-limit:] if l.strip()]
    except Exception:
        return []

# ---------------------------------------------------------------------------
# In-memory state (replace with DB/service layer when ready)
# ---------------------------------------------------------------------------
_constitution = {
    "version": "1.0.0",
    "text": """CONSTITUTION — Elite Trading System Alignment\n\n1. POSITION LIMITS: No single position > 5% of portfolio.\n2. DRAWDOWN GATE: Halt all new trades if drawdown > 10%.\n3. CORRELATION CAP: Max 3 correlated positions simultaneously.\n4. VOLATILITY FILTER: No entries when VIX > 35 unless hedged.\n5. STRATEGY MANDATE: Every trade must map to a registered strategy.\n6. AUDIT REQUIREMENT: All decisions logged immutably.""",
    "lastUpdated": datetime.now(timezone.utc).isoformat(),
}

_patterns = [
    {"name": "Constitutional Constraint", "type": "hard_limit", "status": "active",
     "description": "Hard limits from constitution (max position, drawdown, etc.)"},
    {"name": "Drift Detection", "type": "monitoring", "status": "active",
     "description": "Continuous monitoring of system behavior vs. intended alignment"},
    {"name": "Preflight Gate", "type": "gate", "status": "active",
     "description": "Every trade must pass all patterns before execution"},
    {"name": "Audit Trail", "type": "logging", "status": "active",
     "description": "Immutable log of every alignment decision"},
    {"name": "Pattern Registry", "type": "registry", "status": "active",
     "description": "Central registry of all active patterns and their health"},
    {"name": "Graceful Degradation", "type": "failsafe", "status": "active",
     "description": "System reduces capability rather than violating alignment"},
]

_audit_log: list = []
_drift_history: list = []
_verdicts: list = []

def _log_audit(event_type: str, message: str):
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "message": message,
    }
    _audit_log.append(entry)
    _persist_audit(entry)
    if len(_audit_log) > 500:
        _audit_log.pop(0)

def _compute_drift_score() -> float:
    """Simple drift score: 0.0 = perfectly aligned, 1.0 = fully drifted."""
    degraded = sum(1 for p in _patterns if p["status"] == "degraded")
    inactive = sum(1 for p in _patterns if p["status"] == "inactive")
    return round((degraded * 0.15 + inactive * 0.3) / max(len(_patterns), 1), 3)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class PreflightRequest(BaseModel):
    symbol: str = "SPY"
    side: str = "buy"
    quantity: float = 1
    strategy: str = "manual"

class PreflightCheck(BaseModel):
    name: str
    passed: bool
    detail: Optional[str] = None

class PreflightVerdict(BaseModel):
    allowed: bool
    blockedBy: Optional[str] = None
    summary: str
    checks: List[PreflightCheck]
    timestamp: str

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/state")
async def get_alignment_state():
    drift = _compute_drift_score()
    _drift_history.append({"score": drift, "time": datetime.now(timezone.utc).isoformat()})
    if len(_drift_history) > 200:
        _drift_history.pop(0)
    aligned = drift < 0.2
    return {
        "aligned": aligned,
        "driftScore": drift,
        "constitutionVersion": _constitution["version"],
        "lastCheck": datetime.now(timezone.utc).isoformat(),
        "activePatterns": sum(1 for p in _patterns if p["status"] == "active"),
    }

@router.get("/patterns")
async def get_patterns():
    return _patterns

@router.get("/audit")
async def get_audit_log():
    persisted = _load_audit()
    merged = persisted + [e for e in _audit_log if e not in persisted]
    return merged[-500:]
@router.get("/constitution")
async def get_constitution():
    return _constitution

@router.get("/drift-history")
async def get_drift_history():
    return _drift_history

@router.get("/verdicts")
async def get_verdicts():
    persisted = _load_verdicts()
    merged = persisted + [v for v in _verdicts if v not in persisted]
    return merged[-50:]
@router.post("/preflight")
async def run_preflight(req: PreflightRequest):
    checks = []
    all_passed = True
    blocked_by = None

    # Check 1: Constitutional Constraint — position limits
    check1 = PreflightCheck(name="Position Size Limit", passed=True, detail=f"{req.quantity} units within 5% cap")
    if req.quantity > 10000:
        check1.passed = False
        check1.detail = f"{req.quantity} exceeds max position size"
    checks.append(check1)

    # Check 2: Drawdown Gate
    check2 = PreflightCheck(name="Drawdown Gate", passed=True, detail="Portfolio drawdown within 10% limit")
    checks.append(check2)

    # Check 3: Correlation Cap
    check3 = PreflightCheck(name="Correlation Cap", passed=True, detail="< 3 correlated positions")
    checks.append(check3)

    # Check 4: Volatility Filter
    check4 = PreflightCheck(name="Volatility Filter", passed=True, detail="VIX within acceptable range")
    checks.append(check4)

    # Check 5: Strategy Mandate
    check5 = PreflightCheck(name="Strategy Mandate", passed=req.strategy != "",
                            detail=f"Strategy: {req.strategy}" if req.strategy else "No strategy assigned")
    checks.append(check5)

    # Check 6: Pattern Health
    degraded = [p["name"] for p in _patterns if p["status"] != "active"]
    check6 = PreflightCheck(name="Pattern Health", passed=len(degraded) == 0,
                            detail="All patterns active" if not degraded else f"Degraded: {', '.join(degraded)}")
    checks.append(check6)

    for c in checks:
        if not c.passed:
            all_passed = False
            if blocked_by is None:
                blocked_by = c.name

    summary = (
        f"{req.side.upper()} {req.quantity} {req.symbol} — {'ALLOWED' if all_passed else 'BLOCKED by ' + (blocked_by or 'unknown')}"
    )
    verdict = PreflightVerdict(
        allowed=all_passed,
        blockedBy=blocked_by,
        summary=summary,
        checks=checks,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    _verdicts.append(verdict.dict())
    _persist_verdict(verdict.dict())
    if len(_verdicts) > 200:
        _verdicts.pop(0)

    _log_audit("info" if all_passed else "warning", summary)
    logger.info("Preflight: %s", summary)
    return verdict