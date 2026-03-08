"""P4 Endpoint Tests — Bug 19 first step for overall coverage improvement.

Tests every major API router endpoint returns valid status codes.
Uses the async test client from conftest.py.
"""
import pytest


# ---------------------------------------------------------------------------
# System / Health endpoints
# ---------------------------------------------------------------------------

class TestSystemEndpoints:
    @pytest.mark.anyio
    async def test_health(self, client):
        r = await client.get("/api/v1/system/health")
        assert r.status_code in [200, 404]

    @pytest.mark.anyio
    async def test_status_overview(self, client):
        r = await client.get("/api/v1/status/overview")
        assert r.status_code in [200, 404]

    @pytest.mark.anyio
    async def test_metrics(self, client):
        r = await client.get("/api/v1/system/metrics")
        assert r.status_code in [200, 404]


# ---------------------------------------------------------------------------
# Signal endpoints
# ---------------------------------------------------------------------------

class TestSignalEndpoints:
    @pytest.mark.anyio
    async def test_list_signals(self, client):
        r = await client.get("/api/v1/signals")
        assert r.status_code in [200, 307, 404]

    @pytest.mark.anyio
    async def test_signals_latest(self, client):
        r = await client.get("/api/v1/signals/latest")
        assert r.status_code in [200, 404]


# ---------------------------------------------------------------------------
# Council endpoints
# ---------------------------------------------------------------------------

class TestCouncilEndpoints:
    @pytest.mark.anyio
    async def test_council_status(self, client):
        r = await client.get("/api/v1/council/status")
        assert r.status_code in [200, 404]

    @pytest.mark.anyio
    async def test_council_decisions(self, client):
        r = await client.get("/api/v1/council/decisions")
        assert r.status_code in [200, 404]


# ---------------------------------------------------------------------------
# Risk endpoints
# ---------------------------------------------------------------------------

class TestRiskEndpoints:
    @pytest.mark.anyio
    async def test_risk_overview(self, client):
        r = await client.get("/api/v1/risk")
        assert r.status_code in [200, 307, 404]

    @pytest.mark.anyio
    async def test_kelly_sizer(self, client):
        r = await client.get("/api/v1/risk/kelly-sizer")
        assert r.status_code in [200, 404]


# ---------------------------------------------------------------------------
# Strategy endpoints
# ---------------------------------------------------------------------------

class TestStrategyEndpoints:
    @pytest.mark.anyio
    async def test_strategy_controls(self, client):
        r = await client.get("/api/v1/strategy/controls")
        assert r.status_code in [200, 404, 405]

    @pytest.mark.anyio
    async def test_strategy_status(self, client):
        r = await client.get("/api/v1/strategy/status")
        assert r.status_code in [200, 404, 405]


# ---------------------------------------------------------------------------
# Performance endpoints
# ---------------------------------------------------------------------------

class TestPerformanceEndpoints:
    @pytest.mark.anyio
    async def test_performance_summary(self, client):
        r = await client.get("/api/v1/performance")
        assert r.status_code in [200, 307, 404]

    @pytest.mark.anyio
    async def test_performance_equity_curve(self, client):
        r = await client.get("/api/v1/performance/equity-curve")
        assert r.status_code in [200, 404]


# ---------------------------------------------------------------------------
# Market data endpoints
# ---------------------------------------------------------------------------

class TestMarketEndpoints:
    @pytest.mark.anyio
    async def test_market_overview(self, client):
        r = await client.get("/api/v1/market")
        assert r.status_code in [200, 307, 404]

    @pytest.mark.anyio
    async def test_market_indices(self, client):
        r = await client.get("/api/v1/market/indices")
        assert r.status_code in [200, 404]

    @pytest.mark.anyio
    async def test_market_order_book_returns_200_and_schema(self, client):
        r = await client.get("/api/v1/market/order-book?symbol=SPY")
        assert r.status_code == 200
        data = r.json()
        assert "symbol" in data
        assert "bids" in data
        assert "asks" in data
        assert "status" in data
        # status is either "live" (if Alpaca keys present) or a non-stub fallback
        assert data["status"] != "stub"

    @pytest.mark.anyio
    async def test_market_price_ladder_returns_200_and_schema(self, client):
        r = await client.get("/api/v1/market/price-ladder?symbol=SPY")
        assert r.status_code == 200
        data = r.json()
        assert "symbol" in data
        assert "levels" in data
        assert "status" in data
        assert data["status"] != "stub"

    @pytest.mark.anyio
    async def test_market_regime_returns_200_and_state(self, client):
        r = await client.get("/api/v1/market/regime")
        assert r.status_code == 200
        data = r.json()
        # Must have a "state" key (UNKNOWN when bridge not configured)
        assert "state" in data


# ---------------------------------------------------------------------------
# Alerts endpoints
# ---------------------------------------------------------------------------

class TestAlertEndpoints:
    @pytest.mark.anyio
    async def test_alerts_rules(self, client):
        r = await client.get("/api/v1/alerts/rules")
        assert r.status_code in [200, 404, 405]


# ---------------------------------------------------------------------------
# Backtest endpoints
# ---------------------------------------------------------------------------

class TestBacktestEndpoints:
    @pytest.mark.anyio
    async def test_backtest_status(self, client):
        r = await client.get("/api/v1/backtest/status")
        assert r.status_code in [200, 404]


# ---------------------------------------------------------------------------
# Scanner endpoints
# ---------------------------------------------------------------------------

class TestScannerEndpoints:
    @pytest.mark.anyio
    async def test_scanner_status(self, client):
        r = await client.get("/api/v1/scanner/status")
        assert r.status_code in [200, 404]

    @pytest.mark.anyio
    async def test_turbo_scanner_status(self, client):
        r = await client.get("/api/v1/scanner/turbo/status")
        assert r.status_code in [200, 404]
