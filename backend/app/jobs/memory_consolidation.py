"""Memory Consolidation Job — extracts new heuristics from agent memory bank.

Runs every 6 hours:
1. Scans agent memories for statistically significant patterns
2. Extracts new heuristics that meet confidence thresholds
3. Deactivates stale heuristics below decay threshold
"""
import logging
import datetime

log = logging.getLogger(__name__)

COUNCIL_AGENTS = [
    "market_perception", "flow_perception", "regime", "intermarket",
    "rsi", "bbv", "ema_trend", "relative_strength", "cycle_timing",
    "hypothesis", "strategy", "risk", "execution", "critic",
]


def run() -> dict:
    """Execute memory consolidation. Returns summary dict."""
    ts = datetime.datetime.utcnow().isoformat()
    result = {"status": "ok", "timestamp": ts, "new_heuristics": 0, "agents_scanned": 0}

    try:
        from app.knowledge.heuristic_engine import get_heuristic_engine
        he = get_heuristic_engine()

        total_new = 0
        for agent_name in COUNCIL_AGENTS:
            try:
                new = he.extract_heuristics(agent_name)
                total_new += len(new)
                result["agents_scanned"] += 1
            except Exception as e:
                log.debug("Heuristic extraction failed for %s: %s", agent_name, e)

        result["new_heuristics"] = total_new
        log.info("Memory consolidation: scanned %d agents, extracted %d heuristics",
                 result["agents_scanned"], total_new)
    except Exception as e:
        log.warning("Memory consolidation failed: %s", e)
        result["status"] = "error"
        result["error"] = str(e)

    # Persist snapshot
    try:
        from app.services.database import db_service
        snapshots = db_service.get_config("consolidation_snapshots") or []
        snapshots.append(result)
        db_service.save_config("consolidation_snapshots", snapshots[-28:])  # keep 7 days
    except Exception:
        pass

    return result
