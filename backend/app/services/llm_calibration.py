"""LLM Calibration — track hypothesis (cortex) predictions vs outcomes.

Records each LLM prediction (tier, symbol, regime, direction, confidence) when
the hypothesis agent runs. When a trade resolves, matches outcome to the
prediction and updates per-tier, per-regime accuracy and Brier score.

Feeds back to:
- hypothesis_agent: flag tier degradation when accuracy < 50%
- llm_router: route more traffic to highest-accuracy tier per regime
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum predictions per tier before we trust accuracy for routing
MIN_PREDICTIONS_FOR_ROUTING = 50
# Below this accuracy we flag tier degradation
TIER_DEGRADATION_ACCURACY_THRESHOLD = 0.50


def record_llm_prediction(
    council_decision_id: str,
    symbol: str,
    regime: str,
    llm_tier: str,
    predicted_direction: str,
    predicted_confidence: float,
    trade_id: Optional[str] = None,
    llm_latency_ms: int = 0,
) -> bool:
    """Store one LLM prediction for later outcome matching.

    Call after council run when hypothesis vote has llm_tier in metadata.
    """
    if not council_decision_id or not symbol or not llm_tier:
        return False
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        next_id = 1
        try:
            row = conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM llm_predictions"
            ).fetchone()
            if row:
                next_id = row[0]
        except Exception:
            pass
        conn.execute(
            """INSERT INTO llm_predictions
               (id, council_decision_id, trade_id, llm_tier, symbol, regime,
                predicted_direction, predicted_confidence, llm_latency_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                next_id,
                council_decision_id,
                trade_id or "",
                llm_tier.lower(),
                symbol.upper(),
                (regime or "UNKNOWN").upper(),
                (predicted_direction or "hold").lower(),
                float(predicted_confidence),
                int(llm_latency_ms),
            ],
        )
        return True
    except Exception as e:
        logger.debug("LLM calibration record_llm_prediction failed: %s", e)
        return False


def record_llm_outcome(
    trade_id: Optional[str] = None,
    council_decision_id: Optional[str] = None,
    symbol: Optional[str] = None,
    outcome_direction: str = "win",
    r_multiple: float = 0.0,
) -> Optional[Dict[str, Any]]:
    """Match a resolved trade to an LLM prediction and update calibration.

    outcome_direction: "win" | "loss" | "scratch" (scratch resolves row but does not update Brier)
    Returns updated calibration row (tier, regime, accuracy, brier) or None.
    """
    if not trade_id and not council_decision_id and not symbol:
        return None
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()

        # Find unresolved prediction: by trade_id, then council_decision_id, then symbol
        row = None
        if trade_id:
            try:
                rows = conn.execute(
                    "SELECT id, council_decision_id, llm_tier, regime, predicted_direction, predicted_confidence "
                    "FROM llm_predictions WHERE (trade_id = ? OR council_decision_id = ?) AND resolved_at IS NULL "
                    "ORDER BY created_at DESC LIMIT 1",
                    [trade_id, trade_id],
                ).fetchall()
                if rows:
                    row = rows[0]
            except Exception:
                pass
        if not row and council_decision_id:
            try:
                rows = conn.execute(
                    "SELECT id, council_decision_id, llm_tier, regime, predicted_direction, predicted_confidence "
                    "FROM llm_predictions WHERE council_decision_id = ? AND resolved_at IS NULL "
                    "ORDER BY created_at DESC LIMIT 1",
                    [council_decision_id],
                ).fetchall()
                if rows:
                    row = rows[0]
            except Exception:
                pass
        if not row and symbol:
            try:
                rows = conn.execute(
                    "SELECT id, council_decision_id, llm_tier, regime, predicted_direction, predicted_confidence "
                    "FROM llm_predictions WHERE symbol = ? AND resolved_at IS NULL "
                    "ORDER BY created_at DESC LIMIT 1",
                    [symbol.upper()],
                ).fetchall()
                if rows:
                    row = rows[0]
            except Exception:
                pass

        if not row:
            return None

        pred_id, cid, tier, regime, pred_dir, pred_conf = row
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE llm_predictions SET actual_outcome = ?, r_multiple = ?, resolved_at = ? WHERE id = ?",
            [outcome_direction, r_multiple, now, pred_id],
        )

        # Only update calibration for win/loss (not scratch)
        if outcome_direction in ("win", "loss", "profit", "stop_loss"):
            is_win = outcome_direction in ("win", "profit")
            correct_direction = "buy" if is_win else "sell"
            correct = pred_dir == correct_direction
            outcome_01 = 1.0 if correct else 0.0
            brier = (pred_conf - outcome_01) ** 2
            _update_calibration_row(conn, tier, regime, correct, brier)

        return get_llm_calibration(tier=tier, regime=regime)
    except Exception as e:
        logger.debug("LLM calibration record_llm_outcome failed: %s", e)
        return None


