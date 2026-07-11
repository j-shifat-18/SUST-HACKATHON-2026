"""
Alert lifecycle endpoints:
  GET  /alerts                     — list open alerts
  GET  /alerts/{id}                — get single alert
  POST /alerts/{id}/acknowledge    — acknowledge
  POST /alerts/{id}/escalate       — escalate
  POST /alerts/{id}/resolve        — resolve
All state transitions write to the audit trail.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.v1.deps import CurrentUser, DBClient, RequestId
from app.db.repositories.prisma_repositories import PrismaAlertRepository
from app.domain.value_objects import AlertStatus
from app.engines.alert_service import transition_alert
from app.schemas.alerts import AlertListResponse, AlertResponse, AlertTransitionRequest

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _to_schema(alert) -> AlertResponse:
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
    db: DBClient,
    current_user: CurrentUser,
    status_filter: str = "open",
    agent_id: str | None = None,
):
    """List alerts. Defaults to open alerts. Filter by agent_id or status."""
    repo = PrismaAlertRepository(db)

    try:
        parsed_status = AlertStatus(status_filter)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    if agent_id:
        alerts = await repo.list_for_agent(agent_id, status=parsed_status)
    else:
        # Scope by RBAC role
        region = current_user.region
        area = current_user.area
        alerts = await repo.list_open(region=region, area=area)

    return AlertListResponse(alerts=[_to_schema(a) for a in alerts], total=len(alerts))


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, db: DBClient, current_user: CurrentUser):
    repo = PrismaAlertRepository(db)
    alert = await repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _to_schema(alert)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    body: AlertTransitionRequest,
    db: DBClient,
    current_user: CurrentUser,
):
    repo = PrismaAlertRepository(db)
    alert = await repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        updated_alert, transition = transition_alert(
            alert, AlertStatus.ACKNOWLEDGED, current_user.id, body.note
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await repo.save(updated_alert)
    await repo.save_transition(transition)
    return _to_schema(updated_alert)


@router.post("/{alert_id}/escalate", response_model=AlertResponse)
async def escalate_alert(
    alert_id: str,
    body: AlertTransitionRequest,
    db: DBClient,
    current_user: CurrentUser,
):
    repo = PrismaAlertRepository(db)
    alert = await repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        updated_alert, transition = transition_alert(
            alert, AlertStatus.ESCALATED, current_user.id, body.note
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await repo.save(updated_alert)
    await repo.save_transition(transition)
    return _to_schema(updated_alert)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    body: AlertTransitionRequest,
    db: DBClient,
    current_user: CurrentUser,
):
    repo = PrismaAlertRepository(db)
    alert = await repo.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        updated_alert, transition = transition_alert(
            alert, AlertStatus.RESOLVED, current_user.id, body.note
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await repo.save(updated_alert)
    await repo.save_transition(transition)
    return _to_schema(updated_alert)
