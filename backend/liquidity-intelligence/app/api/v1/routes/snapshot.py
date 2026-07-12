"""
POST /api/v1/snapshot/{agent_id}
Runs the full liquidity intelligence pipeline for a given agent.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from prisma import Prisma

from app.api.v1.deps import get_current_user, get_db
from app.db.repositories.prisma_repositories import (
    PrismaAgentRepository,
    PrismaLiquiditySnapshotRepository,
    PrismaTransactionRepository,
)
from app.domain.entities import User
from app.schemas.liquidity import (
    AnomalyFlagSchema,
    ForecastSchema,
    LiquidityMatrixResponse,
    SnapshotResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Snapshot"])


@router.post("/snapshot/{agent_id}", response_model=SnapshotResponse)
async def create_snapshot(
    agent_id: str,
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """
    Run the full liquidity intelligence pipeline for a given agent.
    Computes real-time liquidity from latest snapshot + recent transactions,
    generates forecasts from actual transaction flow.
    """
    request_id = str(uuid.uuid4())

    # 1. Validate agent exists
    agent_repo = PrismaAgentRepository(db)
    agent = await agent_repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    # 2. Load latest snapshot as baseline
    snapshot_repo = PrismaLiquiditySnapshotRepository(db)
    snapshot = await snapshot_repo.get_latest(agent_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No liquidity snapshot available for agent {agent_id}",
        )

    # 3. Load transactions SINCE the snapshot was captured to compute real-time balance
    tx_repo = PrismaTransactionRepository(db)
    # Use 1 second before snapshot to avoid missing transactions at the exact boundary
    since_time = snapshot.captured_at - timedelta(seconds=1)
    txs_since_snapshot = await tx_repo.list_for_agent(agent_id, since=since_time)

    # 4. Compute real-time balances by applying transactions to snapshot baseline
    physical = float(snapshot.physical_cash.amount)
    bkash = float(snapshot.bkash_balance.amount)
    nagad = float(snapshot.nagad_balance.amount)
    rocket = float(snapshot.rocket_balance.amount)

    for tx in txs_since_snapshot:
        amt = float(tx.amount.amount)
        provider = tx.provider.value

        if tx.transaction_type.value == "cash_in":
            # Cash-in: customer deposits cash → agent gets physical cash, gives e-money
            physical += amt
            if provider == "bkash":
                bkash -= amt
            elif provider == "nagad":
                nagad -= amt
            elif provider == "rocket":
                rocket -= amt
        elif tx.transaction_type.value == "cash_out":
            # Cash-out: customer withdraws cash → agent gives physical cash, gets e-money
            physical -= amt
            if provider == "bkash":
                bkash += amt
            elif provider == "nagad":
                nagad += amt
            elif provider == "rocket":
                rocket += amt

    # Clamp to non-negative
    physical = max(0, physical)
    bkash = max(0, bkash)
    nagad = max(0, nagad)
    rocket = max(0, rocket)

    total = physical + bkash + nagad + rocket

    # Determine lowest provider
    balances = {
        "physical": physical,
        "bkash": bkash,
        "nagad": nagad,
        "rocket": rocket,
    }
    lowest_provider = min(balances, key=balances.get)
    lowest_balance = balances[lowest_provider]

    # Thresholds
    is_low = (lowest_balance / total * 100) < 20.0 if total > 0 else False
    is_critical = (lowest_balance / total * 100) < 10.0 if total > 0 else False

    # Utilization: % in provider wallets vs total
    wallet_total = bkash + nagad + rocket
    utilization_pct = (wallet_total / total * 100) if total > 0 else 0.0

    liquidity_response = LiquidityMatrixResponse(
        agent_id=agent_id,
        physical_cash_bdt=physical,
        bkash_balance_bdt=bkash,
        nagad_balance_bdt=nagad,
        rocket_balance_bdt=rocket,
        total_liquidity_bdt=total,
        utilization_pct=round(utilization_pct, 1),
        lowest_provider=lowest_provider,
        is_low=is_low,
        is_critical=is_critical,
        overall_confidence=snapshot.overall_confidence.value,
        degraded_providers=[],
        captured_at=datetime.now(timezone.utc),
    )

    # 5. Compute forecasts from last 24h hourly net flows
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    txs_24h = await tx_repo.list_for_agent(agent_id, since=since_24h)

    forecasts: list[ForecastSchema] = []
    for provider_name, balance in balances.items():
        # Calculate hourly net flow for this provider
        provider_txs = [t for t in txs_24h if t.provider.value == provider_name]
        net_flow = 0.0
        for tx in provider_txs:
            amt = float(tx.amount.amount)
            if tx.transaction_type.value == "cash_out":
                net_flow += amt  # e-money increases
            elif tx.transaction_type.value == "cash_in":
                net_flow -= amt  # e-money decreases

        hours_span = 24.0
        hourly_net_flow = net_flow / hours_span if hours_span > 0 else 0

        predicted = balance + (hourly_net_flow * 12)  # 12h forecast
        predicted = max(0, predicted)

        depletion_hours = None
        if hourly_net_flow < 0 and balance > 0:
            depletion_hours = round(balance / abs(hourly_net_flow), 1)
            if depletion_hours > 72:
                depletion_hours = None

        confidence = 0.75 if len(provider_txs) > 10 else 0.5

        forecasts.append(
            ForecastSchema(
                provider=provider_name,
                current_balance_bdt=balance,
                predicted_balance_bdt=round(predicted, 0),
                depletion_time_hours=depletion_hours,
                hourly_net_flow_bdt=round(hourly_net_flow, 0),
                confidence=confidence,
                forecast_hours=12,
            )
        )

    # 6. Check for anomalies from DB
    anomaly_count = await db.anomalyflag.count(
        where={"transactionId": {"in": [t.id for t in txs_since_snapshot[:50]]}}
    ) if txs_since_snapshot else 0

    return SnapshotResponse(
        request_id=request_id,
        agent_id=agent_id,
        liquidity=liquidity_response,
        forecasts=forecasts,
        anomaly_count=anomaly_count,
        anomalies=[],
        agent_advisory={
            "operational_status": "NORMAL" if not is_critical else "CRITICAL",
            "summary": f"Real-time liquidity computed from {len(txs_since_snapshot)} transactions since last snapshot.",
            "anomaly_summary": f"{anomaly_count} anomalies detected." if anomaly_count else "No anomalies detected.",
            "recommendations": [f"Monitor {lowest_provider} — lowest at ৳{lowest_balance:,.0f}"] if is_low else [],
            "executive_summary": f"Total liquidity: ৳{total:,.0f}. Lowest: {lowest_provider}.",
        },
        overall_confidence=snapshot.overall_confidence.value,
        generated_at=datetime.now(timezone.utc),
    )
