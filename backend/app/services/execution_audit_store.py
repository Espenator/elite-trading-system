"""Execution audit store — persist execution requests and results for auditability and idempotency.

Writes to a JSONL file under backend/data/ so that:
- Every execution request is logged before forward to OrderExecutor.
- Every result (submitted / failed / rejected) is logged for audit.
- Idempotency: we can look up by council_decision_id to avoid duplicate orders.

Fail-closed: if the store fails to persist, the router can still reject (no submit without audit).
"""
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default path: repo-relative backend/data/execution_audit.jsonl
_DEFAULT_AUDIT_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_AUDIT_FILENAME = "execution_audit.jsonl"


def _default_audit_path() -> Path:
    return _DEFAULT_AUDIT_DIR / _AUDIT_FILENAME


class ExecutionAuditStore:
    """Append-only audit log for execution requests and results. Thread-safe."""

    def __init__(self, audit_path: Optional[Path] = None):
        self._path = Path(audit_path) if audit_path else _default_audit_path()
        self._lock = threading.Lock()
        self._cache: Dict[str, Dict[str, Any]] = {}  # council_decision_id -> latest record
        self._load_cache()

    def _load_cache(self) -> None:
        """Load existing lines into cache (by council_decision_id) for idempotency lookups."""
        if not self._path.exists():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        did = rec.get("council_decision_id") or rec.get("decision_id")
                        if did:
                            self._cache[did] = rec
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning("ExecutionAuditStore: could not load audit file %s: %s", self._path, e)

    def _append(self, record: Dict[str, Any]) -> None:
        """Append one JSON line. Creates parent dir if needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
            did = record.get("council_decision_id") or record.get("decision_id")
            if did:
                self._cache[did] = record

    def record_request(
        self,
        council_decision_id: str,
        symbol: str,
        side: str,
        status: str = "pending",
        reason: Optional[str] = None,
        error_code: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an execution request (before or at validation). status: pending | rejected."""
        rec = {
            "council_decision_id": council_decision_id,
            "symbol": symbol,
            "side": side,
            "status": status,
            "event": "request",
        }
        if reason:
            rec["reason"] = reason
        if error_code:
            rec["error_code"] = error_code
        if payload:
            rec["payload"] = payload
        rec["requested_at"] = _now_ts()
        self._append(rec)

    def record_result(
        self,
        council_decision_id: str,
        success: bool,
        order_id: str = "",
        client_order_id: str = "",
        symbol: str = "",
        side: str = "",
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        mode: str = "paper",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record execution result (after submit or reject)."""
        status = "submitted" if success else "failed"
        rec = {
            "council_decision_id": council_decision_id,
            "event": "result",
            "status": status,
            "success": success,
            "order_id": order_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": side,
            "mode": mode,
            "resolved_at": _now_ts(),
        }
        if error_code:
            rec["error_code"] = error_code
        if error_message:
            rec["error_message"] = error_message
        if payload:
            rec["payload"] = payload
        self._append(rec)

    def get_status(self, council_decision_id: str) -> Optional[Dict[str, Any]]:
        """Return the latest record for this decision (for idempotency). If status is submitted/failed/rejected, do not re-submit."""
        with self._lock:
            return self._cache.get(council_decision_id)

    def is_already_completed(self, council_decision_id: str) -> bool:
        """True if we already have a terminal result for this decision (submitted or failed)."""
        rec = self.get_status(council_decision_id)
        if not rec:
            return False
        status = (rec.get("status") or "").lower()
        return status in ("submitted", "failed", "rejected")


def _now_ts() -> float:
    import time
    return time.time()


_default_store: Optional[ExecutionAuditStore] = None
_store_lock = threading.Lock()


def get_execution_audit_store(audit_path: Optional[Path] = None) -> ExecutionAuditStore:
    """Singleton access to the execution audit store."""
    global _default_store
    with _store_lock:
        if _default_store is None:
            _default_store = ExecutionAuditStore(audit_path=audit_path)
        return _default_store
