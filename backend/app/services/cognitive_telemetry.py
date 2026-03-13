"""Cognitive Telemetry Service — tracks the quality of council reasoning over time.

Embodier Trader Being Intelligence (ETBI) framework:
  Collects metrics after every council evaluation and provides aggregated
  insights for the Research Dashboard. Stored in DuckDB for persistence.

Metrics tracked:
  - hypothesis_diversity: Shannon entropy of agent directions per eval
  - agent_agreement: fraction agreeing with final direction
  - memory_precision: relevance of recalled heuristics
  - confidence_calibration: Brier score (predicted conf vs actual outcome)
  - mode_distribution: explore/exploit/defensive ratio over time
  - latency_profile: per-stage and total latency trends
  - exploration_outcomes: P&L of explore-mode vs exploit-mode decisions
"""
import logging
import math
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.services.database import db_service

logger = logging.getLogger(__name__)

CONFIG_KEY = "cognitive_telemetry"
MAX_SNAPSHOTS = 2000  # Rolling window of evaluations


def _get_store() -> Dict[str, Any]:
    return db_service.get_config(CONFIG_KEY) or {
        "snapshots": [],
        "calibration": {"predictions": [], "outcomes": []},
        "mode_switches": [],
        "aggregate": {},
    }


def _save_store(store: Dict[str, Any]) -> None:
    db_service.set_config(CONFIG_KEY, store)


def record_cognitive_snapshot(
    council_decision_id: str,
    symbol: str,
    final_direction: str,
    final_confidence: float,
    cognitive_meta: Dict[str, Any],
    active_hypothesis: Optional[Dict[str, Any]] = None,
    semantic_context: Optional[Dict[str, Any]] = None,
) -> None:
    """Record cognitive telemetry from a council evaluation."""
    store = _get_store()
    snapshots = store.get("snapshots", [])

    snapshot = {
        "id": council_decision_id,
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction": final_direction,
        "confidence": final_confidence,
        "mode": cognitive_meta.get("mode", "exploit"),
        "hypothesis_diversity": cognitive_meta.get("hypothesis_diversity", 0),
        "agent_agreement": cognitive_meta.get("agent_agreement", 0),
        "memory_precision": cognitive_meta.get("memory_precision", 0),
        "total_latency_ms": cognitive_meta.get("total_latency_ms", 0),
        "stage_latencies": cognitive_meta.get("stage_latencies", {}),
        "hypothesis_direction": (active_hypothesis or {}).get("direction"),
        "heuristics_recalled": len((semantic_context or {}).get("active_heuristics", [])),
    }

    snapshots.append(snapshot)
    store["snapshots"] = snapshots[-MAX_SNAPSHOTS:]

    # Track mode switches
    mode_switches = store.get("mode_switches", [])
    if mode_switches and mode_switches[-1].get("mode") != snapshot["mode"]:
        mode_switches.append({
            "timestamp": snapshot["timestamp"],
            "mode": snapshot["mode"],
            "from_mode": mode_switches[-1]["mode"],
        })
    elif not mode_switches:
        mode_switches.append({"timestamp": snapshot["timestamp"], "mode": snapshot["mode"]})
    store["mode_switches"] = mode_switches[-500:]

    _save_store(store)


