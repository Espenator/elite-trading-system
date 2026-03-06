"""
Settings API - Full CRUD with category support, validation, connection testing,
export/import. Delegates all logic to settings_service.

Endpoints:
  GET  /api/v1/settings                   - All settings (flat merged)
  PUT  /api/v1/settings                   - Bulk update (nested by category)
  GET  /api/v1/settings/categories        - List valid category names
  GET  /api/v1/settings/{category}        - Category settings
  PUT  /api/v1/settings/{category}        - Update one category
  POST /api/v1/settings/reset/{category}  - Reset category to defaults
  POST /api/v1/settings/validate          - Validate a provider API key
  POST /api/v1/settings/test-connection   - Test data source connectivity
  GET  /api/v1/settings/export            - Export full settings as JSON
  POST /api/v1/settings/import            - Import settings from JSON
"""
from fastapi import APIRouter, HTTPException, Depends
from app.core.security import require_auth
from typing import Any, Dict, Optional

from app.services.settings_service import (
    DEFAULTS,
    get_all_settings,
    get_settings_by_category,
    update_all_settings,
    update_settings_by_category,
    reset_settings,
    validate_api_key,
    test_connection,
    export_settings,
    import_settings,
)

router = APIRouter()

# Valid category names derived from service DEFAULTS
VALID_CATEGORIES = set(DEFAULTS.keys())


def _assert_category(category: str) -> None:
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Unknown settings category: '{category}'")


# ── Full settings ───────────────────────────────────────────────
@router.get("", summary="Get all settings")
@router.get("/", include_in_schema=False)
async def get_settings() -> Dict[str, Any]:
    """Return all settings across every category, merged with defaults."""
    return get_all_settings()


@router.put("", summary="Bulk update settings", dependencies=[Depends(require_auth)])
@router.put("/", include_in_schema=False, dependencies=[Depends(require_auth)])
async def put_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Merge incoming category-keyed payload into stored settings."""
    return update_all_settings(payload)


# ── Category list ───────────────────────────────────────────────
@router.get("/categories", summary="List setting categories")
async def list_categories():
    """Return all valid category names."""
    return {"categories": sorted(VALID_CATEGORIES)}


# ── Audit log (must be before /{category} catch-all) ──────────
@router.get("/audit-log", summary="Recent settings change log")
async def get_audit_log():
    """Return recent settings changes for the audit log tab."""
    from app.services.database import db_service
    log = db_service.get_config("settings_audit_log") or []
    return {"entries": log[-50:], "logs": log[-50:]}


# ── Per-category CRUD ──────────────────────────────────────────
# NOTE: static paths (/categories, /export, /validate, /test-connection, /import, /audit-log)
# MUST be declared before the /{category} catch-all path.

@router.get("/{category}", summary="Get settings by category")
async def get_category(category: str) -> Dict[str, Any]:
    """Return settings for a single category."""
    _assert_category(category)
    return get_settings_by_category(category)


@router.put("/{category}", summary="Update category settings", dependencies=[Depends(require_auth)])
async def put_category(category: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Merge payload keys into the specified category settings."""
    _assert_category(category)
    return update_settings_by_category(category, payload)


# ── Reset ─────────────────────────────────────────────────────
@router.post("/reset/{category}", summary="Reset category to defaults", dependencies=[Depends(require_auth)])
async def post_reset(category: str) -> Dict[str, Any]:
    """Reset a single settings category back to factory defaults."""
    _assert_category(category)
    return reset_settings(category)


# ── Validation & connectivity ───────────────────────────────────
@router.post("/validate", summary="Validate an API key", dependencies=[Depends(require_auth)])
async def post_validate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a single provider API key against the real provider endpoint.
    Body: {"provider": "alpaca", "apiKey": "...", "secretKey": "..."}
    """
    provider = payload.get("provider")
    if not provider:
        raise HTTPException(status_code=400, detail="Missing required field: 'provider'")
    return validate_api_key(
        provider=provider,
        api_key=payload.get("apiKey", ""),
        secret_key=payload.get("secretKey", ""),
    )


@router.post("/test-connection", summary="Test data-source connection", dependencies=[Depends(require_auth)])
async def post_test_connection(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test live connectivity to a data source using stored keys.
    Body: {"source": "alpaca" | "unusual_whales" | "finviz" | "fred" | "ollama"}
    """
    source = payload.get("source")
    if not source:
        raise HTTPException(status_code=400, detail="Missing required field: 'source'")
    return test_connection(source)


# ── Export / Import ─────────────────────────────────────────────
@router.get("/export", summary="Export all settings as JSON")
async def get_export() -> Dict[str, Any]:
    """Export all settings as a portable JSON snapshot with metadata."""
    return export_settings()


