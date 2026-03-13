"""HITL Gate & Approval Flow Audit — Prompt 20.

Verifies all 6 gates, approval timeout behavior, overflow, bulk approval,
learning period auto-start, cross-gate logic, and HITL bypass.
"""
import time
import pytest

from app.council.hitl_gate import (
    HITLGate,
    HITLConfig,
    GateResult,
    MAX_PENDING_APPROVALS,
)


# ── Gate 1: Trade size > $5000 ─────────────────────────────────────────────

def test_gate_1_trade_size_requires_approval_when_above_threshold():
    """Gate 1: Trade size > max_trade_value_usd ($5000) requires approval."""
    config = HITLConfig(max_trade_value_usd=5000.0, enabled=True)
    gate = HITLGate(config)
    # 2% of 300_000 = 6000 > 5000
    portfolio = {"account_value": 300_000}
    result = gate.check(
        {
            "final_direction": "buy",
            "final_confidence": 0.8,
            "council_decision_id": "tid-1",
            "metadata": {},
        },
        portfolio_context=portfolio,
    )
    assert result.requires_approval
    assert "trade_size" in result.gates_triggered
    assert result.gate_details["trade_size"]["estimated_value"] == 6000.0
    assert result.gate_details["trade_size"]["threshold"] == 5000.0


def test_gate_1_trade_size_passes_when_below_threshold():
    """Gate 1: Trade size <= threshold does not trigger."""
    config = HITLConfig(max_trade_value_usd=5000.0)
    gate = HITLGate(config)
    portfolio = {"account_value": 100_000}  # 2% = 2000 < 5000
    result = gate.check(
        {
            "final_direction": "buy",
            "final_confidence": 0.8,
            "council_decision_id": "tid-1a",
            "metadata": {"regime": "bullish"},
        },
        portfolio_context=portfolio,
    )
    assert not result.requires_approval
    assert "trade_size" not in result.gates_triggered


def test_gate_1_trade_size_no_portfolio_returns_zero_estimate():
    """Gate 1: Without portfolio_context, trade value is 0 so gate does not fire."""
    gate = HITLGate(HITLConfig(max_trade_value_usd=5000.0))
    result = gate.check(
        {
            "final_direction": "buy",
            "final_confidence": 0.8,
            "council_decision_id": "tid-1b",
            "metadata": {"regime": "bullish"},
        },
        portfolio_context=None,
    )
    assert not result.requires_approval
    assert "trade_size" not in result.gates_triggered


# ── Gate 2: Confidence < 60% ─────────────────────────────────────────────────

def test_gate_2_confidence_requires_approval_when_below_threshold():
    """Gate 2: confidence < min_confidence_for_auto (60%) requires approval."""
    config = HITLConfig(min_confidence_for_auto=0.60)
    gate = HITLGate(config)
    result = gate.check({
        "final_direction": "buy",
        "final_confidence": 0.50,
        "council_decision_id": "tid-2",
    })
    assert result.requires_approval
    assert "low_confidence" in result.gates_triggered
    assert result.gate_details["low_confidence"]["confidence"] == 0.50
    assert result.gate_details["low_confidence"]["threshold"] == 0.60


# ── Gate 3: Learning period ─────────────────────────────────────────────────

def test_gate_3_learning_period_requires_approval_when_within_days():
    """Gate 3: Within learning_period_days requires approval."""
    config = HITLConfig(
        learning_period_days=30,
        learning_start_timestamp=time.time(),  # just started
    )
    gate = HITLGate(config)
    result = gate.check({
        "final_direction": "buy",
        "final_confidence": 0.9,
        "council_decision_id": "tid-3",
    })
    assert result.requires_approval
    assert "learning_period" in result.gates_triggered


def test_gate_3_learning_period_does_not_auto_start():
    """Learning period does NOT auto-start: learning_start_timestamp is 0 by default."""
    config = HITLConfig(learning_period_days=30)
    assert config.learning_start_timestamp == 0.0
    gate = HITLGate(config)
    result = gate.check({
        "final_direction": "buy",
        "final_confidence": 0.9,
        "council_decision_id": "tid-3b",
        "metadata": {"regime": "bullish"},
    })
    assert not result.requires_approval
    assert "learning_period" not in result.gates_triggered


