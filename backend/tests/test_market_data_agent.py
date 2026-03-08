"""Tests for market_data_agent supervisor refactor.

Validates:
1. run_tick() uses alpaca_service.get_clock() instead of raw HTTP
2. run_ingestion defaults to False (bars handled by AlpacaStreamManager)
3. run_tick() returns well-formed (message, level) tuples
4. Each source flag correctly gates its delegate call
"""
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Signature / default tests
# ---------------------------------------------------------------------------

class TestRunTickDefaults:
    def test_run_ingestion_default_is_false(self):
        """run_ingestion must default to False — bars handled by AlpacaStreamManager."""
        from app.services.market_data_agent import run_tick
        sig = inspect.signature(run_tick)
        assert sig.parameters["run_ingestion"].default is False, (
            "run_ingestion must default to False; "
            "bar persistence is delegated to AlpacaStreamManager"
        )

    def test_all_source_flags_default_true(self):
        """All source-enable flags should default to True."""
        from app.services.market_data_agent import run_tick
        sig = inspect.signature(run_tick)
        for flag in ("run_finviz", "run_alpaca", "run_fred", "run_edgar",
                     "run_unusual_whales", "run_openclaw"):
            assert sig.parameters[flag].default is True, (
                f"{flag} must default to True"
            )

    def test_agent_name_constant_exists(self):
        from app.services import market_data_agent
        assert market_data_agent.AGENT_NAME == "Market Data Agent"


# ---------------------------------------------------------------------------
# Alpaca: uses get_clock(), not raw HTTP
# ---------------------------------------------------------------------------

class TestAlpacaClockDelegation:
    @pytest.mark.anyio
    async def test_uses_get_clock_not_raw_http(self):
        """Alpaca block must call alpaca_service.get_clock(), not build a raw URL."""
        mock_alpaca_svc = MagicMock()
        mock_alpaca_svc.get_clock = AsyncMock(return_value={"is_open": True})

        with patch.dict("sys.modules", {
            "app.services.alpaca_service": MagicMock(alpaca_service=mock_alpaca_svc)
        }):
            from app.services import market_data_agent
            entries = await market_data_agent.run_tick(
                run_finviz=False,
                run_alpaca=True,
                run_fred=False,
                run_edgar=False,
                run_unusual_whales=False,
                run_openclaw=False,
                run_ingestion=False,
            )

        mock_alpaca_svc.get_clock.assert_called_once()
        assert any("Alpaca" in msg for msg, _ in entries)

    @pytest.mark.anyio
    async def test_alpaca_market_open_reported(self):
        """market_open=True surfaces in the log entry when clock says open."""
        mock_alpaca_svc = MagicMock()
        mock_alpaca_svc.get_clock = AsyncMock(return_value={"is_open": True})

        with patch.dict("sys.modules", {
            "app.services.alpaca_service": MagicMock(alpaca_service=mock_alpaca_svc)
        }):
            from app.services import market_data_agent
            entries = await market_data_agent.run_tick(
                run_finviz=False, run_alpaca=True, run_fred=False,
                run_edgar=False, run_unusual_whales=False,
                run_openclaw=False, run_ingestion=False,
            )

        messages = [msg for msg, _ in entries]
        assert any("market_open=True" in m for m in messages)

    @pytest.mark.anyio
    async def test_alpaca_market_closed_reported(self):
        """market_open=False surfaces in the log entry when clock says closed."""
        mock_alpaca_svc = MagicMock()
        mock_alpaca_svc.get_clock = AsyncMock(return_value={"is_open": False})

        with patch.dict("sys.modules", {
            "app.services.alpaca_service": MagicMock(alpaca_service=mock_alpaca_svc)
        }):
            from app.services import market_data_agent
            entries = await market_data_agent.run_tick(
                run_finviz=False, run_alpaca=True, run_fred=False,
                run_edgar=False, run_unusual_whales=False,
                run_openclaw=False, run_ingestion=False,
            )

        messages = [msg for msg, _ in entries]
        assert any("market_open=False" in m for m in messages)

    @pytest.mark.anyio
    async def test_alpaca_none_response_is_warning(self):
        """get_clock returning None should produce a warning entry, not an exception."""
        mock_alpaca_svc = MagicMock()
        mock_alpaca_svc.get_clock = AsyncMock(return_value=None)

        with patch.dict("sys.modules", {
            "app.services.alpaca_service": MagicMock(alpaca_service=mock_alpaca_svc)
        }):
            from app.services import market_data_agent
            entries = await market_data_agent.run_tick(
                run_finviz=False, run_alpaca=True, run_fred=False,
                run_edgar=False, run_unusual_whales=False,
                run_openclaw=False, run_ingestion=False,
            )

        levels = [lvl for _, lvl in entries]
        assert "warning" in levels

    @pytest.mark.anyio
    async def test_alpaca_exception_is_warning(self):
        """An exception from get_clock should be caught and returned as a warning entry."""
        mock_alpaca_svc = MagicMock()
        mock_alpaca_svc.get_clock = AsyncMock(side_effect=RuntimeError("timeout"))

        with patch.dict("sys.modules", {
            "app.services.alpaca_service": MagicMock(alpaca_service=mock_alpaca_svc)
        }):
            from app.services import market_data_agent
            entries = await market_data_agent.run_tick(
                run_finviz=False, run_alpaca=True, run_fred=False,
                run_edgar=False, run_unusual_whales=False,
                run_openclaw=False, run_ingestion=False,
            )

        assert entries  # must return something, not propagate
        levels = [lvl for _, lvl in entries]
        assert "warning" in levels


