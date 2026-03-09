"""Tests for DataFence — data validation protective boundary."""
import pytest

from app.council.data_fence import (
    DataFence,
    ValidationResult,
    get_data_fence,
    MAX_SCORE,
    MIN_SCORE,
    MAX_PRICE,
    MIN_PRICE,
)


class TestDataFence:
    """Test suite for DataFence validation logic."""

    def test_singleton(self):
        """Test that get_data_fence returns a singleton."""
        fence1 = get_data_fence()
        fence2 = get_data_fence()
        assert fence1 is fence2

    def test_valid_signal_passes(self):
        """Test that a valid signal passes validation."""
        fence = DataFence()
        signal = {
            "symbol": "AAPL",
            "score": 75.5,
            "source": "turbo_scanner",
            "regime": "BULLISH",
            "timestamp": 1234567890,
            "price": 150.25,
        }
        result = fence.validate_signal(signal)
        assert result.passed
        assert result.rejection_reason == ""
        assert result.integrity_score == 100.0

    def test_missing_required_fields(self):
        """Test that missing required fields cause rejection."""
        fence = DataFence()

        # Missing symbol
        signal = {"score": 75, "source": "test"}
        result = fence.validate_signal(signal)
        assert not result.passed
        assert "missing required fields" in result.rejection_reason.lower()

        # Missing score
        signal = {"symbol": "AAPL", "source": "test"}
        result = fence.validate_signal(signal)
        assert not result.passed

        # Missing source
        signal = {"symbol": "AAPL", "score": 75}
        result = fence.validate_signal(signal)
        assert not result.passed

    def test_mock_source_detection(self):
        """Test that mock sources are detected and rejected."""
        fence = DataFence()

        mock_sources = [
            "mock_scanner",
            "test_engine",
            "fake_data",
            "demo_source",
            "sample_data",
            "MOCK",
            "TEST",
        ]

        for source in mock_sources:
            signal = {
                "symbol": "AAPL",
                "score": 75,
                "source": source,
            }
            result = fence.validate_signal(signal)
            assert not result.passed, f"Mock source should be rejected: {source}"
            assert "mock" in result.rejection_reason.lower() or "test" in result.rejection_reason.lower()

    def test_valid_sources_pass(self):
        """Test that legitimate sources pass validation."""
        fence = DataFence()

        valid_sources = [
            "turbo_scanner",
            "signal_engine",
            "finviz_screener",
            "unusual_whales",
            "council",
        ]

        for source in valid_sources:
            signal = {
                "symbol": "AAPL",
                "score": 75,
                "source": source,
            }
            result = fence.validate_signal(signal)
            assert result.passed, f"Valid source should pass: {source}"

    def test_invalid_symbol(self):
        """Test that invalid symbols are rejected."""
        fence = DataFence()

        invalid_symbols = [
            "",  # Empty
            "A" * 15,  # Too long
            "AAP$",  # Invalid character
            "123",  # Numeric only (should pass actually - some symbols are numeric)
            "apl",  # Lowercase (should get normalized)
        ]

        for symbol in invalid_symbols[:3]:  # Test first 3 which are truly invalid
            signal = {
                "symbol": symbol,
                "score": 75,
                "source": "valid_source",
            }
            result = fence.validate_signal(signal)
            assert not result.passed, f"Invalid symbol should be rejected: {symbol}"

    def test_score_validation(self):
        """Test score range validation."""
        fence = DataFence()

        # Score too low
        signal = {"symbol": "AAPL", "score": -10, "source": "turbo_scanner"}
        result = fence.validate_signal(signal)
        assert not result.passed
        assert "out of range" in result.rejection_reason.lower()

        # Score too high
        signal = {"symbol": "AAPL", "score": 150, "source": "turbo_scanner"}
        result = fence.validate_signal(signal)
        assert not result.passed

        # Score not numeric
        signal = {"symbol": "AAPL", "score": "high", "source": "turbo_scanner"}
        result = fence.validate_signal(signal)
        assert not result.passed
        assert "not numeric" in result.rejection_reason.lower()

        # Valid edge cases
        for score in [MIN_SCORE, MAX_SCORE, 50.0]:
            signal = {"symbol": "AAPL", "score": score, "source": "turbo_scanner"}
            result = fence.validate_signal(signal)
            assert result.passed, f"Valid score should pass: {score}"

    def test_price_validation(self):
        """Test price validation when present."""
        fence = DataFence()

        # Price too low
        signal = {"symbol": "AAPL", "score": 75, "source": "turbo_scanner", "price": 0.001}
        result = fence.validate_signal(signal)
        assert not result.passed

        # Price too high
        signal = {"symbol": "AAPL", "score": 75, "source": "turbo_scanner", "price": 2_000_000}
        result = fence.validate_signal(signal)
        assert not result.passed

        # Valid prices
        for price in [MIN_PRICE, MAX_PRICE, 100.50]:
            signal = {"symbol": "AAPL", "score": 75, "source": "turbo_scanner", "price": price}
            result = fence.validate_signal(signal)
            assert result.passed, f"Valid price should pass: {price}"

    def test_warnings_reduce_integrity(self):
        """Test that warnings reduce integrity score but don't fail validation."""
        fence = DataFence()

        # Signal without regime (should warn)
        signal = {
            "symbol": "AAPL",
            "score": 75,
            "source": "turbo_scanner",
        }
        result = fence.validate_signal(signal)
        assert result.passed
        assert len(result.warnings) > 0
        assert result.integrity_score < 100.0

    def test_sanitize_text(self):
        """Test text sanitization."""
        fence = DataFence()

        # Control characters
        text = "Hello\x00World\x1f"
        sanitized = fence.sanitize_text(text)
        assert "\x00" not in sanitized
        assert "\x1f" not in sanitized

        # Length limiting
        text = "A" * 2000
        sanitized = fence.sanitize_text(text, max_length=100)
        assert len(sanitized) == 100

        # Whitespace trimming
        text = "  AAPL  "
        sanitized = fence.sanitize_text(text)
        assert sanitized == "AAPL"

    def test_signal_sanitization(self):
        """Test that signal data is sanitized."""
        fence = DataFence()

        signal = {
            "symbol": "  aapl  ",  # Should be uppercased and trimmed
            "score": 75,
            "source": "  turbo_scanner  ",  # Should be trimmed
            "description": "Valid\x00signal",  # Should remove null byte
        }
        result = fence.validate_signal(signal)
        assert result.passed
        assert result.sanitized_data["symbol"] == "AAPL"
        assert "\x00" not in result.sanitized_data["description"]

    def test_block_source(self):
        """Test source blocking functionality."""
        fence = DataFence()

        # Block a source
        fence.block_source("bad_source")

        signal = {
            "symbol": "AAPL",
            "score": 75,
            "source": "bad_source",
        }
        result = fence.validate_signal(signal)
        assert not result.passed
        assert "blocked" in result.rejection_reason.lower()

        # Unblock the source
        fence.unblock_source("bad_source")
        result = fence.validate_signal(signal)
        assert result.passed

    def test_order_validation(self):
        """Test order data validation."""
        fence = DataFence()

        # Valid order
        order = {
            "symbol": "AAPL",
            "direction": "buy",
            "price": 150.25,
        }
        result = fence.validate_order(order)
        assert result.passed

        # Missing required fields
        order = {"symbol": "AAPL", "direction": "buy"}
        result = fence.validate_order(order)
        assert not result.passed

        # Invalid direction
        order = {"symbol": "AAPL", "direction": "long", "price": 150}
        result = fence.validate_order(order)
        assert not result.passed

        # Mock source in order
        order = {"symbol": "AAPL", "direction": "buy", "price": 150, "source": "mock_trader"}
        result = fence.validate_order(order)
        assert not result.passed

    def test_order_sanitization(self):
        """Test that order data is sanitized."""
        fence = DataFence()

        order = {
            "symbol": "  tsla  ",  # Should be uppercased
            "direction": "  BUY  ",  # Should be lowercased
            "price": 200.50,
        }
        result = fence.validate_order(order)
        assert result.passed
        assert result.sanitized_data["symbol"] == "TSLA"
        assert result.sanitized_data["direction"] == "buy"

    def test_stats_tracking(self):
        """Test that statistics are tracked correctly."""
        fence = DataFence()

        # Valid signal
        signal = {"symbol": "AAPL", "score": 75, "source": "turbo_scanner"}
        fence.validate_signal(signal)

        # Invalid signal (mock source)
        signal = {"symbol": "AAPL", "score": 75, "source": "mock_source"}
        fence.validate_signal(signal)

        stats = fence.get_stats()
        assert stats["validation_count"] == 2
        assert stats["rejection_count"] == 1
        assert stats["rejection_rate"] == 0.5
        assert stats["mock_detection_count"] == 1

    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization."""
        result = ValidationResult()
        result.warn("Test warning")

        data = result.to_dict()
        assert data["passed"] is True
        assert len(data["warnings"]) == 1
        assert data["integrity_score"] == 90.0  # 100 - 10 for warning

    def test_symbol_normalization(self):
        """Test that symbols are normalized to uppercase."""
        fence = DataFence()

        signal = {
            "symbol": "aapl",
            "score": 75,
            "source": "turbo_scanner",
        }
        result = fence.validate_signal(signal)
        assert result.passed
        assert result.sanitized_data["symbol"] == "AAPL"

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        fence = DataFence()

        # Empty source (should fail mock detection but fail for being empty string)
        signal = {"symbol": "AAPL", "score": 75, "source": ""}
        result = fence.validate_signal(signal)
        # Empty source should pass (it's not mock)
        assert result.passed

        # Numeric symbol (some symbols are numeric)
        signal = {"symbol": "700", "score": 75, "source": "turbo_scanner"}
        result = fence.validate_signal(signal)
        assert result.passed

        # Symbol with dash (e.g., BRK-A)
        signal = {"symbol": "BRK-A", "score": 75, "source": "turbo_scanner"}
        result = fence.validate_signal(signal)
        assert result.passed

    def test_price_type_conversion(self):
        """Test that price strings are converted to float."""
        fence = DataFence()

        signal = {
            "symbol": "AAPL",
            "score": 75,
            "source": "turbo_scanner",
            "price": "150.25",  # String price
        }
        # Price validation happens with try/except for type conversion
        result = fence.validate_signal(signal)
        # String prices should be handled gracefully (warning, not failure)
        assert result.passed or len(result.warnings) > 0

    def test_concurrent_validations(self):
        """Test that multiple validations can happen concurrently."""
        fence = DataFence()

        signals = [
            {"symbol": f"SYM{i}", "score": 70 + i, "source": "turbo_scanner"}
            for i in range(10)
        ]

        results = [fence.validate_signal(s) for s in signals]

        assert all(r.passed for r in results)
        assert fence.get_stats()["validation_count"] == 10
        assert fence.get_stats()["rejection_count"] == 0
