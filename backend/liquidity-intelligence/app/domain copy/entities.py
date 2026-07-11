"""
Domain entities — identity-bearing objects. Zero framework imports.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .value_objects import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    AnomalyType,
    ConfidenceScore,
    Money,
    Provider,
    ReviewLanguage,
    TransactionType,
    UserRole,
)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Agent (super-agent / outlet)
# ---------------------------------------------------------------------------

@dataclass
class AgentEntity:
    id: str
    name: str
    phone: str
    area: str
    region: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

@dataclass
class Transaction:
    id: str
    agent_id: str
    provider: Provider
    transaction_type: TransactionType
    amount: Money
    timestamp: datetime
    area: str
    account_ref: str  # anonymised counterparty ref
    anomaly_flag_id: Optional[str] = None  # set by AnomalyEngine post-processing
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# LiquiditySnapshot
# ---------------------------------------------------------------------------

@dataclass
class LiquiditySnapshot:
    id: str
    agent_id: str
    physical_cash: Money
    bkash_balance: Money
    nagad_balance: Money
    rocket_balance: Money
    overall_confidence: ConfidenceScore
    captured_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_liquidity(self) -> Money:
        return (
            self.physical_cash
            + self.bkash_balance
            + self.nagad_balance
            + self.rocket_balance
        )

    def balance_for(self, provider: Provider) -> Money:
        mapping = {
            Provider.PHYSICAL: self.physical_cash,
            Provider.BKASH: self.bkash_balance,
            Provider.NAGAD: self.nagad_balance,
            Provider.ROCKET: self.rocket_balance,
        }
        return mapping[provider]


# ---------------------------------------------------------------------------
# ForecastHorizon
# ---------------------------------------------------------------------------

@dataclass
class ForecastHorizon:
    id: str
    agent_id: str
    provider: Provider
    forecast_hours: int
    predicted_balance: Money
    depletion_time_hours: Optional[float]  # None = no depletion expected
    confidence: ConfidenceScore
    model_version: str
    generated_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# AnomalyFlag
# ---------------------------------------------------------------------------

@dataclass
class AnomalyFlag:
    id: str
    transaction_id: Optional[str]  # nullable for group-level flags
    transaction_group_ids: list[str]  # for splitting / circular detection
    flag_type: AnomalyType
    severity_score: int  # 0-100
    confidence: ConfidenceScore
    evidence: dict  # raw signals as JSON-serialisable dict
    explanation_en: str
    explanation_bn: str
    explanation_banglish: str
    review_language: ReviewLanguage = ReviewLanguage.EN
    is_reviewed: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

@dataclass
class Alert:
    id: str
    agent_id: str
    alert_type: AlertType
    severity: AlertSeverity
    confidence: ConfidenceScore
    evidence: dict
    status: AlertStatus = AlertStatus.OPEN
    assigned_to_user_id: Optional[str] = None
    anomaly_flag_id: Optional[str] = None
    forecast_horizon_id: Optional[str] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # --- state-machine transitions ---
    def acknowledge(self, user_id: str) -> None:
        if self.status != AlertStatus.OPEN:
            raise ValueError(f"Cannot acknowledge alert in state {self.status}")
        self.status = AlertStatus.ACKNOWLEDGED
        self.assigned_to_user_id = user_id
        self.updated_at = datetime.utcnow()

    def start_progress(self) -> None:
        if self.status != AlertStatus.ACKNOWLEDGED:
            raise ValueError(f"Cannot start progress from state {self.status}")
        self.status = AlertStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()

    def escalate(self) -> None:
        if self.status not in (AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS):
            raise ValueError(f"Cannot escalate from state {self.status}")
        self.status = AlertStatus.ESCALATED
        self.updated_at = datetime.utcnow()

    def resolve(self, notes: str = "") -> None:
        if self.status not in (
            AlertStatus.IN_PROGRESS,
            AlertStatus.ESCALATED,
            AlertStatus.ACKNOWLEDGED,
        ):
            raise ValueError(f"Cannot resolve from state {self.status}")
        self.status = AlertStatus.RESOLVED
        if notes:
            self.notes = notes
        self.updated_at = datetime.utcnow()


# ---------------------------------------------------------------------------
# AlertStateTransition (audit record)
# ---------------------------------------------------------------------------

@dataclass
class AlertStateTransition:
    id: str
    alert_id: str
    from_status: AlertStatus
    to_status: AlertStatus
    actor_user_id: str
    note: str = ""
    transitioned_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Case (linked alerts)
# ---------------------------------------------------------------------------

@dataclass
class Case:
    id: str
    agent_id: str
    title: str
    alert_ids: list[str]
    status: str = "open"  # open / closed
    resolution_note: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# DataFeedStatus
# ---------------------------------------------------------------------------

@dataclass
class DataFeedStatus:
    id: str
    provider: Provider
    last_received_at: Optional[datetime]
    is_healthy: bool
    staleness_threshold_seconds: int = 300

    @property
    def is_stale(self) -> bool:
        if self.last_received_at is None:
            return True
        delta = (datetime.utcnow() - self.last_received_at).total_seconds()
        return delta > self.staleness_threshold_seconds


# ---------------------------------------------------------------------------
# User (internal RBAC entity)
# ---------------------------------------------------------------------------

@dataclass
class User:
    id: str
    firebase_uid: str
    phone: str
    name: str
    role: UserRole
    region: Optional[str] = None
    area: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# AgentTraceLog (AI observability)
# ---------------------------------------------------------------------------

@dataclass
class AgentTraceLog:
    id: str
    request_id: str
    agent_name: str
    input_summary: str
    output_summary: str
    tool_calls: list[dict]
    duration_ms: int
    created_at: datetime = field(default_factory=datetime.utcnow)
