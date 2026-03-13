# ML Drift Detection & Model Registry Integrity — Audit Report

**Date:** March 13, 2026  
**Scope:** Drift detector, model registry, outcome resolver, walk-forward/champion-challenger, ensemble scorer.

---

## 1. Executive summary

- **Drift → retrain:** PSI/data drift and performance decay correctly set `needs_retrain`; the main drift loop does **not** pass `retrain_fn`, so no automatic retrain runs when drift is detected.
- **Drift cooldown:** Fixed at 24h (`RETRAIN_COOLDOWN_HOURS = 24`); no adaptation to regime or volatility.
- **Model registry:** No cleanup of old runs; candidates/archived accumulate. **Added** `cleanup_old_runs(older_than_days=30)` and tests.
- **Outcome resolver:** Symbol/signal_date based; multiple outcomes (e.g. partial fills) are all counted in accuracy. Council outcome matching uses `trade_id` / `council_decision_id` in `weight_learner` (separate from ML outcome_resolver).
- **Ensemble weights:** From env (`ENSEMBLE_XGB_WEIGHT`, `ENSEMBLE_LSTM_WEIGHT`); not per-regime and not learned.
- **Walk-forward / champion-challenger:** Time-based split avoids lookahead; champion_challenger_eval uses **synthetic** evaluation data (not real OOS).
- **Drift log:** In-memory capped at 500; file saves last 50 entries. No rotation by date; acceptable for &lt;1000 entries.

---

## 2. Drift detection → retrain trigger

**Trace:**  
`DriftMonitor.check(live_df, current_accuracy)` → data drift (PSI/alibi) and/or performance drift (floor 0.52, decay 0.10) → `needs_retrain = True` only if `_cooldown_ok()`.

- **PSI threshold:** `PSI_THRESHOLD = 0.20`; feature above that → drifted.  
- **Data drift:** `len(drifted_features) >= max(1, n_features // 5)` → `data_drift_detected`.  
- **Performance:** `current_accuracy < PERF_ACCURACY_FLOOR` or `(baseline - current_accuracy) > PERF_DECAY_THRESHOLD` → `performance_drift_detected`.  
- **Integration gap:** In `main._drift_check_loop()`, `check_drift_and_retrain(..., retrain_fn=None)` is called, so when `needs_retrain` is True no retrain is invoked. To enable auto-retrain, pass a callable (e.g. weekly walk-forward job) as `retrain_fn`.

**Tests added:**  
- `test_rapid_regime_shift_sets_data_drift_and_needs_retrain`  
- `test_drift_cooldown_blocks_second_retrain_within_24h`  
- `test_check_drift_and_retrain_invokes_retrain_fn_when_needs_retrain`  
- `test_check_drift_and_retrain_no_retrain_fn_does_not_raise`

---

## 3. Drift cooldown

- **Current:** `RETRAIN_COOLDOWN_HOURS = 24` in `drift_detector.py` (module constant).  
- **Issue:** Too slow for fast regime changes (e.g. flash crash → recovery).  
- **Recommendation:** Make configurable (e.g. env `DRIFT_RETRAIN_COOLDOWN_HOURS`) and/or shorten under high volatility (e.g. VIX or regime-based).

---

## 4. Model registry cleanup

- **Before:** Only promotion to champion re-stages the previous champion to "archived"; no removal of old candidate/archived runs.  
- **After:** `ModelRegistry.cleanup_old_runs(older_than_days=30, stages=None, delete_artifacts=False)` added. Removes runs in `candidate`/`archived` older than N days; never removes current champions. Optional `delete_artifacts=True` to remove model dirs from disk.

**Tests added:**  
- `test_cleanup_removes_old_candidate_and_archived_runs`  
- `test_cleanup_keeps_recent_candidates`  
- `test_cleanup_respects_stages_param`  
- `test_cleanup_no_op_when_all_recent`

**Recommendation:** Call `cleanup_old_runs(older_than_days=30)` from a scheduled job (e.g. weekly or after training).

---

## 5. Outcome resolver and partial fills

- **ML outcome_resolver:** Stores `(symbol, signal_date, outcome, prediction)`. Accuracy is over all resolved entries that have `prediction` set (30d/90d).  
- **Partial fills:** Multiple `record_outcome` calls (e.g. two legs for same symbol/signal_date) are all stored and included in accuracy. No order_id; matching is by symbol/signal_date only.  
- **Council outcome matching:** In `weight_learner`, matching uses `trade_id` (council_decision_id) and symbol; DuckDB holds full decision history. Bracket/OCO fills that map to one decision are matched by that decision_id; multiple physical orders for one decision need to be reconciled elsewhere (e.g. outcome_tracker / feedback_loop).

