"""Tests for BrightLineEnforcer — constitutional trading limits."""
import pytest
from app.core.alignment.bright_lines import (
    BrightLineEnforcer,
    MAX_POSITION_SIZE_PCT,
    MAX_PORTFOLIO_HEAT_PCT,
    DRAWDOWN_CIRCUIT_BREAKER_PCT,
    CRISIS_HALT_DRAWDOWN_PCT,
    MAX_CORRELATED_EXPOSURE_PCT,
    MAX_LEVERAGE,
    MAX_DAILY_TRADES,
    ViolationType,
)


@pytest.fixture
def enforcer():
    return BrightLineEnforcer()


# --- Passing cases ---

def test_all_checks_pass(enforcer):
    """Normal trade within all limits -> passed=True, no violations."""
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
        correlated_exposure_pct=0.10,
        leverage=1.0,
    )
    assert report.passed is True
    assert len(report.violations) == 0
    assert report.decision.allowed is True


# --- Position size ---

def test_position_size_at_limit(enforcer):
    """Position exactly at limit -> passes (not strict >)."""
    report = enforcer.enforce(
        proposed_position_pct=MAX_POSITION_SIZE_PCT,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
    )
    assert report.passed is True


def test_position_size_over_limit(enforcer):
    """Position 1% over limit -> blocked."""
    report = enforcer.enforce(
        proposed_position_pct=MAX_POSITION_SIZE_PCT + 0.01,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
    )
    assert report.passed is False
    assert ViolationType.POSITION_SIZE in [v.violation_type for v in report.violations]


# --- Portfolio heat ---

def test_portfolio_heat_over_limit(enforcer):
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=MAX_PORTFOLIO_HEAT_PCT + 0.01,
        current_drawdown_pct=0.02,
    )
    assert report.passed is False
    assert ViolationType.PORTFOLIO_HEAT in [v.violation_type for v in report.violations]


# --- Drawdown circuit breaker ---

def test_drawdown_circuit_breaker(enforcer):
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=DRAWDOWN_CIRCUIT_BREAKER_PCT,
    )
    assert report.passed is False
    assert ViolationType.DRAWDOWN_CIRCUIT in [v.violation_type for v in report.violations]


def test_crisis_halt(enforcer):
    """25% drawdown triggers CRISIS_HALT (more severe than circuit breaker)."""
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=CRISIS_HALT_DRAWDOWN_PCT,
    )
    assert report.passed is False
    types = [v.violation_type for v in report.violations]
    assert ViolationType.CRISIS_HALT in types
    assert ViolationType.DRAWDOWN_CIRCUIT in types  # both fire


# --- Correlated exposure ---

def test_correlated_exposure_over_limit(enforcer):
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
        correlated_exposure_pct=MAX_CORRELATED_EXPOSURE_PCT + 0.01,
    )
    assert report.passed is False
    assert ViolationType.CORRELATED_EXPOSURE in [v.violation_type for v in report.violations]


# --- Leverage ---

def test_leverage_over_limit(enforcer):
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
        leverage=MAX_LEVERAGE + 0.1,
    )
    assert report.passed is False
    assert ViolationType.LEVERAGE in [v.violation_type for v in report.violations]


# --- Rapid-fire ---

def test_rapid_fire_blocked(enforcer):
    """Two trades within MIN_TRADE_INTERVAL_SECONDS -> second is blocked."""
    enforcer.record_trade()
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
    )
    assert report.passed is False
    assert ViolationType.RAPID_FIRE in [v.violation_type for v in report.violations]


# --- Daily trade cap ---

def test_daily_trade_cap(enforcer):
    """Exceeding MAX_DAILY_TRADES -> blocked."""
    for _ in range(MAX_DAILY_TRADES):
        enforcer.record_trade()
        enforcer._last_trade_time = None  # bypass rapid-fire for this test
    report = enforcer.enforce(
        proposed_position_pct=0.05,
        current_heat_pct=0.10,
        current_drawdown_pct=0.02,
    )
    assert report.passed is False
    assert ViolationType.DAILY_TRADE_CAP in [v.violation_type for v in report.violations]


# --- Multiple violations ---

def test_multiple_violations_all_reported(enforcer):
    """Bad trade violating 3 limits -> all 3 reported."""
    report = enforcer.enforce(
        proposed_position_pct=0.20,
        current_heat_pct=0.50,
        current_drawdown_pct=0.30,
        leverage=3.0,
    )
    assert report.passed is False
    assert len(report.violations) >= 3
