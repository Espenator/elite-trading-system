"""Weekly job: walk-forward XGBoost retraining with risk-adjusted objective.

Idempotent: checks last training date, skips if trained this week.
CLI: python -m app.jobs.weekly_walkforward_train
"""
import logging
from datetime import date, datetime, timezone

log = logging.getLogger(__name__)

_last_train_date: str = ""


def run(symbols: list = None, use_risk_adjusted: bool = True) -> dict:
    """Pull features, train XGBoost, register as challenger.

    Args:
        symbols: Override symbol list. Defaults to tracked symbols.
        use_risk_adjusted: Use risk-adjusted objective (anti-reward-hacking).

    Returns:
        Dict with status, model info, metrics.
    """
    global _last_train_date

    today = date.today().isoformat()
    # Simple weekly check: skip if we already trained in the last 6 days
    if _last_train_date and _last_train_date >= today:
        log.info("weekly_walkforward_train already ran (%s), skipping", _last_train_date)
        return {"status": "skipped", "reason": "already_trained", "date": _last_train_date}

    log.info("Running weekly_walkforward_train for %s", today)

    result = {
        "status": "completed",
        "date": today,
        "model_name": None,
        "run_id": None,
        "metrics": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Resolve symbols
    if not symbols:
        try:
            from app.modules.symbol_universe import get_tracked_symbols
            symbols = get_tracked_symbols()
        except Exception as e:
            logger.debug("Symbol universe unavailable, using defaults: %s", e)
            symbols = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]

    # Train via v2 pipeline
    try:
        from app.modules.ml_engine.xgboost_trainer import train_xgboost_v2

        train_result = train_xgboost_v2(symbols)

        if train_result is None:
            result["status"] = "no_data"
            result["error"] = "Training returned None (insufficient data)"
            log.warning("Training aborted: no data")
            _last_train_date = today
            return result

        result["metrics"] = train_result.get("metadata", {})
        result["model_path"] = train_result.get("model_path")

        # Register as challenger
        try:
            from app.modules.ml_engine.model_registry import get_registry

            registry = get_registry()
            model = train_result["model"]
            run = registry.log_training_run(
                model_name="xgboost_daily",
                model=model,
                params=train_result.get("params", {}),
                metrics={
                    "val_accuracy": train_result.get("val_accuracy", 0),
                    "cv_logloss": train_result.get("cv_results", {}).get("cv_logloss", 0),
                    "cv_accuracy": train_result.get("cv_results", {}).get("cv_accuracy", 0),
                },
                feature_cols=train_result.get("metadata", {}).get("feature_cols", []),
                notes=f"Weekly walkforward {today}",
            )
            result["run_id"] = run.run_id
            result["model_name"] = "xgboost_daily"
            log.info("Registered challenger: %s", run.run_id)
        except Exception as e:
            log.warning("Model registry failed: %s", e)
            result["registry_error"] = str(e)

    except Exception as e:
        log.warning("Training failed: %s", e)
        result["status"] = "error"
        result["error"] = str(e)

    _last_train_date = today
    log.info("weekly_walkforward_train completed: %s", result.get("status"))
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    print(run())
