from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class Provider(str, Enum):
    BKASH = "bkash"
    NAGAD = "nagad"
    ROCKET = "rocket"
    PHYSICAL = "physical"


class TransactionType(str, Enum):
    CASH_IN = "cash_in"
    CASH_OUT = "cash_out"
    TRANSFER = "transfer"
    RECHARGE = "recharge"


class AlertType(str, Enum):
    LIQUIDITY_LOW = "liquidity_low"
    LIQUIDITY_CRITICAL = "liquidity_critical"
    ANOMALY_DETECTED = "anomaly_detected"
    FORECAST_BREACH = "forecast_breach"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class AnomalyType(str, Enum):
    VELOCITY_SPIKE = "velocity_spike"
    TRANSACTION_SPLITTING = "transaction_splitting"
    CIRCULAR_FLOW = "circular_flow"


class UserRole(str, Enum):
    ADMIN = "admin"
    REGIONAL_MANAGER = "regional_manager"
    AREA_MANAGER = "area_manager"
    OPERATOR = "operator"


class ReviewLanguage(str, Enum):
    EN = "en"
    BN = "bn"
    BANGLISH = "banglish"


@dataclass(frozen=True)
class Money:
    """Immutable monetary amount in BDT (taka)."""
    amount: Decimal
    currency: str = "BDT"

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValueError(f"Money amount cannot be negative: {self.amount}")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

    def __lt__(self, other: "Money") -> bool:
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        return self.amount <= other.amount

    @classmethod
    def zero(cls) -> "Money":
        return cls(Decimal("0"))

    @classmethod
    def from_float(cls, value: float) -> "Money":
        return cls(Decimal(str(round(value, 2))))


@dataclass(frozen=True)
class ConfidenceScore:
    """Score between 0.0 and 1.0 indicating data freshness / model reliability."""
    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(f"ConfidenceScore must be 0-1, got {self.value}")

    def degrade(self, factor: float) -> "ConfidenceScore":
        return ConfidenceScore(max(0.0, self.value * factor))

    @classmethod
    def full(cls) -> "ConfidenceScore":
        return cls(1.0)

    @classmethod
    def none(cls) -> "ConfidenceScore":
        return cls(0.0)


@dataclass(frozen=True)
class ProviderBalance:
    """Balance for a single provider at a point in time."""
    provider: Provider
    balance: Money
    confidence: ConfidenceScore
    is_stale: bool = False
