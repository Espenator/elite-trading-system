"""Shared pytest fixtures for Embodier Trader tests."""
import os
import pytest
from httpx import AsyncClient, ASGITransport

# Set test environment variables before importing app
os.environ["TRADING_MODE"] = "paper"
os.environ["ALPACA_API_KEY"] = "test_key"
os.environ["ALPACA_SECRET_KEY"] = "test_secret"
os.environ["API_AUTH_TOKEN"] = "test_auth_token_for_tests"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_testing_only"
os.environ["ALPACA_SIGNATURE_SECRET"] = "test_signature_secret_for_testing"

from app.main import app  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Auth headers for state-changing endpoint tests."""
    return {"Authorization": "Bearer test_auth_token_for_tests"}



@pytest.fixture
def kelly_sizer():
    """Pre-configured Kelly sizer for tests."""
    from app.services.kelly_position_sizer import KellyPositionSizer
    return KellyPositionSizer()


@pytest.fixture
def sample_signal():
    """Sample signal with Kelly fields for testing."""
    return {
        "symbol": "AAPL",
        "prob_up": 0.72,
        "action": "BUY",
        "kelly_edge": 0.08,
        "signal_quality": 0.85,
        "kelly_fraction": 0.05,
        "composite_score": 78,
        "expected_value": 0.012,
    }


@pytest.fixture
def risk_config():
    """Risk configuration for tests."""
    return {
        "maxDailyDrawdown": 5.0,
        "maxDailyLossPct": 2.0,
        "autoPauseTrading": True,
        "varLimit": 1.5,
    }


@pytest.fixture
def mock_positions():
    """Sample portfolio positions for risk tests."""
    return [
        {"symbol": "AAPL", "market_value": "15000", "unrealized_pl": "450", "qty": "100"},
        {"symbol": "MSFT", "market_value": "12000", "unrealized_pl": "-200", "qty": "80"},
        {"symbol": "GOOGL", "market_value": "8000", "unrealized_pl": "300", "qty": "10"},
    ]