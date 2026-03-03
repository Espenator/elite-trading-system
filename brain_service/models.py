"""Pydantic models for Brain Service payloads."""
from typing import List
from pydantic import BaseModel, Field


class InferRequestModel(BaseModel):
    symbol: str
    timeframe: str = "1d"
    feature_json: str = "{}"
    regime: str = "unknown"
    context: str = ""


class InferResponseModel(BaseModel):
    summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_flags: List[str] = []
    reasoning_bullets: List[str] = []
    error: str = ""


class CriticRequestModel(BaseModel):
    trade_id: str
    symbol: str
    entry_context: str = ""
    outcome_json: str = "{}"


class CriticResponseModel(BaseModel):
    analysis: str = ""
    lessons: List[str] = []
    performance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    error: str = ""


class EmbedRequestModel(BaseModel):
    text: str


class EmbedResponseModel(BaseModel):
    embedding: List[float] = []
    error: str = ""
