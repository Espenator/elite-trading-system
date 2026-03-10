"""Canonical LLM contract: Brain Service (PC2) as single entrypoint; degraded mode tagged."""

import pytest

from app.services.brain_client import (
    BrainClient,
    get_brain_client,
    _stub_infer_response,
)


@pytest.mark.asyncio
async def test_brain_unreachable_returns_low_confidence_tagged():
    """When brain_service is unreachable, fallback returns low-confidence and is tagged (degraded_mode)."""
    client = BrainClient(host="127.0.0.1", port=59999, enabled=True)
    result = await client.infer("AAPL", "1d", "{}", "unknown", "")
    assert result["confidence"] <= 0.2
    assert result.get("degraded_mode") is True
    assert "error" in result
    assert result.get("risk_flags")


@pytest.mark.asyncio
async def test_brain_disabled_returns_stub_tagged():
    """When BRAIN_ENABLED=false, infer returns stub with degraded_mode and risk_flags."""
    client = BrainClient(enabled=False)
    result = await client.infer("MSFT", "1d", "{}", "unknown", "")
    assert result["confidence"] == 0.1
    assert result.get("degraded_mode") is True
    assert "brain_disabled" in result.get("risk_flags", [])


def test_stub_infer_response_includes_degraded_tag():
    """_stub_infer_response() always includes degraded_mode and risk_flags for observability."""
    stub = _stub_infer_response()
    assert stub["confidence"] == 0.1
    assert stub["degraded_mode"] is True
    assert stub["risk_flags"]
    stub_tag = _stub_infer_response("timeout")
    assert "timeout" in stub_tag["risk_flags"]
