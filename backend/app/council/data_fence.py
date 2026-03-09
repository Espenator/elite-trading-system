"""Data Fence — protective boundary system for validating data before council evaluation.

DataFence is a perimeter defense that validates and guards data flowing through
the trading pipeline before it reaches decision engines. It consolidates all
data validation currently scattered across services (mock guards, sanitization,
type validation) into a unified protective layer.

Key responsibilities:
    - Validate signal data completeness and type safety
    - Detect mock/fake/incomplete data sources
    - Sanitize and normalize inputs
    - Check data freshness and reliability
    - Maintain data integrity scores
    - Block bad data from corrupting council decisions

Integrates with:
    - SignalEngine: validates signals before council evaluation
    - OrderExecutor: validates orders before execution
    - DataQualityMonitor: checks source freshness
    - Homeostasis: triggers degradation on bad data

Usage:
    from app.council.data_fence import get_data_fence
    fence = get_data_fence()
    result = fence.validate_signal(signal_data)
    if not result.passed:
        logger.warning("Signal rejected: %s", result.rejection_reason)
"""
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Validation thresholds
MAX_STRING_LENGTH = 1000  # Max length for text fields
MIN_PRICE = 0.01  # Minimum valid price
MAX_PRICE = 1_000_000  # Maximum valid price
MIN_SCORE = 0.0  # Minimum signal score
MAX_SCORE = 100.0  # Maximum signal score
MAX_SYMBOL_LENGTH = 10  # Max ticker symbol length

# Mock/test source patterns (case-insensitive)
MOCK_SOURCE_PATTERNS = [
    r"mock",
    r"test",
    r"fake",
    r"demo",
    r"sample",
    r"placeholder",
]

# Required fields for signal validation
REQUIRED_SIGNAL_FIELDS = {
    "symbol",
    "score",
    "source",
}

# Required fields for order validation
REQUIRED_ORDER_FIELDS = {
    "symbol",
    "direction",
    "price",
}


@dataclass
class ValidationResult:
    """Result of data validation through the fence."""
    passed: bool = True
    rejection_reason: str = ""
    warnings: List[str] = field(default_factory=list)
    sanitized_data: Dict[str, Any] = field(default_factory=dict)
    integrity_score: float = 100.0  # 0-100 quality score

    def fail(self, reason: str):
        """Mark validation as failed."""
        self.passed = False
        self.rejection_reason = reason
        self.integrity_score = 0.0

    def warn(self, warning: str):
        """Add a non-fatal warning."""
        self.warnings.append(warning)
        # Each warning reduces integrity score by 10 points
        self.integrity_score = max(0, self.integrity_score - 10)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "passed": self.passed,
            "rejection_reason": self.rejection_reason,
            "warnings": self.warnings,
            "integrity_score": self.integrity_score,
        }


