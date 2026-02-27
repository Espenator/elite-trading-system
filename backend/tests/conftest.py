"""Shared pytest fixtures for Elite Trading System tests."""
import os
import pytest
from httpx import AsyncClient, ASGITransport

# Set test environment variables before importing app
os.environ["TRADING_MODE"] = "paper"
os.environ["ALPACA_API_KEY"] = "test_key"
os.environ["ALPACA_SECRET_KEY"] = "test_secret"

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