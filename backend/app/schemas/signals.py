"""Schemas for signals API (research doc)."""
from datetime import date
from typing import List

from pydantic import BaseModel, Field


class Signal(BaseModel):
    symbol: str
    date: date
    prob_up: float
    action: str
    edge: float = 0.0  # Kelly edge = prob_up * win_ratio - (1 - prob_up)
    kelly_fraction: float = 0.0  # Optimal Kelly bet fraction
    position_size_pct: float = 0.0  # Half-Kelly position as % of portfolio
    expected_value: float = 0.0  # Expected $ return per $1 risked
    volatility: float = 0.0  # Recent volatility (ATR-based)
    volume_score: float = 0.0  # Relative volume vs 20d avg
    sector: str = ""  # GICS sector


class SignalsResponse(BaseModel):
    as_of: date
    signals: List[Signal]


class ActiveSignalResponse(BaseModel):
    """Single active signal for a symbol (ExecutionDeck)."""
    symbol: str
    date: date
    prob_up: float
    action: str
    entry: float
    target: float
    stop: float
    risk_reward: float = Field(serialization_alias="riskReward")
    type: str  # same as action for display
    confidence: int  # prob_up as 0-100
    edge: float = 0.0
    kelly_fraction: float = 0.0
    position_size_pct: float = 0.0  # Half-Kelly recommended
    expected_value: float = 0.0
    max_loss_pct: float = 2.0  # Max loss per trade as % of portfolio
    trailing_stop_pct: float = 0.0  # Dynamic trailing stop
    sector: str = ""
    signal_quality: float = 0.0  # Signal quality 0-1
    risk_adjusted_score: float = 0.0  # Score adjusted for portfolio risk
    position_recommendation: str = "HOLD"  # FULL / HALF / SKIP / HOLD
    risk_score: int = 100  # Current portfolio risk score 0-100
    trading_allowed: bool = True  # Whether trading is currently allowed
