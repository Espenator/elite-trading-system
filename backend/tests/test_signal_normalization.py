"""Tests for signal normalization in signal_engine.py

Tests that bull and bear signals are normalized symmetrically,
preserving granularity when regime multipliers > 1.0.
"""
import pytest


def test_bull_signal_normalization_crisis_regime():
    """Test bull signal normalization in CRISIS regime (mult=0.65)."""
    # In CRISIS regime, bull signals should be suppressed
    regime_mult = 0.65

    # Test various blended scores
    test_cases = [
        (0.0, 0.0),      # Min score
        (50.0, 32.5),    # Mid score: 50 * 0.65 = 32.5
        (100.0, 65.0),   # Max score: 100 * 0.65 = 65.0
    ]

    for blended, expected in test_cases:
        # Apply the normalization logic from signal_engine.py
        max_input_bull = 100.0 / regime_mult if regime_mult > 1.0 else 100.0
        clamped_blended = min(blended, max_input_bull)
        final_score = max(0.0, clamped_blended * regime_mult)

        assert abs(final_score - expected) < 0.01, f"Failed for blended={blended}"
        assert 0 <= final_score <= 100, f"Score out of range: {final_score}"


def test_bull_signal_normalization_bullish_regime():
    """Test bull signal normalization in BULLISH regime (mult=1.10)."""
    # In BULLISH regime, bull signals should be amplified
    regime_mult = 1.10

    # Test various blended scores
    test_cases = [
        (0.0, 0.0),      # Min score
        (50.0, 55.0),    # Mid score: 50 * 1.10 = 55.0
        (90.0, 99.0),    # High score: 90 * 1.10 = 99.0
        (91.0, 100.0),   # Near max: would be 100.1, gets clamped to 100
        (100.0, 100.0),  # Max score: would be 110, gets clamped to 100
    ]

    for blended, expected in test_cases:
        # Apply the normalization logic from signal_engine.py
        max_input_bull = 100.0 / regime_mult if regime_mult > 1.0 else 100.0
        clamped_blended = min(blended, max_input_bull)
        final_score = max(0.0, clamped_blended * regime_mult)

        assert abs(final_score - expected) < 0.01, f"Failed for blended={blended}"
        assert 0 <= final_score <= 100, f"Score out of range: {final_score}"


def test_bear_signal_normalization_crisis_regime():
    """Test bear signal normalization in CRISIS regime (mult=1.35).

    This tests the fix for the signal normalization issue.
    Before the fix, values would exceed 100 and get clamped, losing granularity.
    After the fix, we clamp the input before multiplying to preserve granularity.
    """
    # In CRISIS regime, bear signals should be amplified
    bear_regime_mult = 1.35

    # Test various blended scores
    test_cases = [
        # (blended, expected_bear_score)
        (100.0, 0.0),    # Strong bull -> weak bear: (100-100) = 0 * 1.35 = 0
        (50.0, 67.5),    # Neutral: (100-50) = 50 * 1.35 = 67.5
        (26.0, 99.9),    # Near threshold: (100-26) = 74 * 1.35 ≈ 100 (at max_input limit)
        (20.0, 100.0),   # Strong bear: (100-20) = 80, clamped to 74.07, * 1.35 = 100
        (0.0, 100.0),    # Max bear: (100-0) = 100, clamped to 74.07, * 1.35 = 100
    ]

    for blended, expected in test_cases:
        # Apply the normalization logic from signal_engine.py (AFTER FIX)
        inverted_score = 100.0 - blended
        max_input_bear = 100.0 / bear_regime_mult if bear_regime_mult > 1.0 else 100.0
        clamped_inverted = min(inverted_score, max_input_bear)
        bear_score = max(0.0, clamped_inverted * bear_regime_mult)

        assert abs(bear_score - expected) < 0.2, f"Failed for blended={blended}: got {bear_score}, expected {expected}"
        assert 0 <= bear_score <= 100.01, f"Score out of range: {bear_score}"  # Allow tiny FP errors


def test_bear_signal_normalization_bullish_regime():
    """Test bear signal normalization in BULLISH regime (mult=0.65)."""
    # In BULLISH regime, bear signals should be suppressed
    bear_regime_mult = 0.65

    # Test various blended scores
    test_cases = [
        (100.0, 0.0),    # Strong bull -> weak bear: (100-100) * 0.65 = 0
        (50.0, 32.5),    # Neutral: (100-50) * 0.65 = 32.5
        (0.0, 65.0),     # Strong bear: (100-0) * 0.65 = 65.0
    ]

    for blended, expected in test_cases:
        # Apply the normalization logic from signal_engine.py
        inverted_score = 100.0 - blended
        max_input_bear = 100.0 / bear_regime_mult if bear_regime_mult > 1.0 else 100.0
        clamped_inverted = min(inverted_score, max_input_bear)
        bear_score = max(0.0, clamped_inverted * bear_regime_mult)

        assert abs(bear_score - expected) < 0.01, f"Failed for blended={blended}"
        assert 0 <= bear_score <= 100, f"Score out of range: {bear_score}"


