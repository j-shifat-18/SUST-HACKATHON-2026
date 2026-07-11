"""Pydantic v2 schemas for liquidity and snapshot endpoints."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ProviderBalanceSchema(BaseModel):
    provider: str
    balance_bdt: float
    share_pct: float
    is_stale: bool
    confidence: float


class LiquidityMatrixResponse(BaseModel):
    agent_id: str
    physical_cash_bdt: float
    bkash_balance_bdt: float
    nagad_balance_bdt: float
    rocket_balance_bdt: float
    total_liquidity_bdt: float
    utilization_pct: float
    lowest_provider: str
    is_low: bool
    is_critical: bool
    overall_confidence: float
    degraded_providers: list[str]
    captured_at: datetime


class ForecastSchema(BaseModel):
    provider: str
    current_balance_bdt: float
    predicted_balance_bdt: float
    depletion_time_hours: Optional[float]
    hourly_net_flow_bdt: float
    confidence: float
    forecast_hours: int


class AnomalyFlagSchema(BaseModel):
    id: str
    flag_type: str
    severity_score: int
    confidence: float
    explanation_en: str
    explanation_bn: str
    explanation_banglish: str
    transaction_count: int
    is_reviewed: bool
    created_at: datetime


class SnapshotResponse(BaseModel):
    request_id: str
    agent_id: str
    liquidity: LiquidityMatrixResponse
    forecasts: list[ForecastSchema]
    anomaly_count: int
    anomalies: list[AnomalyFlagSchema]
    agent_advisory: dict[str, Any]   # structured JSON from CoordinatorAgent
    overall_confidence: float
    generated_at: datetime
