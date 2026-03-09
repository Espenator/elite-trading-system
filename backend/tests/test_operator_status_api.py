"""
Tests for operator status API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_operator_status():
    """Test GET /api/v1/operator-status returns valid status"""
    response = client.get("/api/v1/operator-status")
    assert response.status_code == 200

    data = response.json()
    assert "tradingMode" in data
    assert "executionAuthority" in data
    assert "autoState" in data
    assert "alpacaStatus" in data
    assert "riskPolicy" in data
    assert "blockReasons" in data
    assert "isSystemActive" in data

    # Check default values
    assert data["tradingMode"] in ["Manual", "Auto"]
    assert data["executionAuthority"] in ["human", "system"]
    assert data["autoState"] in ["armed", "active", "paused", "blocked"]
    assert isinstance(data["blockReasons"], list)
    assert isinstance(data["isSystemActive"], bool)


def test_operator_status_schema():
    """Test that operator status response matches expected schema"""
    response = client.get("/api/v1/operator-status")
    data = response.json()

    # Alpaca status structure
    alpaca = data["alpacaStatus"]
    assert "connected" in alpaca
    assert "accountType" in alpaca
    assert "status" in alpaca
    assert alpaca["accountType"] in ["paper", "live"]

    # Risk policy structure
    risk = data["riskPolicy"]
    assert "maxRiskPerTrade" in risk
    assert "maxOpenPositions" in risk
    assert "portfolioHeat" in risk
    assert "maxPortfolioHeat" in risk
    assert "dailyLossCap" in risk
    assert "weeklyDrawdownCap" in risk
    assert "stopLossRequired" in risk
    assert "takeProfitPolicy" in risk
    assert "cooldownAfterLossStreak" in risk
    assert "currentLossStreak" in risk


def test_set_trading_mode_unauthorized():
    """Test that mode change requires authentication"""
    response = client.put("/api/v1/operator-status/mode", json={"mode": "Auto"})
    # Should require auth (403 or 401)
    assert response.status_code in [401, 403]


def test_set_auto_state_unauthorized():
    """Test that auto state change requires authentication"""
    response = client.put("/api/v1/operator-status/auto-state", json={"state": "armed"})
    # Should require auth (403 or 401)
    assert response.status_code in [401, 403]


def test_kill_switch_unauthorized():
    """Test that kill switch requires authentication"""
    response = client.post("/api/v1/operator-status/kill-switch")
    # Should require auth (403 or 401)
    assert response.status_code in [401, 403]


def test_operator_status_default_state():
    """Test that default operator state is safe (Manual mode)"""
    response = client.get("/api/v1/operator-status")
    data = response.json()

    # System should default to Manual mode for safety
    # Even if db is empty, we should get Manual
    assert data["tradingMode"] == "Manual"
    assert data["executionAuthority"] == "human"
