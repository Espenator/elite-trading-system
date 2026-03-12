"""Council verdict WebSocket broadcast — compact payload builder and safe broadcast.

Used by: Council API (POST /evaluate), CouncilGate (all outcomes), and main.py bridge.
Payload is frontend-friendly and consistent for both normal and halted decisions.
WebSocket failures must not break the trading pipeline (broadcast is best-effort).
"""
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def build_compact_verdict_payload(
    verdict: Dict[str, Any],
    halt_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a compact, frontend-friendly verdict payload for WebSocket.

    verdict: full council verdict dict (from DecisionPacket.to_dict() or MessageBus).
    halt_reason: if set, decision was halted (vetoed, hold, timeout, error).

    Returns dict with: councildecisionid, symbol, direction, confidence,
    vote_summary, halt_reason, timestamp.
    """
    votes = verdict.get("votes") or []
    vote_summary: Dict[str, Any] = {"buy": 0, "sell": 0, "hold": 0}
    vetoed_by: List[str] = []
    for v in votes:
        if isinstance(v, dict):
            d = v.get("direction", "hold")
            if d in vote_summary:
                vote_summary[d] = vote_summary.get(d, 0) + 1
            if v.get("veto"):
                vetoed_by.append(v.get("agent_name", "unknown"))
        else:
            d = getattr(v, "direction", "hold")
            if d in vote_summary:
                vote_summary[d] = vote_summary.get(d, 0) + 1
            if getattr(v, "veto", False):
                vetoed_by.append(getattr(v, "agent_name", "unknown"))
    if vetoed_by:
        vote_summary["vetoed_by"] = vetoed_by

    direction = verdict.get("final_direction") or verdict.get("direction") or "hold"
    confidence = verdict.get("final_confidence")
    if confidence is None:
        confidence = verdict.get("confidence", 0.0)
    if isinstance(confidence, (int, float)) and confidence > 1:
        confidence = confidence / 100.0

    resolved_halt = halt_reason if halt_reason is not None else verdict.get("halt_reason")

    return {
        "councildecisionid": verdict.get("council_decision_id") or verdict.get("councildecisionid") or "",
        "symbol": (verdict.get("symbol") or "").upper(),
        "direction": direction.lower(),
        "confidence": round(float(confidence), 4),
        "vote_summary": vote_summary,
        "halt_reason": resolved_halt,
        "timestamp": verdict.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
        "execution_ready": bool(verdict.get("execution_ready", False)),
    }


async def broadcast_council_verdict(payload: Dict[str, Any]) -> None:
    """Broadcast compact verdict to WebSocket channel council_verdict.

    Never raises. Logs and swallows errors so WebSocket failures do not break
    the trading pipeline.
    """
    try:
        from app.websocket_manager import broadcast_ws
        await broadcast_ws("council_verdict", payload, type="verdict")
    except Exception as e:
        logger.debug("Council verdict WS broadcast failed (non-fatal): %s", e)
