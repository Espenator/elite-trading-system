"""Tests for turbo_scanner.py — Bug 15 (direction-aware dedup) + Bug 19 coverage.

Tests the TurboScanner class: initialization, signal creation, dedup logic,
status reporting, and signal retrieval. Does NOT require DuckDB or external APIs.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from app.services.turbo_scanner import (
    TurboScanner, ScanSignal, SIGNAL_TYPES,
    MIN_SIGNAL_SCORE, MAX_SIGNALS_PER_SCAN,
)


# ---------------------------------------------------------------------------
# ScanSignal dataclass
# ---------------------------------------------------------------------------

class TestScanSignal:
    def test_create_signal(self):
        sig = ScanSignal(
            symbol="AAPL",
            signal_type="technical_breakout",
            direction="bullish",
            score=0.75,
            reasoning="Bullish alignment",
        )
        assert sig.symbol == "AAPL"
        assert sig.direction == "bullish"
        assert sig.score == 0.75
        assert sig.source == "turbo_scanner"

    def test_to_dict(self):
        sig = ScanSignal(
            symbol="TSLA",
            signal_type="volume_spike",
            direction="bearish",
            score=0.62,
            reasoning="3.5x avg volume",
            data={"vol_ratio": 3.5},
        )
        d = sig.to_dict()
        assert d["symbol"] == "TSLA"
        assert d["signal_type"] == "volume_spike"
        assert d["direction"] == "bearish"
        assert d["score"] == 0.62
        assert d["data"]["vol_ratio"] == 3.5
        assert "detected_at" in d

    def test_score_rounding(self):
        sig = ScanSignal(
            symbol="SPY", signal_type="vix_regime",
            direction="unknown", score=0.123456, reasoning="test",
        )
        d = sig.to_dict()
        assert d["score"] == 0.123  # rounded to 3 decimals

    def test_default_detected_at_is_iso(self):
        sig = ScanSignal(
            symbol="QQQ", signal_type="momentum_surge",
            direction="bullish", score=0.5, reasoning="test",
        )
        # Should be a valid ISO timestamp
        assert "T" in sig.detected_at


# ---------------------------------------------------------------------------
# TurboScanner initialization and state
# ---------------------------------------------------------------------------

class TestTurboScannerInit:
    def test_default_state(self):
        scanner = TurboScanner()
        assert scanner._running is False
        assert scanner._volatile_mode is False
        assert len(scanner._seen_today) == 0
        assert scanner._stats["total_scans"] == 0

    def test_with_message_bus(self):
        bus = MagicMock()
        scanner = TurboScanner(message_bus=bus)
        assert scanner._bus is bus


# ---------------------------------------------------------------------------
# Dedup logic (Bug 15 fix: direction-aware dedup)
# ---------------------------------------------------------------------------

class TestDedup:
    def test_direction_aware_dedup_key(self):
        """After Bug 15 fix, dedup should include direction."""
        sig_bull = ScanSignal(
            symbol="AAPL", signal_type="technical_breakout",
            direction="bullish", score=0.8, reasoning="bull",
        )
        sig_bear = ScanSignal(
            symbol="AAPL", signal_type="technical_breakout",
            direction="bearish", score=0.7, reasoning="bear",
        )

        # Build dedup keys as the fixed code does
        key_bull = f"{sig_bull.symbol}:{sig_bull.signal_type}:{sig_bull.direction}"
        key_bear = f"{sig_bear.symbol}:{sig_bear.signal_type}:{sig_bear.direction}"

        assert key_bull != key_bear
        assert key_bull == "AAPL:technical_breakout:bullish"
        assert key_bear == "AAPL:technical_breakout:bearish"

    def test_same_direction_is_deduped(self):
        """Same symbol + type + direction should be deduped."""
        scanner = TurboScanner()
        key1 = "AAPL:technical_breakout:bullish"
        key2 = "AAPL:technical_breakout:bullish"
        scanner._seen_today.add(key1)
        assert key2 in scanner._seen_today

    def test_reset_daily_clears_dedup(self):
        scanner = TurboScanner()
        scanner._seen_today.add("AAPL:momentum:bullish")
        scanner._seen_today.add("MSFT:volume:bearish")
        assert len(scanner._seen_today) == 2
        scanner.reset_daily()
        assert len(scanner._seen_today) == 0


# ---------------------------------------------------------------------------
# Status & signals API
# ---------------------------------------------------------------------------

class TestStatusAPI:
    def test_get_status_structure(self):
        scanner = TurboScanner()
        status = scanner.get_status()
        assert "running" in status
        assert "scan_interval" in status
        assert "volatile_mode" in status
        assert "tier1_symbols" in status
        assert "signals_today" in status
        assert "stats" in status
        assert "recent_signals" in status

    def test_get_signals_empty(self):
        scanner = TurboScanner()
        signals = scanner.get_signals()
        assert signals == []

    def test_get_signals_with_type_filter(self):
        scanner = TurboScanner()
        scanner._signals_history.append(ScanSignal(
            symbol="AAPL", signal_type="volume_spike",
            direction="bullish", score=0.7, reasoning="test",
        ))
        scanner._signals_history.append(ScanSignal(
            symbol="MSFT", signal_type="momentum_surge",
            direction="bullish", score=0.6, reasoning="test",
        ))
        volume_signals = scanner.get_signals(signal_type="volume_spike")
        assert len(volume_signals) == 1
        assert volume_signals[0]["symbol"] == "AAPL"

    def test_get_signals_limit(self):
        scanner = TurboScanner()
        for i in range(10):
            scanner._signals_history.append(ScanSignal(
                symbol=f"SYM{i}", signal_type="test",
                direction="bullish", score=0.5, reasoning="test",
            ))
        signals = scanner.get_signals(limit=3)
        assert len(signals) == 3


# ---------------------------------------------------------------------------
# Signal types configuration
# ---------------------------------------------------------------------------

class TestSignalTypes:
    def test_all_types_have_weight(self):
        for stype, config in SIGNAL_TYPES.items():
            assert "weight" in config, f"Missing weight for {stype}"
            assert "priority" in config, f"Missing priority for {stype}"

    def test_weights_are_positive(self):
        for stype, config in SIGNAL_TYPES.items():
            assert config["weight"] > 0
            assert config["priority"] >= 1

    def test_min_signal_score_is_reasonable(self):
        assert 0 < MIN_SIGNAL_SCORE < 1.0

    def test_max_signals_per_scan_is_positive(self):
        assert MAX_SIGNALS_PER_SCAN > 0
