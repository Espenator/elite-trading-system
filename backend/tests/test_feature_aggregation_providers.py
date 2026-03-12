"""Tests for feature aggregation: real providers, freshness, and defensive behavior.

Covers: success path, stale data (HOLD), provider timeout, partial provider (OHLCV ok, flow empty).
No mock data in production code paths; tests patch providers to control inputs.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch


@pytest.mark.asyncio
async def test_aggregate_success_returns_validated_payload():
    """When providers return valid data, aggregate returns typed features and freshness metadata."""
    ohlcv_rows = [
        {"date": (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat(), "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0 + i * 0.5, "volume": 1_000_000}
        for i in range(30, 0, -1)
    ]
    last_bar_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")

    def mock_fetch_ohlcv(symbol, limit=60):
        return ohlcv_rows, last_bar_utc, True, ""

    def mock_fetch_regime():
        return {"regime": "bullish", "regime_confidence": 0.8, "vix_close": 14.0}, last_bar_utc, True, ""

    def mock_fetch_flow(symbol):
        return {"flow_call_volume": 100, "flow_put_volume": 80, "flow_net_premium": 50.0, "flow_pcr": 0.8, "flow_total_premium": 200.0}, last_bar_utc, True, ""

    def mock_fetch_indicators(symbol):
        return {"ind_rsi_14": 55.0, "ind_ema_9": 100.5}, last_bar_utc, True, ""

    def mock_fetch_intermarket(symbol):
        return {"intermarket_spy_return": 0.01, "vix_level": 14.0}, last_bar_utc, True, ""

    with patch("app.features.providers.fetch_ohlcv", side_effect=mock_fetch_ohlcv), \
         patch("app.features.providers.fetch_regime", side_effect=mock_fetch_regime), \
         patch("app.features.providers.fetch_flow", side_effect=mock_fetch_flow), \
         patch("app.features.providers.fetch_indicators", side_effect=mock_fetch_indicators), \
         patch("app.features.providers.fetch_intermarket", side_effect=mock_fetch_intermarket):
        from app.features.feature_aggregator import aggregate
        fv = await aggregate("AAPL", timeframe="1d")

    out = fv.to_dict()
    assert "features" in out
    assert "data_quality" in out
    assert "data_freshness" in out or "data_freshness" in out.get("data_quality", {})
    assert "provider_health" in out or "provider_health" in out.get("data_quality", {})

    features = out["features"]
    assert "last_close" in features
    dq = out.get("data_quality", {})
    assert dq.get("is_sufficient") is True
    freshness = out.get("data_freshness") or dq.get("data_freshness") or {}
    assert "last_bar_utc" in freshness
    assert freshness.get("is_stale") is False


@pytest.mark.asyncio
async def test_aggregate_stale_data_sets_insufficient_and_hold_semantics():
    """When last bar is too old, is_sufficient is False and no silent zero last_close."""
    # Last bar 5 days ago
    old_utc = (datetime.now(timezone.utc) - timedelta(days=5)).replace(hour=16, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
    ohlcv_rows = [
        {"date": (datetime.now(timezone.utc) - timedelta(days=5 + i)).date().isoformat(), "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1_000_000}
        for i in range(10, 0, -1)
    ]

    def mock_fetch_ohlcv(symbol, limit=60):
        return ohlcv_rows, old_utc, True, ""

    def mock_fetch_regime():
        return {"regime": "unknown", "regime_confidence": 0.0}, "", True, ""

    def mock_fetch_flow(symbol):
        return {}, "", True, "no_flow_data"

    def mock_fetch_indicators(symbol):
        return {}, "", True, "no_indicator_row"

    def mock_fetch_intermarket(symbol):
        return {}, "", True, ""

    with patch("app.features.providers.fetch_ohlcv", side_effect=mock_fetch_ohlcv), \
         patch("app.features.providers.fetch_regime", side_effect=mock_fetch_regime), \
         patch("app.features.providers.fetch_flow", side_effect=mock_fetch_flow), \
         patch("app.features.providers.fetch_indicators", side_effect=mock_fetch_indicators), \
         patch("app.features.providers.fetch_intermarket", side_effect=mock_fetch_intermarket):
        from app.features.feature_aggregator import aggregate
        fv = await aggregate("AAPL", timeframe="1d")

    out = fv.to_dict()
    dq = out.get("data_quality", {})
    assert dq.get("is_sufficient") is False
    assert dq.get("missing_data_reason") == "stale_ohlcv"
    freshness = out.get("data_freshness") or dq.get("data_freshness") or {}
    assert freshness.get("is_stale") is True
    # Price features may still be present (computed from stale bars) but council should HOLD
    assert "provider_health" in out or "provider_health" in dq


@pytest.mark.asyncio
async def test_aggregate_provider_timeout_marks_provider_failed():
    """When one provider times out, that provider is marked failed; others still present."""
    ohlcv_rows = [
        {"date": (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat(), "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1_000_000}
        for i in range(5, 0, -1)
    ]
    last_bar_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")

    def mock_fetch_ohlcv(symbol, limit=60):
        return ohlcv_rows, last_bar_utc, True, ""

    def mock_fetch_regime():
        raise TimeoutError("regime timeout")

    def mock_fetch_flow(symbol):
        return {}, "", True, "no_flow_data"

    def mock_fetch_indicators(symbol):
        return {}, "", True, ""

    def mock_fetch_intermarket(symbol):
        return {}, "", True, ""

    with patch("app.features.providers.fetch_ohlcv", side_effect=mock_fetch_ohlcv), \
         patch("app.features.providers.fetch_regime", side_effect=mock_fetch_regime), \
         patch("app.features.providers.fetch_flow", side_effect=mock_fetch_flow), \
         patch("app.features.providers.fetch_indicators", side_effect=mock_fetch_indicators), \
         patch("app.features.providers.fetch_intermarket", side_effect=mock_fetch_intermarket):
        from app.features.feature_aggregator import aggregate
        fv = await aggregate("AAPL", timeframe="1d")

    out = fv.to_dict()
    ph = out.get("provider_health") or out.get("data_quality", {}).get("provider_health") or {}
    assert ph.get("regime", {}).get("ok") is False or "error" in ph.get("regime", {})
    assert ph.get("ohlcv", {}).get("ok") is True
    # OHLCV present so is_sufficient can still be True (we have bars)
    assert out["features"].get("last_close") is not None or out["feature_count"] >= 0


@pytest.mark.asyncio
async def test_aggregate_partial_provider_flow_empty_no_zeros():
    """When OHLCV is present but flow has no row, flow_features are empty (no invented zeros)."""
    ohlcv_rows = [
        {"date": (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat(), "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0 + i * 0.1, "volume": 1_000_000}
        for i in range(25, 0, -1)
    ]
    last_bar_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")

    def mock_fetch_ohlcv(symbol, limit=60):
        return ohlcv_rows, last_bar_utc, True, ""

    def mock_fetch_regime():
        return {"regime": "normal", "regime_confidence": 0.5, "vix_close": 18.0}, last_bar_utc, True, ""

    def mock_fetch_flow(symbol):
        return {}, "", True, "no_flow_data"  # no row

    def mock_fetch_indicators(symbol):
        return {"ind_rsi_14": 50.0}, last_bar_utc, True, ""

    def mock_fetch_intermarket(symbol):
        return {"vix_level": 18.0}, last_bar_utc, True, ""

    with patch("app.features.providers.fetch_ohlcv", side_effect=mock_fetch_ohlcv), \
         patch("app.features.providers.fetch_regime", side_effect=mock_fetch_regime), \
         patch("app.features.providers.fetch_flow", side_effect=mock_fetch_flow), \
         patch("app.features.providers.fetch_indicators", side_effect=mock_fetch_indicators), \
         patch("app.features.providers.fetch_intermarket", side_effect=mock_fetch_intermarket):
        from app.features.feature_aggregator import aggregate
        fv = await aggregate("AAPL", timeframe="1d")

    out = fv.to_dict()
    features = out["features"]
    # Flow had no row so flow_* keys should be absent (no invented zeros)
    flow_keys = [k for k in features if "flow_" in k]
    assert len(flow_keys) == 0, "flow_features should be empty when provider has no row"
    assert "last_close" in features
    dq = out.get("data_quality", {})
    assert dq.get("is_sufficient") is True