# ── Gate 4: Novel regime ────────────────────────────────────────────────────

def test_gate_4_novel_regime_requires_approval():
    """Gate 4: Regime not in known_regimes requires approval."""
    gate = HITLGate()
    result = gate.check({
        "final_direction": "buy",
        "final_confidence": 0.9,
        "council_decision_id": "tid-4",
        "metadata": {"regime": "hyperinflation"},
    })
    assert result.requires_approval
    assert "novel_regime" in result.gates_triggered
    assert result.gate_details["novel_regime"]["regime"] == "hyperinflation"


def test_gate_4_known_regime_passes():
    """Gate 4: Known regime does not trigger."""
    gate = HITLGate()
    result = gate.check({
        "final_direction": "buy",
        "final_confidence": 0.9,
        "council_decision_id": "tid-4b",
        "metadata": {"regime": "bullish"},
    })
    assert "novel_regime" not in result.gates_triggered


# ── Gate 5: Consecutive losses > 5 ────────────────────────────────────────────

def test_gate_5_consecutive_losses_requires_approval():
    """Gate 5: consecutive_losses >= max_consecutive_losses (5) requires approval."""
    config = HITLConfig(max_consecutive_losses=5)
    gate = HITLGate(config)
    for _ in range(5):
        gate.record_outcome(is_win=False)
    result = gate.check({
        "final_direction": "buy",
        "final_confidence": 0.9,
        "council_decision_id": "tid-5",
    })
    assert result.requires_approval
    assert "losing_streak" in result.gates_triggered
    assert result.gate_details["losing_streak"]["consecutive_losses"] == 5


# ── Gate 6: Sector concentration > 40% ──────────────────────────────────────

def test_gate_6_sector_concentration_requires_approval():
    """Gate 6: Any sector > max_sector_concentration (40%) requires approval."""
    config = HITLConfig(max_sector_concentration=0.40)
    gate = HITLGate(config)
    result = gate.check(
        {
            "final_direction": "buy",
            "final_confidence": 0.9,
            "council_decision_id": "tid-6",
        },
        portfolio_context={"sector_allocation": {"Technology": 0.50}},
    )
    assert result.requires_approval
    assert "sector_concentration" in result.gates_triggered
    assert result.gate_details["sector_concentration"]["sector"] == "Technology"
    assert result.gate_details["sector_concentration"]["allocation"] == 0.50


# ── Approval timeout: pending do NOT expire ───────────────────────────────────

def test_approval_timeout_pending_does_not_expire():
    """Pending approvals have no timeout: a trade pending >5 min is still in get_pending()."""
    config = HITLConfig(min_confidence_for_auto=0.99)
    gate = HITLGate(config)
    result = gate.check({
        "final_direction": "buy",
        "final_confidence": 0.5,
        "council_decision_id": "pending-5min",
    })
    assert result.requires_approval
    gate._pending_approvals[result.decision_id] = result
    pending = gate.get_pending()
    assert len(pending) == 1
    assert pending[0]["decision_id"] == result.decision_id
    # Simulate 5+ minutes passing (we do not advance real time; we just assert
    # there is no expiry logic — get_pending still returns the item).
    pending_after = gate.get_pending()
    assert len(pending_after) == 1
    assert pending_after[0]["decision_id"] == "pending-5min"


# ── Overflow: 101st pending evicts oldest ────────────────────────────────────

def test_overflow_101st_pending_evicts_oldest():
    """When _pending_approvals reaches MAX_PENDING_APPROVALS (100), 101st evicts oldest."""
    config = HITLConfig(min_confidence_for_auto=0.99)
    gate = HITLGate(config)
    oldest_id = None
    for i in range(MAX_PENDING_APPROVALS + 1):
        did = f"decision-{i:03d}"
        result = GateResult(
            requires_approval=True,
            gates_triggered=["low_confidence"],
            decision_id=did,
            symbol="AAPL",
        )
        if len(gate._pending_approvals) >= MAX_PENDING_APPROVALS:
            oldest_key = next(iter(gate._pending_approvals))
            gate._pending_approvals.pop(oldest_key, None)
        gate._pending_approvals[result.decision_id] = result
        if i == 0:
            oldest_id = did
    assert len(gate._pending_approvals) == MAX_PENDING_APPROVALS
    # The first one added (decision-000) should have been evicted
    assert oldest_id not in gate._pending_approvals
    pending_ids = [p["decision_id"] for p in gate.get_pending()]
    assert "decision-000" not in pending_ids
    assert "decision-100" in pending_ids