**Tests added:**  
- `test_partial_fill_scenario_multiple_outcomes_same_symbol_counted`  
- `test_partial_fill_scenario_mixed_correct_incorrect`

---

## 6. Ensemble weights

- **Source:** `ensemble_scorer.py`: `XGB_WEIGHT` and `LSTM_WEIGHT` from env (`ENSEMBLE_XGB_WEIGHT`, `ENSEMBLE_LSTM_WEIGHT`), defaults 0.6 / 0.4.  
- **Not:** Per-regime or dynamically learned; single global blend.

---

## 7. Walk-forward and OOS validation

- **Train/val split:** `trainer.py` and `xgboost_trainer.py` use `split_by_time(train_end, val_end)`; validation is strictly after train end → no lookahead.  
- **Champion-challenger:** `champion_challenger_eval.py` uses **synthetic** predictions/actuals derived from stored `val_accuracy` and a fixed seed. Code comment: "Using synthetic evaluation data - results are NOT reliable for production." Real OOS would require loading the model and running on held-out data.

---

## 8. Drift log persistence

- **In-memory:** `_drift_log` capped at `MAX_HISTORY_ENTRIES = 500`.  
- **File:** `_save_drift_log()` writes `_drift_log[-50:]` to `drift_log.json`.  
- **Scale:** File stays small; in-memory bounded. For &gt;1000 entries over time, only last 500 are kept in memory and 50 on disk. No date-based rotation; acceptable unless long-term audit trail is required.

---

## 9. Hardcoded thresholds — should be configurable

| Location | Constant | Current value | Suggestion |
|----------|----------|---------------|------------|
| `drift_detector.py` | `DATA_DRIFT_P_VALUE` | 0.05 | Env / config |
| `drift_detector.py` | `PERF_ACCURACY_FLOOR` | 0.52 | Env / config |
| `drift_detector.py` | `PERF_DECAY_THRESHOLD` | 0.10 | Env / config |
| `drift_detector.py` | `PSI_THRESHOLD` | 0.20 | Env / config |
| `drift_detector.py` | `MAX_HISTORY_ENTRIES` | 500 | Env / config |
| `drift_detector.py` | `RETRAIN_COOLDOWN_HOURS` | 24 | Env (e.g. `DRIFT_RETRAIN_COOLDOWN_HOURS`) |
| `multi_window_evaluator.py` | `EVAL_WINDOWS` | [30, 60, 90, 252] | Config |
| `multi_window_evaluator.py` | `THRESHOLDS` (sharpe, profit_factor, max_dd, win_rate) | 0.5, 1.2, -0.15, 0.45 | Config |
| `ensemble_scorer.py` | `XGB_WEIGHT` / `LSTM_WEIGHT` | 0.6 / 0.4 (env) | Already env; consider per-regime |
| `model_registry.py` | `min_sharpe_improvement` / `min_accuracy_improvement` | 0.05 / 0.01 in `evaluate_and_promote` | Config / env |
| `outcome_resolver.py` | Resolved list cap | 2000 | Config |
| `outcome_resolver.py` | 30d / 90d windows | Fixed in `_recompute_accuracy` | Config |

---

## 10. Files touched

- **backend/app/modules/ml_engine/drift_detector.py** — (no code change; cooldown still 24h, documented).  
- **backend/app/modules/ml_engine/model_registry.py** — Added `cleanup_old_runs()`.  
- **backend/tests/test_drift_detector.py** — Rapid regime shift, cooldown, and `check_drift_and_retrain` + retrain_fn tests.  
- **backend/tests/test_model_registry_cleanup.py** — New tests for cleanup.  
- **backend/tests/test_outcome_resolver.py** — Partial-fill scenario tests.  
- **docs/ML-DRIFT-REGISTRY-AUDIT-REPORT.md** — This report.

---

## 11. Recommended next steps

1. **Wire retrain into drift loop:** Pass a retrain callable (e.g. `weekly_walkforward_train.run` or a lightweight retrain) into `check_drift_and_retrain` when drift is detected (with cooldown and rate limits).  
2. **Make drift cooldown configurable:** Env `DRIFT_RETRAIN_COOLDOWN_HOURS` (default 24); consider shortening for high-vol regimes.  
3. **Schedule registry cleanup:** From scheduler, call `get_registry().cleanup_old_runs(30)` (and optionally `delete_artifacts=True`).  
4. **Champion-challenger OOS:** Replace synthetic eval in `champion_challenger_eval.py` with loading the challenger model and evaluating on real held-out data (e.g. from feature store or DuckDB).  
5. **Move thresholds to config:** Add drift, multi-window, and outcome_resolver thresholds to `core/config.py` or env so they can be tuned without code changes.
