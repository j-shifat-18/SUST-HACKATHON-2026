"""
Alert management endpoints.
GET /api/v1/alerts — list alerts
GET /api/v1/alerts/{alert_id} — get single alert
POST /api/v1/alerts/{alert_id}/acknowledge — OPEN → ACKNOWLEDGED
POST /api/v1/alerts/{alert_id}/escalate — ACKNOWLEDGED|IN_PROGRESS → ESCALATED
POST /api/v1/alerts/{alert_id}/resolve — ACKNOWLEDGED|IN_PROGRESS|ESCALATED → RESOLVED
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from prisma import Prisma

from app.api.v1.deps import get_current_user, get_db
from app.db.repositories.prisma_repositories import PrismaAlertRepository
from app.domain.entities import AlertStateTransition, User
from app.domain.value_objects import AlertStatus
from app.schemas.alerts import (
    AlertListResponse,
    AlertResponse,
    AlertTransitionRequest,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _to_response(alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        agent_id=alert.agent_id,
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        confidence=alert.confidence.value,
        evidence=alert.evidence,
        status=alert.status.value,
        assigned_to_user_id=alert.assigned_to_user_id,
        notes=alert.notes,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status_filter: str = Query(default="open"),
    agent_id: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """List alerts, filtered by status and scoped to the user's region/area."""
    alert_repo = PrismaAlertRepository(db)

    if agent_id:
        try:
            alert_status = AlertStatus(status_filter)
        except ValueError:
            alert_status = None
        alerts = await alert_repo.list_for_agent(agent_id, status=alert_status)
    else:
        # Use status filter and scope to user's region
        try:
            alert_status = AlertStatus(status_filter)
        except ValueError:
            alert_status = AlertStatus.OPEN

        # Query directly with status filter and region scope
        where: dict = {"status": alert_status.value}
        agent_filter: dict = {}
        if user.region:
            agent_filter["region"] = user.region
        if user.area:
            agent_filter["area"] = user.area
        if agent_filter:
            where["agent"] = {"is": agent_filter}

        rows = await db.alert.find_many(
            where=where, order={"createdAt": "desc"}, take=100
        )
        # Map to domain entities
        from app.domain.value_objects import AlertType, AlertSeverity, ConfidenceScore
        alerts = []
        for m in rows:
            from app.domain.entities import Alert
            alerts.append(Alert(
                id=m.id, agent_id=m.agentId,
                alert_type=AlertType(m.alertType),
                severity=AlertSeverity(m.severity),
                confidence=ConfidenceScore(m.confidence),
                evidence=m.evidence if isinstance(m.evidence, dict) else {},
                status=AlertStatus(m.status),
                assigned_to_user_id=m.assignedToUserId,
                anomaly_flag_id=m.anomalyFlagId,
                forecast_horizon_id=m.forecastHorizonId,
                notes=m.notes or "",
                created_at=m.createdAt,
                updated_at=m.updatedAt,
            ))

    return AlertListResponse(
        alerts=[_to_response(a) for a in alerts],
        total=len(alerts),
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """Get a single alert by ID."""
    alert_repo = PrismaAlertRepository(db)
    alert = await alert_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _to_response(alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    body: AlertTransitionRequest = AlertTransitionRequest(),
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """
    Acknowledge an open alert. Transition: OPEN → ACKNOWLEDGED → RESOLVED.
    Also closes any linked case automatically.
    """
    alert_repo = PrismaAlertRepository(db)
    alert = await alert_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        from_status = alert.status
        alert.acknowledge(user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save acknowledge transition
    transition = AlertStateTransition(
        id=str(uuid.uuid4()),
        alert_id=alert.id,
        from_status=from_status,
        to_status=alert.status,
        actor_user_id=user.id,
        note=body.note or "Alert acknowledged.",
        transitioned_at=datetime.now(timezone.utc),
    )
    await alert_repo.save(alert)
    await alert_repo.save_transition(transition)

    # Auto-resolve after acknowledge
    ack_status = alert.status
    alert.resolve(notes=body.note or "Resolved after acknowledgement.")
    resolve_transition = AlertStateTransition(
        id=str(uuid.uuid4()),
        alert_id=alert.id,
        from_status=ack_status,
        to_status=alert.status,
        actor_user_id=user.id,
        note=body.note or "Auto-resolved after acknowledgement.",
        transitioned_at=datetime.now(timezone.utc),
    )
    await alert_repo.save(alert)
    await alert_repo.save_transition(resolve_transition)

    # Auto-close any case linked to this alert
    cases = await db.case.find_many(where={"agentId": alert.agent_id, "status": "open"})
    for case_row in cases:
        raw_ids = case_row.alertIds
        if isinstance(raw_ids, str):
            import json as _json
            try:
                case_alert_ids = _json.loads(raw_ids)
            except Exception:
                case_alert_ids = []
        elif isinstance(raw_ids, list):
            case_alert_ids = raw_ids
        else:
            case_alert_ids = []

        if alert.id in case_alert_ids:
            # Check if all alerts in this case are now resolved
            all_resolved = True
            for linked_id in case_alert_ids:
                if linked_id == alert.id:
                    continue
                linked_alert = await db.alert.find_unique(where={"id": linked_id})
                if linked_alert and linked_alert.status != "resolved":
                    all_resolved = False
                    break

            if all_resolved:
                await db.case.update(
                    where={"id": case_row.id},
                    data={
                        "status": "closed",
                        "resolutionNote": body.note or "All linked alerts resolved.",
                    },
                )

    return _to_response(alert)


@router.post("/{alert_id}/escalate", response_model=AlertResponse)
async def escalate_alert(
    alert_id: str,
    body: AlertTransitionRequest = AlertTransitionRequest(),
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """Escalate an alert. Transition: ACKNOWLEDGED|IN_PROGRESS → ESCALATED."""
    alert_repo = PrismaAlertRepository(db)
    alert = await alert_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        from_status = alert.status
        alert.escalate()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    transition = AlertStateTransition(
        id=str(uuid.uuid4()),
        alert_id=alert.id,
        from_status=from_status,
        to_status=alert.status,
        actor_user_id=user.id,
        note=body.note,
        transitioned_at=datetime.now(timezone.utc),
    )
    await alert_repo.save(alert)
    await alert_repo.save_transition(transition)

    return _to_response(alert)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    body: AlertTransitionRequest = AlertTransitionRequest(),
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """Resolve an alert. Transition: ACKNOWLEDGED|IN_PROGRESS|ESCALATED → RESOLVED."""
    alert_repo = PrismaAlertRepository(db)
    alert = await alert_repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        from_status = alert.status
        alert.resolve(notes=body.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    transition = AlertStateTransition(
        id=str(uuid.uuid4()),
        alert_id=alert.id,
        from_status=from_status,
        to_status=alert.status,
        actor_user_id=user.id,
        note=body.note,
        transitioned_at=datetime.now(timezone.utc),
    )
    await alert_repo.save(alert)
    await alert_repo.save_transition(transition)

    return _to_response(alert)