def _update_calibration_row(
    conn,
    llm_tier: str,
    regime: str,
    correct: bool,
    brier: float,
) -> None:
    """Upsert one row in llm_calibration for (tier, regime)."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute(
            "SELECT n_predictions, n_correct, brier_score FROM llm_calibration WHERE llm_tier = ? AND regime = ?",
            [llm_tier, regime],
        ).fetchall()
        if rows:
            n_pred, n_correct, old_brier = rows[0]
            n_pred += 1
            n_correct += 1 if correct else 0
            # Running average Brier
            new_brier = old_brier + (brier - old_brier) / n_pred
            conn.execute(
                """UPDATE llm_calibration SET n_predictions = ?, n_correct = ?, brier_score = ?, last_updated = ?
                   WHERE llm_tier = ? AND regime = ?""",
                [n_pred, n_correct, new_brier, now, llm_tier, regime],
            )
        else:
            conn.execute(
                """INSERT INTO llm_calibration (llm_tier, regime, n_predictions, n_correct, brier_score, last_updated)
                   VALUES (?, ?, 1, ?, ?, ?)""",
                [llm_tier, regime, 1 if correct else 0, brier, now],
            )
    except Exception as e:
        logger.debug("LLM calibration _update_calibration_row failed: %s", e)


def get_llm_calibration(
    tier: Optional[str] = None,
    regime: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return calibration stats, optionally filtered by tier and/or regime."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        if tier and regime:
            rows = conn.execute(
                "SELECT llm_tier, regime, n_predictions, n_correct, brier_score, last_updated "
                "FROM llm_calibration WHERE llm_tier = ? AND regime = ?",
                [tier, regime],
            ).fetchall()
        elif tier:
            rows = conn.execute(
                "SELECT llm_tier, regime, n_predictions, n_correct, brier_score, last_updated "
                "FROM llm_calibration WHERE llm_tier = ?",
                [tier],
            ).fetchall()
        elif regime:
            rows = conn.execute(
                "SELECT llm_tier, regime, n_predictions, n_correct, brier_score, last_updated "
                "FROM llm_calibration WHERE regime = ?",
                [regime],
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT llm_tier, regime, n_predictions, n_correct, brier_score, last_updated FROM llm_calibration"
            ).fetchall()

        if not rows:
            return None
        out = []
        for r in rows:
            n_pred, n_correct = r[2], r[3]
            accuracy = (n_correct / n_pred) if n_pred else 0.0
            out.append({
                "llm_tier": r[0],
                "regime": r[1],
                "n_predictions": n_pred,
                "n_correct": n_correct,
                "accuracy": round(accuracy, 4),
                "brier_score": round(float(r[4]), 4),
                "last_updated": r[5],
            })
        if tier and regime and len(out) == 1:
            return out[0]
        return {"calibration": out}
    except Exception as e:
        logger.debug("LLM calibration get_llm_calibration failed: %s", e)
        return None


def get_tier_accuracy_for_router(regime: str) -> List[Tuple[str, float]]:
    """Return list of (tier, accuracy) for the regime, for llm_router tier selection.

    Only includes tiers with >= MIN_PREDICTIONS_FOR_ROUTING predictions.
    Sorted by accuracy descending.
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        rows = conn.execute(
            "SELECT llm_tier, n_predictions, n_correct FROM llm_calibration WHERE regime = ? AND n_predictions >= ?",
            [regime.upper(), MIN_PREDICTIONS_FOR_ROUTING],
        ).fetchall()
        result = []
        for r in rows:
            acc = (r[2] / r[1]) if r[1] else 0.0
            result.append((r[0], round(acc, 4)))
        result.sort(key=lambda x: -x[1])
        return result
    except Exception as e:
        logger.debug("get_tier_accuracy_for_router failed: %s", e)
        return []


def is_tier_degraded(llm_tier: str, regime: Optional[str] = None) -> bool:
    """True if tier accuracy is below TIER_DEGRADATION_ACCURACY_THRESHOLD.

    Used to flag hypothesis_agent when a tier should be deprioritized.
    """
    cal = get_llm_calibration(tier=llm_tier, regime=regime or "")
    if not cal:
        return False
    if "calibration" in cal:
        for c in cal["calibration"]:
            if c["n_predictions"] >= 10 and c["accuracy"] < TIER_DEGRADATION_ACCURACY_THRESHOLD:
                return True
        return False
    return (
        cal.get("n_predictions", 0) >= 10
        and cal.get("accuracy", 1.0) < TIER_DEGRADATION_ACCURACY_THRESHOLD
    )


def get_llm_predictions_table_exists() -> bool:
    """Return True if llm_predictions table exists (for tests)."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        conn.execute("SELECT 1 FROM llm_predictions LIMIT 1")
        return True
    except Exception:
        return False
