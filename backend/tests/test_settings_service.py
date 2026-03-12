"""Tests for settings_service masking and update behavior."""
import pytest
from unittest.mock import patch, MagicMock

from app.services.settings_service import (
    get_all_settings,
    get_settings_by_category,
    update_all_settings,
    update_settings_by_category,
    DEFAULTS,
)


@pytest.fixture
def mock_db():
    """Mock db_service with in-memory store."""
    store = {}
    with patch("app.services.settings_service.db_service") as m:
        m.get_config.side_effect = lambda k: store.get(k)
        m.set_config.side_effect = lambda k, v: store.update({k: v})
        yield store


@pytest.fixture
def with_stored_settings(mock_db):
    """Pre-populate app_settings with a secret."""
    mock_db["app_settings"] = {
        "dataSources": {
            **DEFAULTS["dataSources"],
            "alpacaApiKey": "PK_REAL_KEY_1234",
            "alpacaSecretKey": "secret_abc",
        }
    }
    return mock_db


def test_get_all_settings_masks_secrets(with_stored_settings):
    """GET /settings should return masked secrets (****last4)."""
    result = get_all_settings()
    ds = result.get("dataSources", {})
    assert ds.get("alpacaApiKey", "").startswith("****")
    assert ds.get("alpacaSecretKey", "").startswith("****")
    assert "1234" in (ds.get("alpacaApiKey") or "")
    assert "abc" in (ds.get("alpacaSecretKey") or "")


def test_update_all_settings_does_not_overwrite_secret_with_masked(with_stored_settings):
    """PUT /settings with masked value for a secret should not overwrite stored secret."""
    with patch("app.services.settings_service._propagate_env_changes"):
        update_all_settings({
            "dataSources": {
                "alpacaApiKey": "****1234",
                "finvizApiKey": "new_finviz_key",
            }
        })
    raw = get_settings_by_category("dataSources", mask_secrets=False)
    assert raw.get("alpacaApiKey") == "PK_REAL_KEY_1234"
    assert raw.get("finvizApiKey") == "new_finviz_key"


def test_get_settings_by_category_raw_for_internal_use(with_stored_settings):
    """Internal call with mask_secrets=False returns raw values for test_connection."""
    raw = get_settings_by_category("dataSources", mask_secrets=False)
    assert raw.get("alpacaApiKey") == "PK_REAL_KEY_1234"
    masked = get_settings_by_category("dataSources", mask_secrets=True)
    assert masked.get("alpacaApiKey", "").startswith("****")
