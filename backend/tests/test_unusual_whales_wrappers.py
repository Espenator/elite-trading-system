"""Test module-level wrapper functions for Unusual Whales service."""

import pytest


def test_wrapper_functions_importable():
    """Test that all wrapper functions can be imported successfully."""
    from app.services.unusual_whales_service import (
        get_insider_trades,
        get_dark_pool_flow,
        get_options_chain,
        get_institutional_flow,
    )

    # All functions should be importable and callable
    assert callable(get_insider_trades)
    assert callable(get_dark_pool_flow)
    assert callable(get_options_chain)
    assert callable(get_institutional_flow)


@pytest.mark.asyncio
async def test_get_insider_trades_filters_by_symbol():
    """Test get_insider_trades filters results by symbol."""
    from unittest.mock import AsyncMock, patch
    from app.services.unusual_whales_service import get_insider_trades

    mock_data = [
        {"ticker": "AAPL", "trade_type": "buy", "amount": 100000},
        {"ticker": "TSLA", "trade_type": "sell", "amount": 50000},
        {"ticker": "AAPL", "trade_type": "buy", "amount": 25000},
    ]

    with patch("app.services.unusual_whales_service._get_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        mock_service.get_insider_trades = AsyncMock(return_value=mock_data)

        result = await get_insider_trades("AAPL")

        assert len(result) == 2
        assert all(trade["ticker"] == "AAPL" for trade in result)


@pytest.mark.asyncio
async def test_get_dark_pool_flow_returns_single_match():
    """Test get_dark_pool_flow returns first matching entry."""
    from unittest.mock import AsyncMock, patch
    from app.services.unusual_whales_service import get_dark_pool_flow

    mock_data = [
        {"ticker": "AAPL", "volume": 1000000, "price": 150.0},
        {"ticker": "TSLA", "volume": 500000, "price": 250.0},
    ]

    with patch("app.services.unusual_whales_service._get_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        mock_service.get_darkpool_flow = AsyncMock(return_value=mock_data)

        result = await get_dark_pool_flow("AAPL")

        assert result is not None
        assert result["ticker"] == "AAPL"
        assert result["volume"] == 1000000


@pytest.mark.asyncio
async def test_get_options_chain_filters_by_symbol():
    """Test get_options_chain filters flow alerts by symbol."""
    from unittest.mock import AsyncMock, patch
    from app.services.unusual_whales_service import get_options_chain

    mock_data = [
        {"ticker": "AAPL", "strike": 150, "expiry": "2026-04-17"},
        {"ticker": "TSLA", "strike": 250, "expiry": "2026-04-17"},
        {"ticker": "AAPL", "strike": 155, "expiry": "2026-04-17"},
    ]

    with patch("app.services.unusual_whales_service._get_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        mock_service.get_flow_alerts = AsyncMock(return_value=mock_data)

        result = await get_options_chain("AAPL")

        assert len(result) == 2
        assert all(alert["ticker"] == "AAPL" for alert in result)


@pytest.mark.asyncio
async def test_get_institutional_flow_filters_by_symbol():
    """Test get_institutional_flow filters congress trades by symbol."""
    from unittest.mock import AsyncMock, patch
    from app.services.unusual_whales_service import get_institutional_flow

    mock_data = [
        {"ticker": "AAPL", "representative": "John Doe", "transaction_type": "purchase"},
        {"ticker": "TSLA", "representative": "Jane Smith", "transaction_type": "sale"},
    ]

    with patch("app.services.unusual_whales_service._get_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        mock_service.get_congress_trades = AsyncMock(return_value=mock_data)

        result = await get_institutional_flow("AAPL")

        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_wrappers_handle_case_insensitive_symbols():
    """Test wrappers handle case-insensitive symbol matching."""
    from unittest.mock import AsyncMock, patch
    from app.services.unusual_whales_service import get_insider_trades

    mock_data = [
        {"ticker": "aapl", "trade_type": "buy", "amount": 100000},
        {"ticker": "TSLA", "trade_type": "sell", "amount": 50000},
    ]

    with patch("app.services.unusual_whales_service._get_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        mock_service.get_insider_trades = AsyncMock(return_value=mock_data)

        result = await get_insider_trades("AAPL")

        assert len(result) == 1
        assert result[0]["ticker"] == "aapl"


@pytest.mark.asyncio
async def test_get_dark_pool_flow_not_found():
    """Test get_dark_pool_flow returns None when symbol not found."""
    from unittest.mock import AsyncMock, patch
    from app.services.unusual_whales_service import get_dark_pool_flow

    mock_data = [
        {"ticker": "TSLA", "volume": 500000, "price": 250.0},
    ]

    with patch("app.services.unusual_whales_service._get_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        mock_service.get_darkpool_flow = AsyncMock(return_value=mock_data)

        result = await get_dark_pool_flow("AAPL")

        assert result is None


@pytest.mark.asyncio
async def test_wrappers_handle_paginated_response():
    """Test wrappers handle paginated API response format."""
    from unittest.mock import AsyncMock, patch
    from app.services.unusual_whales_service import get_insider_trades

    mock_data = {
        "data": [
            {"ticker": "AAPL", "trade_type": "buy", "amount": 100000},
            {"ticker": "TSLA", "trade_type": "sell", "amount": 50000},
        ],
        "count": 2,
        "page": 1,
    }

    with patch("app.services.unusual_whales_service._get_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        mock_service.get_insider_trades = AsyncMock(return_value=mock_data)

        result = await get_insider_trades("AAPL")

        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_wrappers_handle_empty_response():
    """Test wrappers handle empty responses gracefully."""
    from unittest.mock import AsyncMock, patch
    from app.services.unusual_whales_service import get_insider_trades

    with patch("app.services.unusual_whales_service._get_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        mock_service.get_insider_trades = AsyncMock(return_value=[])

        result = await get_insider_trades("AAPL")

        assert result == []


@pytest.mark.asyncio
async def test_wrappers_handle_exception():
    """Test wrappers handle exceptions gracefully and return empty results."""
    from unittest.mock import AsyncMock, patch
    from app.services.unusual_whales_service import get_insider_trades

    with patch("app.services.unusual_whales_service._get_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        mock_service.get_insider_trades = AsyncMock(side_effect=Exception("API Error"))

        result = await get_insider_trades("AAPL")

        assert result == []

