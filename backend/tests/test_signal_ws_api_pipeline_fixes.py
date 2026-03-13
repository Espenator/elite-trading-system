"""Regression tests for signal/ws/api pipeline fixes."""

from pathlib import Path

from fastapi.routing import APIRoute

from app.core.security import require_auth
from app.services.signal_engine import EventDrivenSignalEngine
from app.websocket_manager import WS_ALLOWED_CHANNELS


def _read(*parts: str) -> str:
    root = Path(__file__).resolve().parents[1]
    return root.joinpath(*parts).read_text(encoding="utf-8")


def _get_route(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def test_signal_engine_threshold_is_50():
    """Signal engine pre-filter must allow CouncilGate regime thresholds."""
    assert EventDrivenSignalEngine.SIGNAL_THRESHOLD == 50


def test_main_uses_signals_channel_not_signal():
    """Main WS bridge must publish to plural channel used by frontend."""
    src = _read("app", "main.py")
    assert 'broadcast_ws("signals", {"type": "new_signal", "signal": signal_data})' in src
    assert 'broadcast_ws("signal", {"type": "new_signal", "signal": signal_data})' not in src


def test_ws_channel_registries_are_synced():
    """Both backend WS channel registries should match and include signal channels."""
    from app.main import _VALID_WS_CHANNELS

    assert "signals" in _VALID_WS_CHANNELS
    assert "signals" in WS_ALLOWED_CHANNELS
    assert "signal" in _VALID_WS_CHANNELS
    assert "signal" in WS_ALLOWED_CHANNELS
    assert _VALID_WS_CHANNELS == frozenset(WS_ALLOWED_CHANNELS)


def test_dlq_endpoints_require_auth():
    """State-changing DLQ routes must include auth dependency."""
    from app.api.v1 import system

    replay = _get_route(system.router, "/dlq/replay", "POST")
    clear = _get_route(system.router, "/dlq", "DELETE")
    replay_deps = [dep.call for dep in replay.dependant.dependencies]
    clear_deps = [dep.call for dep in clear.dependant.dependencies]
    assert require_auth in replay_deps
    assert require_auth in clear_deps


def test_metrics_ws_reset_requires_auth():
    """WS circuit-breaker reset endpoint must include auth dependency."""
    from app.api.v1 import metrics_api

    reset = _get_route(metrics_api.router, "/api/v1/metrics/ws-circuit-breaker/reset", "POST")
    deps = [dep.call for dep in reset.dependant.dependencies]
    assert require_auth in deps