class DataFence:
    """Protective boundary system for data validation and quality control."""

    def __init__(self):
        """Initialize the data fence."""
        self._blocked_sources: Set[str] = set()
        self._validation_count = 0
        self._rejection_count = 0
        self._mock_detection_count = 0

    def validate_signal(
        self,
        signal_data: Dict[str, Any],
        check_freshness: bool = True,
    ) -> ValidationResult:
        """Validate signal data before council evaluation.

        Args:
            signal_data: Signal dictionary to validate
            check_freshness: Whether to check data source freshness

        Returns:
            ValidationResult with pass/fail status and sanitized data
        """
        result = ValidationResult()
        self._validation_count += 1

        # Check 1: Required fields
        missing = REQUIRED_SIGNAL_FIELDS - set(signal_data.keys())
        if missing:
            result.fail(f"Missing required fields: {', '.join(missing)}")
            self._rejection_count += 1
            return result

        # Check 2: Mock source detection
        source = str(signal_data.get("source", "")).strip()
        if self._is_mock_source(source):
            result.fail(f"Mock/test source detected: {source}")
            self._rejection_count += 1
            self._mock_detection_count += 1
            return result

        # Check 3: Blocked sources
        if source.lower() in self._blocked_sources:
            result.fail(f"Source is blocked: {source}")
            self._rejection_count += 1
            return result

        # Check 4: Symbol validation
        symbol = str(signal_data.get("symbol", "")).strip().upper()
        if not self._is_valid_symbol(symbol):
            result.fail(f"Invalid symbol: {symbol}")
            self._rejection_count += 1
            return result

        # Check 5: Score validation
        score = signal_data.get("score")
        if score is None:
            result.fail("Score is missing")
            self._rejection_count += 1
            return result

        try:
            score = float(score)
        except (ValueError, TypeError):
            result.fail(f"Score is not numeric: {score}")
            self._rejection_count += 1
            return result

        if not (MIN_SCORE <= score <= MAX_SCORE):
            result.fail(f"Score {score} out of range [{MIN_SCORE}, {MAX_SCORE}]")
            self._rejection_count += 1
            return result

        # Check 6: Sanitize text fields
        sanitized = self._sanitize_signal(signal_data)
        result.sanitized_data = sanitized

        # Check 7: Data completeness warning
        if not signal_data.get("regime"):
            result.warn("Missing regime field")

        if not signal_data.get("timestamp"):
            result.warn("Missing timestamp field")

        # Check 8: Price validation if present
        price = signal_data.get("price")
        if price is not None:
            try:
                price = float(price)
                if not (MIN_PRICE <= price <= MAX_PRICE):
                    result.fail(f"Price {price} out of range [{MIN_PRICE}, {MAX_PRICE}]")
                    self._rejection_count += 1
                    return result
            except (ValueError, TypeError):
                result.warn(f"Invalid price value: {price}")

        logger.debug(
            "Signal validation: %s %s score=%.1f integrity=%.0f%%",
            "PASS" if result.passed else "FAIL",
            symbol,
            score,
            result.integrity_score,
        )

        return result

    def validate_order(
        self,
        order_data: Dict[str, Any],
    ) -> ValidationResult:
        """Validate order data before execution.

        Args:
            order_data: Order dictionary to validate

        Returns:
            ValidationResult with pass/fail status
        """
        result = ValidationResult()
        self._validation_count += 1

        # Check 1: Required fields
        missing = REQUIRED_ORDER_FIELDS - set(order_data.keys())
        if missing:
            result.fail(f"Missing required order fields: {', '.join(missing)}")
            self._rejection_count += 1
            return result

        # Check 2: Symbol validation
        symbol = str(order_data.get("symbol", "")).strip().upper()
        if not self._is_valid_symbol(symbol):
            result.fail(f"Invalid order symbol: {symbol}")
            self._rejection_count += 1
            return result

        # Check 3: Direction validation
        direction = str(order_data.get("direction", "")).lower().strip()
        if direction not in ("buy", "sell", "hold"):
            result.fail(f"Invalid direction: {direction}")
            self._rejection_count += 1
            return result

        # Check 4: Price validation
        price = order_data.get("price")
        try:
            price = float(price)
        except (ValueError, TypeError):
            result.fail(f"Order price is not numeric: {price}")
            self._rejection_count += 1
            return result

        if not (MIN_PRICE <= price <= MAX_PRICE):
            result.fail(f"Order price {price} out of range [{MIN_PRICE}, {MAX_PRICE}]")
            self._rejection_count += 1
            return result

        # Check 5: Mock source detection for orders
        source = str(order_data.get("source", "")).strip()
        if source and self._is_mock_source(source):
            result.fail(f"Mock/test source in order: {source}")
            self._rejection_count += 1
            self._mock_detection_count += 1
            return result

        # Sanitize order data
        result.sanitized_data = self._sanitize_order(order_data)

        logger.debug(
            "Order validation: %s %s %s @ $%.2f",
            "PASS" if result.passed else "FAIL",
            direction.upper(),
            symbol,
            price,
        )

        return result

    def sanitize_text(self, text: str, max_length: int = MAX_STRING_LENGTH) -> str:
        """Sanitize text input by removing dangerous characters and limiting length.

        Args:
            text: Text to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized text
        """
        if not isinstance(text, str):
            text = str(text)

        # Remove control characters and null bytes
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

        # Trim whitespace
        text = text.strip()

        # Limit length
        if len(text) > max_length:
            text = text[:max_length]

        return text

    def block_source(self, source: str):
        """Block a data source from passing validation.

        Args:
            source: Source name to block
        """
        self._blocked_sources.add(source.lower().strip())
        logger.warning("Data source blocked: %s", source)

    def unblock_source(self, source: str):
        """Unblock a previously blocked data source.

        Args:
            source: Source name to unblock
        """
        self._blocked_sources.discard(source.lower().strip())
        logger.info("Data source unblocked: %s", source)

    def get_stats(self) -> Dict[str, Any]:
        """Get data fence statistics.

        Returns:
            Statistics dictionary
        """
        rejection_rate = 0.0
        if self._validation_count > 0:
            rejection_rate = self._rejection_count / self._validation_count

        return {
            "validation_count": self._validation_count,
            "rejection_count": self._rejection_count,
            "rejection_rate": round(rejection_rate, 3),
            "mock_detection_count": self._mock_detection_count,
            "blocked_sources": list(self._blocked_sources),
        }

    def _is_mock_source(self, source: str) -> bool:
        """Check if a source matches mock/test patterns.

        Args:
            source: Source string to check

        Returns:
            True if source appears to be mock/test data
        """
        if not source:
            return False

        source_lower = source.lower()
        for pattern in MOCK_SOURCE_PATTERNS:
            if re.search(pattern, source_lower):
                return True

        return False

    def _is_valid_symbol(self, symbol: str) -> bool:
        """Validate ticker symbol format.

        Args:
            symbol: Ticker symbol to validate

        Returns:
            True if symbol appears valid
        """
        if not symbol or len(symbol) > MAX_SYMBOL_LENGTH:
            return False

        # Symbols should be alphanumeric, possibly with dots or dashes
        if not re.match(r'^[A-Z0-9.-]+$', symbol):
            return False

        return True

    def _sanitize_signal(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize signal data fields.

        Args:
            signal_data: Raw signal data

        Returns:
            Sanitized signal data
        """
        sanitized = {}

        for key, value in signal_data.items():
            # Preserve numeric fields as-is
            if isinstance(value, (int, float)):
                sanitized[key] = value
            # Sanitize string fields
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_text(value)
            # Preserve other types (dict, list, etc.)
            else:
                sanitized[key] = value

        # Ensure symbol is uppercase
        if "symbol" in sanitized and isinstance(sanitized["symbol"], str):
            sanitized["symbol"] = sanitized["symbol"].upper().strip()

        return sanitized

    def _sanitize_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize order data fields.

        Args:
            order_data: Raw order data

        Returns:
            Sanitized order data
        """
        sanitized = {}

        for key, value in order_data.items():
            if isinstance(value, (int, float)):
                sanitized[key] = value
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_text(value)
            else:
                sanitized[key] = value

        # Normalize symbol and direction
        if "symbol" in sanitized and isinstance(sanitized["symbol"], str):
            sanitized["symbol"] = sanitized["symbol"].upper().strip()

        if "direction" in sanitized and isinstance(sanitized["direction"], str):
            sanitized["direction"] = sanitized["direction"].lower().strip()

        return sanitized


# Singleton instance
_fence: Optional[DataFence] = None


def get_data_fence() -> DataFence:
    """Get the global DataFence singleton instance.

    Returns:
        DataFence singleton
    """
    global _fence
    if _fence is None:
        _fence = DataFence()
    return _fence
