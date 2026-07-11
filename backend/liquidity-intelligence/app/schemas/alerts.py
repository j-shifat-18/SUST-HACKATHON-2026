"""Pydantic v2 schemas for alert endpoints."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: str
    agent_id: str
    alert_type: str
    severity: str
    confidence: float
    evidence: dict[str, Any]
    status: str
    assigned_to_user_id: Optional[str]
    notes: str
    created_at: datetime
    updated_at: datetime


class AlertTransitionRequest(BaseModel):
    note: str = Field(default="", max_length=1000)


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]
    total: int
