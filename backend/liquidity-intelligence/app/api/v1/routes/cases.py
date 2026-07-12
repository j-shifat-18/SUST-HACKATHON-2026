"""
GET /api/v1/cases — list cases for the user's region
GET /api/v1/cases/{case_id} — get case with audit timeline
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from prisma import Prisma
from pydantic import BaseModel

from app.api.v1.deps import get_current_user, get_db
from app.domain.entities import User

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/cases", tags=["Cases"])


class CaseTimelineEntry(BaseModel):
    time: str
    action: str
    actor: str
    notes: str


class CaseResponse(BaseModel):
    id: str
    agent_id: str
    title: str
    alert_ids: list[str]
    status: str
    resolution_note: str
    created_at: datetime
    updated_at: datetime
    timeline: list[CaseTimelineEntry] = []


class CaseListResponse(BaseModel):
    cases: list[CaseResponse]
    total: int


@router.get("", response_model=CaseListResponse)
async def list_cases(
    status_filter: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """List cases scoped to the user's region/area."""
    where: dict = {}
    
    if status_filter and status_filter != "all":
        where["status"] = status_filter
    
    # Scope to user's region
    agent_filter: dict = {}
    if user.region:
        agent_filter["region"] = user.region
    if user.area:
        agent_filter["area"] = user.area
    if agent_filter:
        where["agent"] = {"is": agent_filter}
    
    rows = await db.case.find_many(
        where=where,
        order={"createdAt": "desc"},
        take=50,
    )
    
    cases = []
    for row in rows:
        # Build timeline from alert state transitions linked to this case
        timeline = []
        raw_ids = row.alertIds
        if isinstance(raw_ids, str):
            import json as _json
            try:
                alert_ids = _json.loads(raw_ids)
            except Exception:
                alert_ids = []
        elif isinstance(raw_ids, list):
            alert_ids = raw_ids
        else:
            alert_ids = []
        
        # Add case creation event
        timeline.append(CaseTimelineEntry(
            time=row.createdAt.strftime("%H:%M"),
            action="Case Created",
            actor="System",
            notes=f"Auto-generated from {len(alert_ids)} linked alert(s).",
        ))
        
        # Get transitions for linked alerts
        if alert_ids:
            transitions = await db.alertstatetransition.find_many(
                where={"alertId": {"in": alert_ids}},
                order={"transitionedAt": "asc"},
            )
            for t in transitions:
                # Get actor name
                actor_name = "System"
                if t.actorUserId:
                    actor_user = await db.user.find_unique(where={"id": t.actorUserId})
                    if actor_user:
                        actor_name = actor_user.name
                
                timeline.append(CaseTimelineEntry(
                    time=t.transitionedAt.strftime("%H:%M"),
                    action=f"{t.fromStatus} → {t.toStatus}",
                    actor=actor_name,
                    notes=t.note or f"Alert status changed to {t.toStatus}.",
                ))
        
        # Add resolution if closed
        if row.status == "closed" and row.resolutionNote:
            timeline.append(CaseTimelineEntry(
                time=row.updatedAt.strftime("%H:%M"),
                action="Case Closed",
                actor="System",
                notes=row.resolutionNote,
            ))
        
        cases.append(CaseResponse(
            id=row.id,
            agent_id=row.agentId,
            title=row.title,
            alert_ids=alert_ids,
            status=row.status,
            resolution_note=row.resolutionNote or "",
            created_at=row.createdAt,
            updated_at=row.updatedAt,
            timeline=timeline,
        ))
    
    return CaseListResponse(cases=cases, total=len(cases))


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """Get a single case with full audit timeline."""
    row = await db.case.find_unique(where={"id": case_id})
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    
    raw_ids = row.alertIds
    if isinstance(raw_ids, str):
        import json as _json
        try:
            alert_ids = _json.loads(raw_ids)
        except Exception:
            alert_ids = []
    elif isinstance(raw_ids, list):
        alert_ids = raw_ids
    else:
        alert_ids = []
    timeline = []
    
    timeline.append(CaseTimelineEntry(
        time=row.createdAt.strftime("%H:%M"),
        action="Case Created",
        actor="System",
        notes=f"Auto-generated from {len(alert_ids)} linked alert(s).",
    ))
    
    if alert_ids:
        transitions = await db.alertstatetransition.find_many(
            where={"alertId": {"in": alert_ids}},
            order={"transitionedAt": "asc"},
        )
        for t in transitions:
            actor_name = "System"
            if t.actorUserId:
                actor_user = await db.user.find_unique(where={"id": t.actorUserId})
                if actor_user:
                    actor_name = actor_user.name
            
            timeline.append(CaseTimelineEntry(
                time=t.transitionedAt.strftime("%H:%M"),
                action=f"{t.fromStatus} → {t.toStatus}",
                actor=actor_name,
                notes=t.note or f"Alert status changed to {t.toStatus}.",
            ))
    
    if row.status == "closed" and row.resolutionNote:
        timeline.append(CaseTimelineEntry(
            time=row.updatedAt.strftime("%H:%M"),
            action="Case Closed",
            actor="System",
            notes=row.resolutionNote,
        ))
    
    return CaseResponse(
        id=row.id,
        agent_id=row.agentId,
        title=row.title,
        alert_ids=alert_ids,
        status=row.status,
        resolution_note=row.resolutionNote or "",
        created_at=row.createdAt,
        updated_at=row.updatedAt,
        timeline=timeline,
    )