def record_outcome(council_decision_id: str, outcome: str, r_multiple: float) -> None:
    """Record trade outcome for confidence calibration (Brier score).

    Args:
        council_decision_id: Links to the council evaluation
        outcome: "win" | "loss" | "scratch"
        r_multiple: Realized R-multiple
    """
    store = _get_store()
    calibration = store.get("calibration", {"predictions": [], "outcomes": []})

    # Find the matching snapshot to get predicted confidence
    snapshots = store.get("snapshots", [])
    matching = [s for s in snapshots if s["id"] == council_decision_id]
    if matching:
        snap = matching[-1]
        actual = 1.0 if outcome == "win" else 0.0
        calibration["predictions"].append({
            "id": council_decision_id,
            "predicted_conf": snap["confidence"],
            "actual": actual,
            "r_multiple": r_multiple,
            "mode": snap.get("mode", "exploit"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        calibration["predictions"] = calibration["predictions"][-1000:]

    store["calibration"] = calibration
    _save_store(store)


def get_cognitive_dashboard() -> Dict[str, Any]:
    """Aggregate cognitive telemetry for the Research Dashboard."""
    store = _get_store()
    snapshots = store.get("snapshots", [])
    calibration = store.get("calibration", {"predictions": [], "outcomes": []})
    mode_switches = store.get("mode_switches", [])

    if not snapshots:
        return {
            "total_evaluations": 0,
            "metrics": {
                "avg_hypothesis_diversity": 0,
                "avg_agent_agreement": 0,
                "avg_memory_precision": 0,
                "avg_latency_ms": None,
            },
            "mode_distribution": {"exploit": 1.0},
            "latency_profile": {},
            "calibration": {},
            "exploration_outcomes": {},
            "recent_snapshots": [],
            "time_series": [],
        }

    # Aggregate metrics
    n = len(snapshots)
    avg_diversity = sum(s.get("hypothesis_diversity", 0) for s in snapshots) / n
    avg_agreement = sum(s.get("agent_agreement", 0) for s in snapshots) / n
    avg_memory_precision = sum(s.get("memory_precision", 0) for s in snapshots) / n
    avg_latency = sum(s.get("total_latency_ms", 0) for s in snapshots) / n

    # Mode distribution
    mode_counts = {}
    for s in snapshots:
        m = s.get("mode", "exploit")
        mode_counts[m] = mode_counts.get(m, 0) + 1
    mode_dist = {k: round(v / n, 3) for k, v in mode_counts.items()}

    # Latency profile by stage (averaged)
    stage_totals = {}
    stage_counts = {}
    for s in snapshots:
        for stage, ms in s.get("stage_latencies", {}).items():
            stage_totals[stage] = stage_totals.get(stage, 0) + ms
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
    latency_profile = {
        stage: round(stage_totals[stage] / stage_counts[stage], 1)
        for stage in stage_totals
    }

    # Brier score for confidence calibration
    predictions = calibration.get("predictions", [])
    brier_score = None
    if predictions:
        brier_sum = sum(
            (p["predicted_conf"] - p["actual"]) ** 2
            for p in predictions
        )
        brier_score = round(brier_sum / len(predictions), 4)

    # Exploration vs exploitation outcomes
    explore_outcomes = [p for p in predictions if p.get("mode") == "explore"]
    exploit_outcomes = [p for p in predictions if p.get("mode") == "exploit"]
    exploration_outcomes = {
        "explore_count": len(explore_outcomes),
        "explore_win_rate": (
            sum(1 for p in explore_outcomes if p["actual"] == 1.0) / len(explore_outcomes)
            if explore_outcomes else None
        ),
        "explore_avg_r": (
            sum(p.get("r_multiple", 0) for p in explore_outcomes) / len(explore_outcomes)
            if explore_outcomes else None
        ),
        "exploit_count": len(exploit_outcomes),
        "exploit_win_rate": (
            sum(1 for p in exploit_outcomes if p["actual"] == 1.0) / len(exploit_outcomes)
            if exploit_outcomes else None
        ),
        "exploit_avg_r": (
            sum(p.get("r_multiple", 0) for p in exploit_outcomes) / len(exploit_outcomes)
            if exploit_outcomes else None
        ),
    }

    # Mode switches in last 24h
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_switches = [s for s in mode_switches if s.get("timestamp", "") > cutoff]

    # Time series (last 50 snapshots for charts)
    time_series = [
        {
            "timestamp": s["timestamp"],
            "diversity": s.get("hypothesis_diversity", 0),
            "agreement": s.get("agent_agreement", 0),
            "confidence": s.get("confidence", 0),
            "latency_ms": s.get("total_latency_ms", 0),
            "mode": s.get("mode", "exploit"),
        }
        for s in snapshots[-50:]
    ]

    return {
        "total_evaluations": n,
        "metrics": {
            "avg_hypothesis_diversity": round(avg_diversity, 4),
            "avg_agent_agreement": round(avg_agreement, 4),
            "avg_memory_precision": round(avg_memory_precision, 4),
            "avg_latency_ms": round(avg_latency, 1),
        },
        "mode_distribution": mode_dist,
        "mode_switches_24h": len(recent_switches),
        "latency_profile": latency_profile,
        "calibration": {
            "brier_score": brier_score,
            "total_predictions": len(predictions),
        },
        "exploration_outcomes": exploration_outcomes,
        "recent_snapshots": snapshots[-10:],
        "time_series": time_series,
    }


def determine_cognitive_mode(
    regime_entropy: float = 0.0,
    homeostasis_mode: str = "NORMAL",
    recent_explore_win_rate: Optional[float] = None,
    hypothesis_diversity: float = 0.0,
) -> str:
    """Determine whether the council should explore, exploit, or defend.

    Rules:
      - HALTED/DEFENSIVE homeostasis → "defensive"
      - High regime entropy (>0.8) AND high diversity → "explore"
      - Recent exploration win rate < 30% → back to "exploit"
      - Default: "exploit"
    """
    if homeostasis_mode in ("HALTED", "DEFENSIVE"):
        return "defensive"

    # Explore when regime is uncertain and agents disagree
    if regime_entropy > 0.8 and hypothesis_diversity > 0.5:
        # But not if recent exploration has been losing
        if recent_explore_win_rate is not None and recent_explore_win_rate < 0.30:
            return "exploit"
        return "explore"

    return "exploit"
