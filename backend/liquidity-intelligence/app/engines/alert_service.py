"""
AlertService — creates structured alerts from engine outputs.
Handles the alert state machine transitions with full audit trail.
Pure domain logic — no framework imports.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from app.domain.entities import Alert, AlertStateTransition, AnomalyFlag, ForecastHorizon
from app.domain.value_objects import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    ConfidenceScore,
    Money,
)
from app.engines.liquidity_engine import LiquidityMatrix


def _new_id() -> str:
    return str(uuid.uuid4())


def create_liquidity_alert(
    agent_id: str,
    matrix: LiquidityMatrix,
) -> Optional[Alert]:
    """
    Create a LIQUIDITY_LOW or LIQUIDITY_CRITICAL alert from a LiquidityMatrix.
    Returns None if no threshold breach.
    """
    if not (matrix.is_low or matrix.is_critical):
        return None

    alert_type = AlertType.LIQUIDITY_CRITICAL if matrix.is_critical else AlertType.LIQUIDITY_LOW
    severity = AlertSeverity.CRITICAL if matrix.is_critical else AlertSeverity.HIGH

    return Alert(
        id=_new_id(),
        agent_id=agent_id,
        alert_type=alert_type,
        severity=severity,
        confidence=matrix.overall_confidence,
        evidence={
            "lowest_provider": matrix.lowest_provider.value,
            "total_liquidity_bdt": float(matrix.total_liquidity.amount),
            "bkash_bdt": float(matrix.bkash_balance.amount),
            "nagad_bdt": float(matrix.nagad_balance.amount),
            "rocket_bdt": float(matrix.rocket_balance.amount),
            "physical_cash_bdt": float(matrix.physical_cash.amount),
            "degraded_providers": matrix.degraded_providers,
        },
        status=AlertStatus.OPEN,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def create_anomaly_alert(
    agent_id: str,
    anomaly_flag: AnomalyFlag,
) -> Alert:
    """Create an ANOMALY_DETECTED alert from an AnomalyFlag entity."""
    severity = _score_to_severity(anomaly_flag.severity_score)
    return Alert(
        id=_new_id(),
        agent_id=agent_id,
        alert_type=AlertType.ANOMALY_DETECTED,
        severity=severity,
        confidence=anomaly_flag.confidence,
        evidence={
            "flag_type": anomaly_flag.flag_type.value,
            "severity_score": anomaly_flag.severity_score,
            "transaction_count": len(anomaly_flag.transaction_group_ids),
            "summary_en": anomaly_flag.explanation_en[:200],
        },
        anomaly_flag_id=anomaly_flag.id,
        status=AlertStatus.OPEN,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def create_forecast_alert(
    agent_id: str,
    forecast: ForecastHorizon,
    depletion_threshold_hours: float = 6.0,
) -> Optional[Alert]:
    """
    Create a FORECAST_BREACH alert if depletion is predicted within threshold.
    Returns None if no imminent depletion.
    """
    if forecast.depletion_time_hours is None:
        return None
    if forecast.depletion_time_hours > depletion_threshold_hours:
        return None

    hours = forecast.depletion_time_hours
    severity = AlertSeverity.CRITICAL if hours <= 2 else AlertSeverity.HIGH

    return Alert(
        id=_new_id(),
        agent_id=agent_id,
        alert_type=AlertType.FORECAST_BREACH,
        severity=severity,
        confidence=forecast.confidence,
        evidence={
            "provider": forecast.provider.value,
            "depletion_time_hours": round(hours, 1),
            "predicted_balance_bdt": float(forecast.predicted_balance.amount),
            "model_version": forecast.model_version,
        },
        forecast_horizon_id=forecast.id,
        status=AlertStatus.OPEN,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def transition_alert(
    alert: Alert,
    to_status: AlertStatus,
    actor_user_id: str,
    note: str = "",
) -> tuple[Alert, AlertStateTransition]:
    """
    Apply a state transition to an alert.
    Returns the updated alert and the transition audit record.
    Raises ValueError if the transition is invalid.
    """
    from_status = alert.status

    if to_status == AlertStatus.ACKNOWLEDGED:
        alert.acknowledge(actor_user_id)
    elif to_status == AlertStatus.IN_PROGRESS:
        alert.start_progress()
    elif to_status == AlertStatus.ESCALATED:
        alert.escalate()
    elif to_status == AlertStatus.RESOLVED:
        alert.resolve(note)
    else:
        raise ValueError(f"Unsupported target status: {to_status}")

    transition = AlertStateTransition(
        id=_new_id(),
        alert_id=alert.id,
        from_status=from_status,
        to_status=to_status,
        actor_user_id=actor_user_id,
        note=note,
        transitioned_at=datetime.utcnow(),
    )
    return alert, transition


def _score_to_severity(score: int) -> AlertSeverity:
    if score >= 80:
        return AlertSeverity.CRITICAL
    if score >= 55:
        return AlertSeverity.HIGH
    if score >= 30:
        return AlertSeverity.MEDIUM
    return AlertSeverity.LOW