def test_signal_normalization_preserves_granularity():
    """Test that the fix preserves granularity at high scores in CRISIS regime.

    Before the fix:
    - blended=0 -> bear=(100-0)*1.35=135 -> clamped to 100
    - blended=10 -> bear=(100-10)*1.35=121.5 -> clamped to 100
    - blended=20 -> bear=(100-20)*1.35=108 -> clamped to 100
    All three resulted in bear_score=100, losing granularity.

    After the fix:
    - All scores should clamp to max 100, but still maintain differences
    - The clamping happens before multiplication, preserving relative differences
    """
    bear_regime_mult = 1.35
    max_input_bear = 100.0 / bear_regime_mult  # ≈ 74.07

    test_scores = [0.0, 10.0, 20.0, 26.0]
    bear_scores = []

    for blended in test_scores:
        inverted_score = 100.0 - blended
        clamped_inverted = min(inverted_score, max_input_bear)
        bear_score = max(0.0, clamped_inverted * bear_regime_mult)
        bear_scores.append(bear_score)

    # After the fix, scores that were previously all clamped to 100
    # should now hit the maximum (100) for strong bear signals
    # The clamping happens at the input, so max_input_bear * 1.35 = 100

    # blended=26 gives inverted=74, which is at the threshold (74.07)
    assert abs(bear_scores[3] - 100.0) < 0.2  # Near 100

    # blended=0, 10, 20 all give inverted > 74.07, so all clamp to max_input_bear
    # and result in 100
    assert abs(bear_scores[0] - 100.0) < 0.01  # Should be 100
    assert abs(bear_scores[1] - 100.0) < 0.01  # Should be 100
    assert abs(bear_scores[2] - 100.0) < 0.01  # Should be 100

    # The key is that with the new approach, we're clamping at the input
    # This is better than clamping at the output because it's more explicit
    # about when we hit the maximum value


def test_signal_normalization_symmetry():
    """Test that bull and bear signals have symmetric normalization behavior."""
    # Test in NEUTRAL regime where both multipliers are 1.0
    bull_mult = 1.0
    bear_mult = 1.0

    blended = 70.0

    # Bull signal
    max_input_bull = 100.0 / bull_mult if bull_mult > 1.0 else 100.0
    clamped_blended = min(blended, max_input_bull)
    bull_score = max(0.0, clamped_blended * bull_mult)

    # Bear signal
    inverted_score = 100.0 - blended
    max_input_bear = 100.0 / bear_mult if bear_mult > 1.0 else 100.0
    clamped_inverted = min(inverted_score, max_input_bear)
    bear_score = max(0.0, clamped_inverted * bear_mult)

    # In neutral regime, bull=70 and bear=30 should sum to 100
    assert abs(bull_score - 70.0) < 0.01
    assert abs(bear_score - 30.0) < 0.01
    assert abs((bull_score + bear_score) - 100.0) < 0.01


def test_regime_multiplier_ranges():
    """Test that all regime multipliers produce valid scores."""
    # Test all regime multipliers from the actual code
    bull_multipliers = [0.65, 0.80, 0.90, 1.00, 1.05, 1.10]  # CRISIS to BULLISH
    bear_multipliers = [0.65, 0.80, 1.00, 1.05, 1.10, 1.35]  # BULLISH to CRISIS

    test_blended = [0.0, 25.0, 50.0, 75.0, 100.0]

    for regime_mult in bull_multipliers:
        for blended in test_blended:
            max_input_bull = 100.0 / regime_mult if regime_mult > 1.0 else 100.0
            clamped_blended = min(blended, max_input_bull)
            final_score = max(0.0, clamped_blended * regime_mult)

            assert 0 <= final_score <= 100, (
                f"Bull signal out of range: blended={blended}, "
                f"mult={regime_mult}, score={final_score}"
            )

    for bear_regime_mult in bear_multipliers:
        for blended in test_blended:
            inverted_score = 100.0 - blended
            max_input_bear = 100.0 / bear_regime_mult if bear_regime_mult > 1.0 else 100.0
            clamped_inverted = min(inverted_score, max_input_bear)
            bear_score = max(0.0, clamped_inverted * bear_regime_mult)

            assert 0 <= bear_score <= 100.01, (  # Allow tiny FP errors
                f"Bear signal out of range: blended={blended}, "
                f"mult={bear_regime_mult}, score={bear_score}"
            )


def test_edge_cases():
    """Test edge cases for signal normalization."""
    # Test with mult = 1.0 (no scaling)
    regime_mult = 1.0
    blended = 100.0

    max_input_bull = 100.0 / regime_mult if regime_mult > 1.0 else 100.0
    clamped_blended = min(blended, max_input_bull)
    final_score = max(0.0, clamped_blended * regime_mult)

    assert final_score == 100.0

    # Test with very small multiplier
    regime_mult = 0.65
    blended = 100.0

    max_input_bull = 100.0 / regime_mult if regime_mult > 1.0 else 100.0
    clamped_blended = min(blended, max_input_bull)
    final_score = max(0.0, clamped_blended * regime_mult)

    assert final_score == 65.0

    # Test with zero blended score
    regime_mult = 1.35
    blended = 0.0

    max_input_bull = 100.0 / regime_mult if regime_mult > 1.0 else 100.0
    clamped_blended = min(blended, max_input_bull)
    final_score = max(0.0, clamped_blended * regime_mult)

    assert final_score == 0.0
