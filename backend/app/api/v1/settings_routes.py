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
from fastapi import APIRouter, HTTPException
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


@router.put("", summary="Bulk update settings")
@router.put("/", include_in_schema=False)
async def put_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Merge incoming category-keyed payload into stored settings."""
    return update_all_settings(payload)


# ── Category list ───────────────────────────────────────────────
@router.get("/categories", summary="List setting categories")
async def list_categories():
    """Return all valid category names."""
    return {"categories": sorted(VALID_CATEGORIES)}


# ── Per-category CRUD ──────────────────────────────────────────
# NOTE: static paths (/categories, /export, /validate, /test-connection, /import)
# MUST be declared before the /{category} catch-all path.

@router.get("/{category}", summary="Get settings by category")
async def get_category(category: str) -> Dict[str, Any]:
    """Return settings for a single category."""
    _assert_category(category)
    return get_settings_by_category(category)


@router.put("/{category}", summary="Update category settings")
async def put_category(category: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Merge payload keys into the specified category settings."""
    _assert_category(category)
    return update_settings_by_category(category, payload)


# ── Reset ─────────────────────────────────────────────────────
@router.post("/reset/{category}", summary="Reset category to defaults")
async def post_reset(category: str) -> Dict[str, Any]:
    """Reset a single settings category back to factory defaults."""
    _assert_category(category)
    return reset_settings(category)


# ── Validation & connectivity ───────────────────────────────────
@router.post("/validate", summary="Validate an API key")
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


@router.post("/test-connection", summary="Test data-source connection")
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


@router.post("/import", summary="Import settings from JSON")
async def post_import(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Import a previously exported settings snapshot."""
    return import_settings(payload)