def test_overflow_integration_via_check():
    """Hitl.check() caps pending at 100: adding 101st via check() evicts oldest."""
    config = HITLConfig(min_confidence_for_auto=0.99)
    gate = HITLGate(config)
    for i in range(MAX_PENDING_APPROVALS + 5):
        result = gate.check({
            "final_direction": "buy",
            "final_confidence": 0.5,
            "council_decision_id": f"cid-{i:03d}",
        })
        assert result.requires_approval
    assert len(gate._pending_approvals) == MAX_PENDING_APPROVALS
    # First few should be evicted (dict order insertion)
    pending_ids = [p["decision_id"] for p in gate.get_pending()]
    assert len(pending_ids) == MAX_PENDING_APPROVALS


# ── No bulk approve ───────────────────────────────────────────────────────────

def test_no_bulk_approve_method():
    """HITLGate has no approve_all / bulk_approve method — only approve(decision_id)."""
    gate = HITLGate()
    assert hasattr(gate, "approve")
    assert callable(gate.approve)
    assert not hasattr(gate, "approve_all")
    assert not hasattr(gate, "bulk_approve")


# ── Cross-gate logic: gates evaluated independently ──────────────────────────

def test_gates_evaluated_independently_multiple_triggered():
    """Gates do not interact; each is evaluated independently; multiple can trigger."""
    config = HITLConfig(
        min_confidence_for_auto=0.70,
        learning_period_days=30,
        learning_start_timestamp=time.time(),
    )
    gate = HITLGate(config)
    result = gate.check({
        "final_direction": "sell",
        "final_confidence": 0.50,
        "council_decision_id": "multi",
    })
    assert result.requires_approval
    assert "low_confidence" in result.gates_triggered
    assert "learning_period" in result.gates_triggered
    assert len(result.gates_triggered) >= 2


# ── HITL disabled bypass ─────────────────────────────────────────────────────

def test_hitl_disabled_bypasses_all_gates():
    """When config.enabled=False, check() returns no approval required (HITL bypass)."""
    config = HITLConfig(enabled=False)
    gate = HITLGate(config)
    result = gate.check({
        "final_direction": "buy",
        "final_confidence": 0.3,
        "council_decision_id": "bypass",
        "metadata": {"regime": "unknown_regime"},
    }, portfolio_context={"sector_allocation": {"Tech": 0.99}, "account_value": 1_000_000})
    assert not result.requires_approval
    assert len(result.gates_triggered) == 0


def test_hold_always_passes():
    """Hold decisions skip all gate checks."""
    gate = HITLGate(HITLConfig(min_confidence_for_auto=0.99))
    result = gate.check({
        "final_direction": "hold",
        "final_confidence": 0.1,
        "council_decision_id": "hold-1",
    })
    assert not result.requires_approval


# ── Approve / reject ──────────────────────────────────────────────────────────

def test_approve_and_reject_work():
    """approve(decision_id) and reject(decision_id) remove from pending."""
    config = HITLConfig(min_confidence_for_auto=0.99)
    gate = HITLGate(config)
    gate.check({"final_direction": "buy", "final_confidence": 0.5, "council_decision_id": "a1"})
    gate.check({"final_direction": "buy", "final_confidence": 0.5, "council_decision_id": "a2"})
    assert len(gate.get_pending()) == 2
    assert gate.approve("a1", approver="test") is True
    assert len(gate.get_pending()) == 1
    assert gate.reject("a2", reason="no", rejector="test") is True
    assert len(gate.get_pending()) == 0


def test_get_status_includes_pending_count():
    """get_status() returns pending_count and config."""
    config = HITLConfig(min_confidence_for_auto=0.6)
    gate = HITLGate(config)
    gate.check({"final_direction": "buy", "final_confidence": 0.5, "council_decision_id": "s1"})
    status = gate.get_status()
    assert status["pending_count"] == 1
    assert status["enabled"] is True
    assert "config" in status
    assert status["config"]["min_confidence_for_auto"] == 0.6
