"""
Settings API - Full CRUD with category support, validation, connection testing,
export/import. Delegates all logic to settings_service.

Endpoints:
  GET  /api/v1/settings              - All settings
  PUT  /api/v1/settings              - Bulk update
  GET  /api/v1/settings/{category}   - Category settings
  PUT  /api/v1/settings/{category}   - Update category
  POST /api/v1/settings/reset        - Reset to defaults
  POST /api/v1/settings/validate     - Validate provider keys
  POST /api/v1/settings/test-connection - Test data source connectivity
  GET  /api/v1/settings/export       - Export settings as JSON
  POST /api/v1/settings/import       - Import settings from JSON
"""
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Optional

from app.services.settings_service import (
    get_all_settings,
    get_settings_by_category,
    update_all_settings,
    update_category_settings,
    reset_settings,
    validate_api_key,
    test_connection,
    export_settings,
    import_settings,
    CATEGORIES,
)

router = APIRouter()


# ── Full settings ───────────────────────────────────────────────
@router.get("", summary="Get all settings")
@router.get("/", summary="Get all settings", include_in_schema=False)
async def get_settings():
    """Return all settings merged with defaults."""
    return get_all_settings()


@router.put("", summary="Bulk update settings")
@router.put("/", summary="Bulk update settings", include_in_schema=False)
async def put_settings(payload: Dict[str, Any]):
    """Merge incoming keys into stored settings."""
    return update_all_settings(payload)


# ── Category endpoints ──────────────────────────────────────────
@router.get("/categories", summary="List setting categories")
async def list_categories():
    """Return available setting category names."""
    return {"categories": list(CATEGORIES.keys())}


@router.get("/{category}", summary="Get settings by category")
async def get_category(category: str):
    """Return settings for a specific category."""
    if category not in CATEGORIES:
        raise HTTPException(404, f"Unknown category: {category}")
    return get_settings_by_category(category)


@router.put("/{category}", summary="Update category settings")
async def put_category(category: str, payload: Dict[str, Any]):
    """Update only the keys belonging to *category*."""
    if category not in CATEGORIES:
        raise HTTPException(404, f"Unknown category: {category}")
    return update_category_settings(category, payload)


# ── Reset ───────────────────────────────────────────────────────
@router.post("/reset", summary="Reset settings to defaults")
async def post_reset(category: Optional[str] = None):
    """Reset all settings (or a single category) to defaults."""
    if category and category not in CATEGORIES:
        raise HTTPException(404, f"Unknown category: {category}")
    return reset_settings(category)


# ── Validation & connectivity ───────────────────────────────────
@router.post("/validate", summary="Validate an API key")
async def post_validate(payload: Dict[str, Any]):
    """
    Validate a single provider key.
    Body: {"provider": "alpaca", "apiKey": "...", "secretKey": "..."}
    """
    provider = payload.get("provider")
    if not provider:
        raise HTTPException(400, "Missing 'provider' field")
    api_key = payload.get("apiKey", "")
    secret_key = payload.get("secretKey", "")
    return validate_api_key(provider, api_key, secret_key)


@router.post("/test-connection", summary="Test data-source connection")
async def post_test_connection(payload: Dict[str, Any]):
    """
    Test connectivity to a data source using stored keys.
    Body: {"source": "alpaca"}
    """
    source = payload.get("source")
    if not source:
        raise HTTPException(400, "Missing 'source' field")
    return test_connection(source)


# ── Export / Import ─────────────────────────────────────────────
@router.get("/export", summary="Export settings")
async def get_export():
    """Export all settings as JSON with metadata."""
    return export_settings()


@router.post("/import", summary="Import settings")
async def post_import(payload: Dict[str, Any]):
    """Import settings from a previously exported JSON payload."""
    return import_settings(payload)
