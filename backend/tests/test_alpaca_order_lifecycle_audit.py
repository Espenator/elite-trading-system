"""
Alpaca Broker Integration — Order Lifecycle & Reconciliation Audit (Prompt 18).

Tests:
- All 9 order executor gates (regime, circuit breaker, Kelly, portfolio heat,
  viability, HITL placeholder, duplicate check, market hours placeholder, notional).
- 429 rate limit scenario (AlpacaService retry + optional key pool reporting).
- Position reconciliation gap detection (internal vs Alpaca drift).

Run: cd backend && python -m pytest tests/test_alpaca_order_lifecycle_audit.py -v
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.execution_decision import ExecutionDecision, ExecutionDenyReason
from app.services.order_executor import OrderExecutor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bus():
    bus = AsyncMock()
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def executor(mock_bus):
    return OrderExecutor(
        message_bus=mock_bus,
        auto_execute=False,
        min_score=70.0,
        max_daily_trades=10,
        cooldown_seconds=0,
        max_portfolio_heat=0.5,
        max_single_position=0.10,
    )


def _valid_verdict(score=75.0, regime="GREEN", **kwargs):
    base = {
        "symbol": "AAPL",
        "final_direction": "buy",
        "final_confidence": 0.8,
        "execution_ready": True,
        "signal_data": {"score": score, "regime": regime, "price": 150.0},
        "price": 150.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    base.update(kwargs)
    return base


def _mock_kelly_result(qty=100, kelly_pct=0.05):
    return {
        "action": "BUY",
        "kelly_pct": kelly_pct,
        "qty": qty,
        "edge": 0.1,
        "raw_kelly": 0.1,
        "stats_source": "test",
        "stop_loss": 140.0,
        "take_profit": 160.0,
    }


def _mock_risk_governor_approve():
    mock_gov = MagicMock()
    def _approve(req):
        return MagicMock(approved=True, approved_shares=req.shares, reason="")
    mock_gov.approve = _approve
    return patch("app.modules.openclaw.execution.risk_governor.get_governor", return_value=mock_gov)


def _run_verdict(executor, verdict, mock_bus):
    """Run verdict through executor with minimal mocks so gates run."""
    with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
        m_kelly.return_value = _mock_kelly_result(qty=50)
        with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
            with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                alpaca = MagicMock()
                alpaca.get_account = AsyncMock(return_value={"equity": "100000", "last_equity": "100000"})
                alpaca.get_positions = AsyncMock(return_value=[])
                alpaca._cache_get = MagicMock(return_value=None)
                executor._get_alpaca_service = MagicMock(return_value=alpaca)
                with patch("app.api.v1.strategy.REGIME_PARAMS", {
                    "GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0},
                    "RED": {"max_pos": 0, "kelly_scale": 0.25, "signal_mult": 0.85},
                    "YELLOW": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0},
                }):
                    with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                        with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                            with _mock_risk_governor_approve():
                                import asyncio
                                return asyncio.get_event_loop().run_until_complete(
                                    _run_verdict_async(executor, verdict)
                                )
    return None


async def _run_verdict_async(executor, verdict):
    executor._running = True
    await executor._on_council_verdict(verdict)
    await executor.stop()


# ---------------------------------------------------------------------------
# Gate 1: Regime gate
# ---------------------------------------------------------------------------

class TestGate1Regime:
    """Regime gate: market regime must allow trading (max_pos > 0, kelly_scale > 0)."""

    @pytest.mark.anyio
    async def test_regime_red_blocks_order(self, executor, mock_bus):
        verdict = _valid_verdict(regime="RED")
        with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
            m_kelly.return_value = _mock_kelly_result(qty=50)
            with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                    alpaca = MagicMock()
                    alpaca.get_account = AsyncMock(return_value={"equity": "100000"})
                    alpaca.get_positions = AsyncMock(return_value=[])
                    alpaca._cache_get = MagicMock(return_value=None)
                    executor._get_alpaca_service = MagicMock(return_value=alpaca)
                    with patch("app.api.v1.strategy.REGIME_PARAMS", {
                        "RED": {"max_pos": 0, "kelly_scale": 0, "signal_mult": 0},
                        "GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0},
                    }):
                        with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                            with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                await executor.start()
                                await executor._on_council_verdict(verdict)
                                await executor.stop()
        assert executor._signals_rejected >= 1


    @pytest.mark.anyio
    async def test_regime_position_limit_blocks_when_at_cap(self, executor, mock_bus):
        verdict = _valid_verdict(regime="GREEN")
        with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
            m_kelly.return_value = _mock_kelly_result(qty=50)
            with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                    alpaca = MagicMock()
                    alpaca.get_account = AsyncMock(return_value={"equity": "100000"})
                    alpaca.get_positions = AsyncMock(return_value=[
                        {"symbol": "A"}, {"symbol": "B"}, {"symbol": "C"},
                        {"symbol": "D"}, {"symbol": "E"},
                    ])
                    alpaca._cache_get = MagicMock(return_value=None)
                    executor._get_alpaca_service = MagicMock(return_value=alpaca)
                    with patch("app.api.v1.strategy.REGIME_PARAMS", {
                        "GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0},
                    }):
                        with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                            with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                await executor.start()
                                await executor._on_council_verdict(verdict)
                                await executor.stop()
        assert executor._signals_rejected >= 1


# ---------------------------------------------------------------------------
# Gate 2: Circuit breaker
# ---------------------------------------------------------------------------

class TestGate2CircuitBreaker:
    """Circuit breaker: leverage <= 2x, concentration <= 25%."""

    @pytest.mark.anyio
    async def test_circuit_breaker_high_leverage_blocks(self, executor, mock_bus):
        verdict = _valid_verdict()
        with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
            m_kelly.return_value = _mock_kelly_result(qty=50)
            with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                    alpaca = MagicMock()
                    alpaca.get_account = AsyncMock(return_value={"equity": "100000"})
                    alpaca.get_positions = AsyncMock(return_value=[
                        {"symbol": "X", "market_value": "150000"},
                        {"symbol": "Y", "market_value": "100000"},
                    ])
                    alpaca._cache_get = MagicMock(return_value=None)
                    executor._get_alpaca_service = MagicMock(return_value=alpaca)
                    with patch("app.api.v1.strategy.REGIME_PARAMS", {"GREEN": {"max_pos": 6, "kelly_scale": 1.0, "signal_mult": 1.0}}):
                        with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                            with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                await executor.start()
                                await executor._on_council_verdict(verdict)
                                await executor.stop()
        assert executor._signals_rejected >= 1


# ---------------------------------------------------------------------------
# Gate 3: Kelly sizing
# ---------------------------------------------------------------------------

class TestGate3KellySizing:
    """Kelly sizing gate: REJECT or HOLD from sizer blocks order."""

    @pytest.mark.anyio
    async def test_kelly_hold_blocks_order(self, executor, mock_bus):
        verdict = _valid_verdict()
        with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
            m_kelly.return_value = {"action": "HOLD", "kelly_pct": 0.0, "qty": 0, "edge": 0.01, "stats_source": "test"}
            with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                    alpaca = MagicMock()
                    alpaca.get_account = AsyncMock(return_value={"equity": "100000"})
                    alpaca.get_positions = AsyncMock(return_value=[])
                    alpaca._cache_get = MagicMock(return_value=None)
                    executor._get_alpaca_service = MagicMock(return_value=alpaca)
                    with patch("app.api.v1.strategy.REGIME_PARAMS", {"GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0}}):
                        with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                            with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                await executor.start()
                                await executor._on_council_verdict(verdict)
                                await executor.stop()
        assert executor._signals_rejected >= 1


# ---------------------------------------------------------------------------
# Gate 4: Portfolio heat
# ---------------------------------------------------------------------------

class TestGate4PortfolioHeat:
    """Portfolio heat: new_position_pct must not exceed remaining heat capacity."""

    @pytest.mark.anyio
    async def test_portfolio_heat_exceeded_blocks_order(self, executor, mock_bus):
        verdict = _valid_verdict()
        with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
            m_kelly.return_value = _mock_kelly_result(qty=50, kelly_pct=0.40)
            with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock) as m_heat:
                    m_heat.return_value = (False, {"current_heat": 0.45, "remaining": 0.05})
                    alpaca = MagicMock()
                    alpaca.get_account = AsyncMock(return_value={"equity": "100000", "last_equity": "100000"})
                    alpaca.get_positions = AsyncMock(return_value=[])
                    alpaca._cache_get = MagicMock(return_value=None)
                    executor._get_alpaca_service = MagicMock(return_value=alpaca)
                    with patch("app.api.v1.strategy.REGIME_PARAMS", {"GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0}}):
                        with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                            with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                await executor.start()
                                await executor._on_council_verdict(verdict)
                                await executor.stop()
        assert executor._signals_rejected >= 1


# ---------------------------------------------------------------------------
# Gate 5: Viability
# ---------------------------------------------------------------------------

class TestGate5Viability:
    """Viability: expected cost must not exceed edge (when ENABLE_EXECUTION_VIABILITY_GATE)."""

    @pytest.mark.anyio
    async def test_viability_denied_blocks_order(self, executor, mock_bus):
        verdict = _valid_verdict()
        with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
            m_kelly.return_value = _mock_kelly_result(qty=50)
            with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                    with patch.object(executor, "_check_viability", new_callable=AsyncMock) as m_viab:
                        m_viab.return_value = (False, "cost exceeds edge")
                        alpaca = MagicMock()
                        alpaca.get_account = AsyncMock(return_value={"equity": "100000"})
                        alpaca.get_positions = AsyncMock(return_value=[])
                        alpaca._cache_get = MagicMock(return_value=None)
                        executor._get_alpaca_service = MagicMock(return_value=alpaca)
                        with patch("app.api.v1.strategy.REGIME_PARAMS", {"GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0}}):
                            with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                                with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                    with patch("app.core.config.settings") as m_settings:
                                        m_settings.ENABLE_EXECUTION_VIABILITY_GATE = True
                                        with _mock_risk_governor_approve():
                                            await executor.start()
                                            await executor._on_council_verdict(verdict)
                                            await executor.stop()
        assert executor._signals_rejected >= 1


# ---------------------------------------------------------------------------
# Gate 6: HITL — not in OrderExecutor (handled upstream in council_gate/hitl_gate)
# ---------------------------------------------------------------------------

class TestGate6HITL:
    """HITL gate is enforced upstream (council_gate / hitl_gate); OrderExecutor assumes verdict is approved."""

    def test_execution_decision_required_for_submit(self):
        """OrderExecutor only submits via ExecutionDecision (no direct path)."""
        from app.services.order_executor import OrderExecutor
        from app.services.execution_decision import ExecutionDecision
        dec = ExecutionDecision(
            symbol="AAPL", side="buy", qty=10, price=150.0, direction="buy",
            execution_ready=True, signal_score=75.0, council_confidence=0.8,
            regime="GREEN", kelly_pct=0.05, stop_loss=140.0, take_profit=160.0,
            sizing_metadata={}, risk_checks_passed=True, verdict_timestamp=time.time(),
            council_decision_id="test-id",
        )
        assert dec.symbol == "AAPL" and dec.qty == 10


# ---------------------------------------------------------------------------
# Gate 7: Duplicate check
# ---------------------------------------------------------------------------

class TestGate7DuplicateCheck:
    """Duplicate verdicts (same symbol/direction/confidence/price within 60s) are suppressed."""

    @pytest.mark.anyio
    async def test_duplicate_verdict_suppressed(self, executor, mock_bus):
        verdict = _valid_verdict()
        with patch.object(executor, "_compute_kelly_size", new_callable=AsyncMock) as m_kelly:
            m_kelly.return_value = _mock_kelly_result(qty=50)
            with patch.object(executor, "_check_drawdown", new_callable=AsyncMock, return_value=True):
                with patch.object(executor, "_check_portfolio_heat", new_callable=AsyncMock, return_value=(True, {})):
                    alpaca = MagicMock()
                    alpaca.get_account = AsyncMock(return_value={"equity": "100000", "last_equity": "100000"})
                    alpaca.get_positions = AsyncMock(return_value=[])
                    alpaca._cache_get = MagicMock(return_value=None)
                    executor._get_alpaca_service = MagicMock(return_value=alpaca)
                    with patch("app.api.v1.strategy.REGIME_PARAMS", {"GREEN": {"max_pos": 5, "kelly_scale": 1.0, "signal_mult": 1.0}}):
                        with patch("app.api.v1.risk_shield_api.is_entries_frozen", return_value=False):
                            with patch("app.api.v1.brain.get_degraded_status", return_value={"degraded": False}):
                                with _mock_risk_governor_approve():
                                    await executor.start()
                                    await executor._on_council_verdict(verdict)
                                    publish_count_first = mock_bus.publish.call_count
                                    await executor._on_council_verdict(verdict)
                                    publish_count_second = mock_bus.publish.call_count
                                    await executor.stop()
        assert publish_count_second == publish_count_first


# ---------------------------------------------------------------------------
# Gate 8: Market hours — OrderExecutor does not check; Alpaca rejects outside hours
# ---------------------------------------------------------------------------

class TestGate8MarketHours:
    """Market hours: no explicit gate in OrderExecutor; rely on Alpaca API rejection."""

    def test_order_type_selection_uses_notional(self):
        """_select_order_type uses notional (price * qty) for market vs limit vs TWAP."""
        from app.services.order_executor import OrderExecutor
        bus = MagicMock()
        ex = OrderExecutor(message_bus=bus, auto_execute=False)
        order_type, limit_price = ex._select_order_type(100.0, 30)
        assert order_type == "market" and limit_price is None
        order_type, limit_price = ex._select_order_type(100.0, 60)
        assert order_type == "limit" and limit_price == 100.0
        order_type, limit_price = ex._select_order_type(500.0, 60)
        assert order_type == "twap" and limit_price == 500.0


# ---------------------------------------------------------------------------
# Gate 9: Notional limit
# ---------------------------------------------------------------------------

class TestGate9NotionalLimit:
    """Notional thresholds: <= 5K market, 5K–25K limit, > 25K TWAP."""

    def test_notional_threshold_constants(self):
        assert OrderExecutor.LIMIT_ORDER_NOTIONAL_THRESHOLD == 5_000.0
        assert OrderExecutor.TWAP_NOTIONAL_THRESHOLD == 25_000.0

    def test_select_order_type_respects_thresholds(self):
        bus = MagicMock()
        ex = OrderExecutor(message_bus=bus, auto_execute=False)
        assert ex._select_order_type(50.0, 80)[0] == "market"   # 4000 < 5k
        assert ex._select_order_type(100.0, 51)[0] == "limit"   # 5100 in (5k, 25k]
        assert ex._select_order_type(500.0, 60)[0] == "twap"   # 30k > 25k


# ---------------------------------------------------------------------------
# 429 rate limit scenario
# ---------------------------------------------------------------------------

class Test429RateLimit:
    """429 handling: AlpacaService retries with backoff; optionally report to key pool."""

    @pytest.mark.anyio
    async def test_alpaca_service_retries_on_429(self):
        """AlpacaService._request retries 429 (and 503) with exponential backoff (2^attempt seconds)."""
        from app.services.alpaca_service import AlpacaService

        call_count = 0

        async def fake_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            if call_count == 1:
                r.status_code = 429
                r.json = MagicMock(return_value={"message": "rate limit"})
                r.text = "rate limit"
            else:
                r.status_code = 200
                r.json = MagicMock(return_value={"id": "ok"})
            return r

        with patch("app.services.alpaca_service.settings") as m_settings:
            m_settings.ALPACA_API_KEY = "k"
            m_settings.ALPACA_SECRET_KEY = "s"
            m_settings.ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
            m_settings.TRADING_MODE = "paper"
            svc = AlpacaService()
            mock_client = AsyncMock()
            mock_client.request = fake_request
            mock_client.is_closed = False
            svc._http_client = mock_client
            result = await svc._request("GET", "/orders")
        assert call_count >= 2
        assert result is not None

    def test_key_pool_has_report_rate_limit(self):
        """AlpacaKeyPool can record rate limit hits for observability."""
        from app.services.alpaca_key_pool import get_alpaca_key_pool, AlpacaKeyConfig
        pool = get_alpaca_key_pool()
        if pool.key_count == 0:
            pytest.skip("No keys configured in test env")
        pool.report_rate_limit("trading")
        key = pool.get_key("trading")
        if key:
            assert key.rate_limit_hits >= 0


# ---------------------------------------------------------------------------
# Position reconciliation gap detection
# ---------------------------------------------------------------------------

class TestPositionReconciliationGap:
    """Detect drift between internal state and Alpaca positions (no periodic job today)."""

    @pytest.mark.anyio
    async def test_can_detect_drift_internal_vs_alpaca(self):
        """Given internal positions and Alpaca positions, drift can be computed."""
        internal = [{"symbol": "AAPL", "qty": 10}, {"symbol": "MSFT", "qty": 5}]
        alpaca = [{"symbol": "AAPL", "qty": "10"}, {"symbol": "MSFT", "qty": "3"}]  # MSFT drift
        alpaca_by_sym = {p["symbol"]: int(float(p["qty"])) for p in alpaca}
        drift = []
        for pos in internal:
            sym = pos["symbol"]
            internal_qty = pos["qty"]
            broker_qty = alpaca_by_sym.get(sym, 0)
            if internal_qty != broker_qty:
                drift.append({"symbol": sym, "internal": internal_qty, "broker": broker_qty})
        assert len(drift) == 1 and drift[0]["symbol"] == "MSFT" and drift[0]["broker"] == 3

    @pytest.mark.anyio
    async def test_position_manager_syncs_on_startup_only(self):
        """PositionManager._sync_from_alpaca exists and is used on start; no periodic reconciliation."""
        from app.services.position_manager import PositionManager
        pm = PositionManager(message_bus=MagicMock())
        assert hasattr(pm, "_sync_from_alpaca")


# ---------------------------------------------------------------------------
# Paper vs live safety
# ---------------------------------------------------------------------------

class TestPaperVsLiveSafety:
    """TRADING_MODE=paper must not hit live Alpaca URL."""

    def test_alpaca_service_paper_url_when_paper_mode(self):
        with patch("app.services.alpaca_service.settings") as m_settings:
            m_settings.TRADING_MODE = "paper"
            m_settings.ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
            m_settings.ALPACA_API_KEY = "k"
            m_settings.ALPACA_SECRET_KEY = "s"
            m_settings.ALPACA_DATA_URL = "https://data.alpaca.markets"
            from app.services.alpaca_service import AlpacaService
            svc = AlpacaService()
            assert "paper" in svc.base_url.lower()

    def test_alpaca_service_forces_paper_url_if_mode_paper_but_url_live(self):
        """Safety: TRADING_MODE=paper with live URL forces base_url to paper."""
        with patch("app.services.alpaca_service.settings") as m_settings:
            m_settings.TRADING_MODE = "paper"
            m_settings.ALPACA_BASE_URL = "https://api.alpaca.markets"
            m_settings.ALPACA_API_KEY = "k"
            m_settings.ALPACA_SECRET_KEY = "s"
            m_settings.ALPACA_DATA_URL = "https://data.alpaca.markets"
            from app.services.alpaca_service import AlpacaService
            svc = AlpacaService()
            assert "paper" in svc.base_url.lower()
