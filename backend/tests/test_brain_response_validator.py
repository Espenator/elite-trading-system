"""Tests for strict parser/validator for Brain Service hypothesis and critic responses."""
import pytest

from app.services.brain_response_validator import (
    validate_hypothesis_response,
    validate_critic_response,
    ValidatedHypothesis,
    ValidatedCritic,
)


class TestValidateHypothesisResponse:
    """Strict validator must never leak malformed data; invalid → safe defaults."""

    def test_valid_llm_response(self):
        raw = {
            "direction": "buy",
            "confidence": 0.75,
            "reasoning": "Strong momentum and volume.",
            "summary": "Bullish setup.",
            "risk_flags": [],
            "reasoning_bullets": ["RSI oversold", "Volume surge"],
            "supporting_signals": ["breakout", "sector strength"],
            "invalidation_notes": ["break below 50d MA"],
        }
        v = validate_hypothesis_response(raw)
        assert isinstance(v, ValidatedHypothesis)
        assert v.direction == "buy"
        assert v.confidence == 0.75
        assert "momentum" in v.reasoning
        assert v.supporting_signals == ["breakout", "sector strength"]
        assert v.invalidation_notes == ["break below 50d MA"]
        assert v.is_fallback is False

    def test_fallback_tag_sets_is_fallback_and_caps_confidence(self):
        raw = {
            "direction": "buy",
            "confidence": 0.8,
            "reasoning": "Ok",
            "summary": "Ok",
            "risk_flags": ["timeout"],
            "reasoning_bullets": [],
            "supporting_signals": [],
            "invalidation_notes": [],
        }
        v = validate_hypothesis_response(raw)
        assert v.is_fallback is True
        assert v.confidence <= 0.2
        assert v.direction == "buy"

    def test_malformed_direction_coerced_to_hold(self):
        raw = {
            "direction": "LONG",
            "confidence": 0.6,
            "reasoning": "x",
            "summary": "x",
            "risk_flags": [],
        }
        v = validate_hypothesis_response(raw)
        assert v.direction == "hold"

    def test_malformed_confidence_clamped(self):
        raw = {
            "direction": "sell",
            "confidence": 1.5,
            "reasoning": "x",
            "summary": "x",
            "risk_flags": [],
        }
        v = validate_hypothesis_response(raw)
        assert 0.0 <= v.confidence <= 1.0
        assert v.confidence == 1.0

    def test_empty_and_none_safe(self):
        v = validate_hypothesis_response({})
        assert v.direction == "hold"
        assert v.confidence == 0.2
        assert v.reasoning == ""
        assert v.supporting_signals == []
        assert v.invalidation_notes == []
        assert v.is_fallback is False  # no fallback tag

    def test_error_key_sets_fallback(self):
        v = validate_hypothesis_response({"error": "timeout", "confidence": 0.9})
        assert v.is_fallback is True
        assert v.confidence <= 0.2


class TestValidateCriticResponse:
    def test_valid_critic_response(self):
        raw = {
            "analysis": "Trade met target.",
            "lessons": ["Hold winners"],
            "performance_score": 0.8,
            "key_takeaways": ["R-multiple positive"],
        }
        v = validate_critic_response(raw)
        assert isinstance(v, ValidatedCritic)
        assert v.analysis == "Trade met target."
        assert v.lessons == ["Hold winners"]
        assert v.performance_score == 0.8
        assert v.key_takeaways == ["R-multiple positive"]
        assert v.is_fallback is False

    def test_critic_error_sets_fallback(self):
        v = validate_critic_response({"error": "timeout", "performance_score": 0.5})
        assert v.is_fallback is True

    def test_critic_empty_safe(self):
        v = validate_critic_response({})
        assert v.analysis == ""
        assert v.performance_score == 0.2
        assert v.lessons == []
        assert v.key_takeaways == []
