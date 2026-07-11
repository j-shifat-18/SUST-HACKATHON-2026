"""
POST /snapshot/{agent_id}
Runs the full pipeline (engines + agents) and returns a SnapshotResponse.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status

from app.agents.pipeline import run_full_pipeline
from app.api.v1.deps import CurrentUser, DBClient, RequestId
from app.db.repositories.prisma_repositories import (
    PrismaAgentRepository,
    PrismaDataFeedRepository,
    PrismaLiquiditySnapshotRepository,
    PrismaTransactionRepository,
)
from app.domain.value_objects import Provider
from app.schemas.liquidity import (
    AnomalyFlagSchema,
    ForecastSchema,
    LiquidityMatrixResponse,
    SnapshotResponse,
)

router = APIRouter(prefix="/snapshot", tags=["Snapshot"])


@router.post("/{agent_id}", response_model=SnapshotResponse)
async def get_snapshot(
    agent_id: str,
    db: DBClient,
    current_user: CurrentUser,
    request_id: RequestId,
):
    """
    Runs the full liquidity intelligence pipeline for the given agent.
    Returns liquidity matrix, forecasts, anomaly flags, and AI advisory.

    Degrades gracefully if data feeds are stale — returns lower-confidence
    result rather than failing silently.
    """
    agent_repo = PrismaAgentRepository(db)
    agent = await agent_repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    snapshot_repo = PrismaLiquiditySnapshotRepository(db)
    snapshot = await snapshot_repo.get_latest(agent_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No liquidity snapshot available for this agent.",
        )

    tx_repo = PrismaTransactionRepository(db)
    since = datetime.utcnow() - timedelta(hours=72)
    transactions = await tx_repo.list_for_agent(agent_id, since=since)

    feed_repo = PrismaDataFeedRepository(db)
    feed_statuses = await feed_repo.list_all()

    # Run full pipeline (engines + AI agents)
    result = await run_full_pipeline(
        agent_id=agent_id,
        snapshot=snapshot,
        transactions=transactions,
        feed_statuses=feed_statuses,
        request_id=request_id,
    )

    # Build response
    m = result.liquidity_matrix
    liquidity_resp = LiquidityMatrixResponse(
        agent_id=m.agent_id,
        physical_cash_bdt=float(m.physical_cash.amount),
        bkash_balance_bdt=float(m.bkash_balance.amount),
        nagad_balance_bdt=float(m.nagad_balance.amount),
        rocket_balance_bdt=float(m.rocket_balance.amount),
        total_liquidity_bdt=float(m.total_liquidity.amount),
        utilization_pct=m.utilization_pct,
        lowest_provider=m.lowest_provider.value,
        is_low=m.is_low,
        is_critical=m.is_critical,
        overall_confidence=m.overall_confidence.value,
        degraded_providers=m.degraded_providers,
        captured_at=snapshot.captured_at,
    )

    from app.core.config import get_settings
    settings = get_settings()
    forecast_responses = [
        ForecastSchema(
            provider=f.provider.value,
            current_balance_bdt=float(f.current_balance.amount),
            predicted_balance_bdt=float(f.predicted_balance_at_horizon.amount),
            depletion_time_hours=f.depletion_time_hours,
            hourly_net_flow_bdt=f.hourly_net_flow,
            confidence=f.confidence.value,
            forecast_hours=settings.forecast_horizon_hours,
        )
        for f in result.forecasts
    ]

    anomaly_schemas = [
        AnomalyFlagSchema(
            id=f"flag_{i}",
            flag_type=a.flag_type.value,
            severity_score=a.severity_score,
            confidence=a.confidence,
            explanation_en=a.explanation_en,
            explanation_bn=a.explanation_bn,
            explanation_banglish=a.explanation_banglish,
            transaction_count=len(a.transaction_group_ids),
            is_reviewed=False,
            created_at=datetime.utcnow(),
        )
        for i, a in enumerate(result.anomalies)
    ]

    return SnapshotResponse(
        request_id=request_id,
        agent_id=agent_id,
        liquidity=liquidity_resp,
        forecasts=forecast_responses,
        anomaly_count=len(anomaly_schemas),
        anomalies=anomaly_schemas,
        agent_advisory=result.agent_response,
        overall_confidence=m.overall_confidence.value,
        generated_at=result.generated_at,
    )