@router.post("/import", summary="Import settings from JSON", dependencies=[Depends(require_auth)])
async def post_import(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Import a previously exported settings snapshot."""
    return import_settings(payload)


# ══════════════════════════════════════════════════════════════════════
# Glass Box: Operator Control Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.post("/risk-limits", summary="Update risk cap sliders", dependencies=[Depends(require_auth)])
async def post_risk_limits(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update risk caps from operator control panel.

    Body: {
        "max_portfolio_heat": 0.25,
        "max_single_position": 0.10,
        "max_daily_trades": 10,
        "max_drawdown_pct": 5.0,
        "kelly_fraction": 0.25,
        "stop_loss_atr_mult": 2.0
    }
    """
    import os

    valid_keys = {
        "max_portfolio_heat", "max_single_position", "max_daily_trades",
        "max_drawdown_pct", "kelly_fraction", "stop_loss_atr_mult",
    }
    updates = {k: v for k, v in payload.items() if k in valid_keys}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid risk limit keys provided")

    # Persist to settings store
    risk_settings = get_settings_by_category("risk") if "risk" in VALID_CATEGORIES else {}
    risk_settings.update(updates)
    if "risk" in VALID_CATEGORIES:
        update_settings_by_category("risk", risk_settings)

    # Apply to running OrderExecutor if available
    applied = {}
    try:
        import app.main as main_mod
        executor = getattr(main_mod, "_order_executor", None)
        if executor:
            if "max_portfolio_heat" in updates:
                executor.max_portfolio_heat = float(updates["max_portfolio_heat"])
                applied["max_portfolio_heat"] = executor.max_portfolio_heat
            if "max_single_position" in updates:
                executor.max_single_position = float(updates["max_single_position"])
                applied["max_single_position"] = executor.max_single_position
            if "max_daily_trades" in updates:
                executor.max_daily_trades = int(updates["max_daily_trades"])
                applied["max_daily_trades"] = executor.max_daily_trades
    except Exception:
        pass

    # Audit log
    _audit_log("risk-limits", updates)

    return {"status": "ok", "updated": updates, "applied_live": applied}


@router.post("/learning", summary="Update learning config", dependencies=[Depends(require_auth)])
async def post_learning(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update learning writeback mode and exploration slider.

    Body: {
        "writeback_enabled": true,
        "exploration_rate": 0.15,
        "learning_rate": 0.05,
        "min_sample_for_heuristic": 25
    }
    """
    valid_keys = {"writeback_enabled", "exploration_rate", "learning_rate", "min_sample_for_heuristic"}
    updates = {k: v for k, v in payload.items() if k in valid_keys}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid learning keys provided")

    # Apply to weight learner if available
    applied = {}
    try:
        from app.council.weight_learner import get_weight_learner
        learner = get_weight_learner()
        if "learning_rate" in updates:
            learner.learning_rate = float(updates["learning_rate"])
            applied["learning_rate"] = learner.learning_rate
    except Exception:
        pass

    # Apply exploration rate to cognitive service if available
    try:
        from app.services.cognitive_telemetry import _get_store
        store = _get_store()
        if "exploration_rate" in updates:
            store["exploration_rate"] = float(updates["exploration_rate"])
            applied["exploration_rate"] = store["exploration_rate"]
    except Exception:
        pass

    _audit_log("learning", updates)
    return {"status": "ok", "updated": updates, "applied_live": applied}


@router.post("/data-sources", summary="Update data source weights/mute", dependencies=[Depends(require_auth)])
async def post_data_sources(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Per-source weight and mute controls for the operator panel.

    Body: {
        "sources": {
            "alpaca": {"weight": 1.0, "muted": false},
            "unusual_whales": {"weight": 0.8, "muted": false},
            "finviz": {"weight": 0.6, "muted": true}
        }
    }
    """
    sources = payload.get("sources", {})
    if not sources:
        raise HTTPException(status_code=400, detail="Missing 'sources' in request body")

    # Persist to settings
    ds_settings = get_settings_by_category("data_sources") if "data_sources" in VALID_CATEGORIES else {}
    ds_settings["source_weights"] = sources
    if "data_sources" in VALID_CATEGORIES:
        update_settings_by_category("data_sources", ds_settings)

    _audit_log("data-sources", sources)
    return {"status": "ok", "sources": sources}


def _audit_log(action: str, details: Any) -> None:
    """Append to settings audit log."""
    import datetime
    try:
        from app.services.database import db_service
        log = db_service.get_config("settings_audit_log") or []
        log.append({
            "action": action,
            "details": details,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        # Keep last 200 entries
        db_service.save_config("settings_audit_log", log[-200:])
    except Exception:
        pass
