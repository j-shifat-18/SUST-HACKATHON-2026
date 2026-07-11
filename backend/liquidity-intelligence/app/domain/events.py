"""
Domain events — decoupled state-change signals. Zero framework imports.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class LiquidityThresholdBreachedEvent(DomainEvent):
    agent_id: str = ""
    provider: str = ""
    balance_bdt: float = 0.0
    threshold_pct: float = 0.0


@dataclass(frozen=True)
class AnomalyDetectedEvent(DomainEvent):
    agent_id: str = ""
    anomaly_flag_id: str = ""
    flag_type: str = ""
    severity_score: int = 0


@dataclass(frozen=True)
class AlertStatusChangedEvent(DomainEvent):
    alert_id: str = ""
    from_status: str = ""
    to_status: str = ""
    actor_user_id: str = ""


@dataclass(frozen=True)
class ForecastBreachEvent(DomainEvent):
    agent_id: str = ""
    provider: str = ""
    depletion_hours: float = 0.0
    confidence: float = 0.0


@dataclass(frozen=True)
class DataFeedStaleEvent(DomainEvent):
    provider: str = ""
    last_received_at: str = ""  # ISO string
