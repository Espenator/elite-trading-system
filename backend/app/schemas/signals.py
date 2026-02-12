"""Schemas for signals API (research doc)."""
from datetime import date
from typing import List

from pydantic import BaseModel, Field


class Signal(BaseModel):
    symbol: str
    date: date
    prob_up: float
    action: str


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