# ---------------------------------------------------------------------------
# Source gates
# ---------------------------------------------------------------------------

class TestSourceGates:
    @pytest.mark.anyio
    async def test_all_disabled_returns_empty(self):
        """When every flag is False, run_tick returns an empty list."""
        from app.services import market_data_agent
        entries = await market_data_agent.run_tick(
            run_finviz=False, run_alpaca=False, run_fred=False,
            run_edgar=False, run_unusual_whales=False,
            run_openclaw=False, run_ingestion=False,
        )
        assert entries == []

    @pytest.mark.anyio
    async def test_ingestion_skipped_when_false(self):
        """_run_ingestion must NOT be called when run_ingestion=False."""
        with patch("app.services.market_data_agent._run_ingestion",
                   new_callable=AsyncMock) as mock_ingest:
            from app.services import market_data_agent
            await market_data_agent.run_tick(
                run_finviz=False, run_alpaca=False, run_fred=False,
                run_edgar=False, run_unusual_whales=False,
                run_openclaw=False, run_ingestion=False,
            )
        mock_ingest.assert_not_called()

    @pytest.mark.anyio
    async def test_ingestion_called_when_true(self):
        """_run_ingestion must be called when run_ingestion=True."""
        with patch("app.services.market_data_agent._run_ingestion",
                   new_callable=AsyncMock,
                   return_value=[("DuckDB ingestion: 0 OHLCV", "success")]) as mock_ingest:
            from app.services import market_data_agent
            await market_data_agent.run_tick(
                run_finviz=False, run_alpaca=False, run_fred=False,
                run_edgar=False, run_unusual_whales=False,
                run_openclaw=False, run_ingestion=True,
            )
        mock_ingest.assert_called_once()


# ---------------------------------------------------------------------------
# Return-value contract
# ---------------------------------------------------------------------------

class TestReturnContract:
    @pytest.mark.anyio
    async def test_returns_list_of_tuples(self):
        """run_tick must always return a list of (str, str) tuples."""
        mock_alpaca_svc = MagicMock()
        mock_alpaca_svc.get_clock = AsyncMock(return_value={"is_open": False})

        with patch.dict("sys.modules", {
            "app.services.alpaca_service": MagicMock(alpaca_service=mock_alpaca_svc)
        }):
            from app.services import market_data_agent
            result = await market_data_agent.run_tick(
                run_finviz=False, run_alpaca=True, run_fred=False,
                run_edgar=False, run_unusual_whales=False,
                run_openclaw=False, run_ingestion=False,
            )

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, tuple) and len(item) == 2
            msg, level = item
            assert isinstance(msg, str)
            assert isinstance(level, str)
