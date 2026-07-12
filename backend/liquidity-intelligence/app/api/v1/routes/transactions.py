"""
POST /api/v1/transactions — ingest a new transaction and run anomaly detection.
Automatically creates alerts if anomalies are detected.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from prisma import Prisma
from prisma import Json
from pydantic import BaseModel, Field

from app.api.v1.deps import get_current_user, get_db
from app.core.config import get_settings
from app.domain.entities import User
from app.engines.anomaly_engine import (
    AnomalyResult,
    TransactionRecord,
    run_all_detections,
)
from app.engines.alert_service import create_alert_from_anomaly, create_liquidity_alert

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/transactions", tags=["Transactions"])
settings = get_settings()


class TransactionCreateRequest(BaseModel):
    agent_id: str
    provider: str = Field(..., pattern="^(bkash|nagad|rocket|physical)$")
    transaction_type: str = Field(..., pattern="^(cash_in|cash_out|transfer|recharge)$")
    amount: float = Field(..., gt=0)
    account_ref: str = Field(..., min_length=3)
    area: Optional[str] = None
    metadata: Optional[dict] = None


class BalanceSetRequest(BaseModel):
    """Set the current balance for a provider (initial setup or manual correction)."""
    agent_id: str
    physical_cash: Optional[float] = None
    bkash_balance: Optional[float] = None
    nagad_balance: Optional[float] = None
    rocket_balance: Optional[float] = None


class TransactionResponse(BaseModel):
    id: str
    agent_id: str
    provider: str
    transaction_type: str
    amount: float
    timestamp: str
    account_ref: str
    alerts_generated: int = 0
    anomalies_detected: list[str] = []


class TransactionHistoryItem(BaseModel):
    id: str
    provider: str
    transaction_type: str
    amount: float
    timestamp: str
    account_ref: str


@router.get("", response_model=list[TransactionHistoryItem])
async def list_transactions(
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """Get recent transactions for the user's agent, sorted by time descending."""
    # Find agent for this user (agent_id = user_id in our setup)
    agent = await db.agent.find_unique(where={"id": user.id})
    if not agent:
        # Try to find by region/area
        agents = await db.agent.find_many(
            where={"region": user.region, "area": user.area, "isActive": True},
            take=1,
        )
        if not agents:
            return []
        agent = agents[0]

    rows = await db.transaction.find_many(
        where={"agentId": agent.id},
        order={"timestamp": "desc"},
        take=limit,
    )

    return [
        TransactionHistoryItem(
            id=r.id,
            provider=r.provider,
            transaction_type=r.transactionType,
            amount=float(r.amount),
            timestamp=r.timestamp.isoformat(),
            account_ref=r.accountRef,
        )
        for r in rows
    ]


@router.post("/balance", status_code=status.HTTP_200_OK)
async def set_balance(
    body: BalanceSetRequest,
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """
    Set or update the agent's current balance for each provider.
    Creates a new liquidity snapshot. This is used for:
    - Initial setup (how much money the agent has)
    - Manual corrections (physical cash count)
    
    Only provided fields are updated; omitted fields keep the last known value.
    """
    agent = await db.agent.find_unique(where={"id": body.agent_id})
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {body.agent_id} not found")

    now = datetime.now(timezone.utc)

    # Get the latest snapshot as a baseline (if exists)
    latest = await db.liquiditysnapshot.find_first(
        where={"agentId": body.agent_id},
        order={"capturedAt": "desc"},
    )

    physical = body.physical_cash if body.physical_cash is not None else (float(latest.physicalCash) if latest else 0)
    bkash = body.bkash_balance if body.bkash_balance is not None else (float(latest.bkashBalance) if latest else 0)
    nagad = body.nagad_balance if body.nagad_balance is not None else (float(latest.nagadBalance) if latest else 0)
    rocket = body.rocket_balance if body.rocket_balance is not None else (float(latest.rocketBalance) if latest else 0)

    # Create new snapshot — set capturedAt slightly in the future to ensure
    # it becomes the definitive baseline and no old transactions bleed in
    snapshot_time = now + timedelta(seconds=2)
    snapshot_id = str(uuid.uuid4())
    await db.liquiditysnapshot.create(
        data={
            "id": snapshot_id,
            "agentId": body.agent_id,
            "physicalCash": physical,
            "bkashBalance": bkash,
            "nagadBalance": nagad,
            "rocketBalance": rocket,
            "overallConfidence": 1.0,
            "capturedAt": snapshot_time,
        }
    )

    total = physical + bkash + nagad + rocket
    return {
        "snapshot_id": snapshot_id,
        "agent_id": body.agent_id,
        "physical_cash_bdt": physical,
        "bkash_balance_bdt": bkash,
        "nagad_balance_bdt": nagad,
        "rocket_balance_bdt": rocket,
        "total_liquidity_bdt": total,
        "captured_at": now.isoformat(),
    }


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    body: TransactionCreateRequest,
    user: User = Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    """
    Ingest a new transaction. Automatically runs:
    1. Anomaly detection (velocity spike, splitting, circular flow)
    2. Liquidity threshold check
    3. Alert generation with AI advisory if anomalies found
    """
    now = datetime.now(timezone.utc)
    tx_id = str(uuid.uuid4())

    # Verify agent exists
    agent = await db.agent.find_unique(where={"id": body.agent_id})
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {body.agent_id} not found")

    # Store the transaction
    await db.transaction.create(
        data={
            "id": tx_id,
            "agentId": body.agent_id,
            "provider": body.provider,
            "transactionType": body.transaction_type,
            "amount": float(body.amount),
            "timestamp": now,
            "area": body.area or agent.area,
            "accountRef": body.account_ref,
            "metadata": Json(json.dumps(body.metadata or {})),
        }
    )

    # --- Run anomaly detection pipeline ---
    # Load recent transactions for this agent (last 24h for analysis)
    since = now - timedelta(hours=24)
    recent_rows = await db.transaction.find_many(
        where={"agentId": body.agent_id, "timestamp": {"gte": since}},
        order={"timestamp": "desc"},
        take=500,
    )

    # Convert to engine format
    tx_records = [
        TransactionRecord(
            id=r.id,
            agent_id=r.agentId,
            provider=r.provider,
            transaction_type=r.transactionType,
            amount=float(r.amount),
            timestamp=r.timestamp,
            account_ref=r.accountRef,
        )
        for r in recent_rows
    ]

    # Run detection
    anomalies = run_all_detections(tx_records)

    # Get user language for advisory generation
    user_row = await db.user.find_unique(where={"id": user.id})
    user_language = user_row.language if user_row else "en"

    # Get latest snapshot for context
    snapshot_info = None
    latest_snapshot = await db.liquiditysnapshot.find_first(
        where={"agentId": body.agent_id},
        order={"capturedAt": "desc"},
    )
    if latest_snapshot:
        snapshot_info = {
            "physical_cash": float(latest_snapshot.physicalCash),
            "bkash": float(latest_snapshot.bkashBalance),
            "nagad": float(latest_snapshot.nagadBalance),
            "rocket": float(latest_snapshot.rocketBalance),
            "total": float(latest_snapshot.physicalCash + latest_snapshot.bkashBalance + latest_snapshot.nagadBalance + latest_snapshot.rocketBalance),
        }

    alerts_generated = 0
    anomaly_types = []

    for anomaly in anomalies:
        # Check if a similar alert already exists (within last hour for same type)
        one_hour_ago = now - timedelta(hours=1)
        existing = await db.alert.find_first(
            where={
                "agentId": body.agent_id,
                "alertType": "anomaly_detected",
                "status": "open",
                "createdAt": {"gte": one_hour_ago},
            }
        )

        if existing:
            # Don't duplicate — skip
            continue

        # Create alert with AI advisory baked in
        alert_data = create_alert_from_anomaly(
            anomaly=anomaly,
            agent_id=body.agent_id,
            agent_name=agent.name,
            user_language=user_language,
            snapshot_info=snapshot_info,
        )

        # Store anomaly flag
        anomaly_flag_id = str(uuid.uuid4())
        await db.anomalyflag.create(
            data={
                "id": anomaly_flag_id,
                "transactionId": tx_id,
                "transactionGroupIds": Json(json.dumps(anomaly.transaction_ids)),
                "flagType": anomaly.flag_type,
                "severityScore": anomaly.severity_score,
                "confidence": anomaly.confidence,
                "evidence": Json(json.dumps(anomaly.evidence, default=str)),
                "explanationEn": alert_data["notes"] if user_language == "en" else "",
                "explanationBn": alert_data["notes"] if user_language in ("bn", "Bengali", "Both") else "",
                "explanationBanglish": alert_data["notes"] if user_language in ("banglish", "Banglish") else "",
                "reviewLanguage": user_language if user_language in ("en", "bn", "banglish") else "en",
                "isReviewed": False,
                "createdAt": now,
            }
        )

        # Store alert
        await db.alert.create(
            data={
                "id": alert_data["id"],
                "agentId": body.agent_id,
                "alertType": alert_data["alert_type"],
                "severity": alert_data["severity"],
                "confidence": alert_data["confidence"],
                "evidence": Json(json.dumps(alert_data["evidence"], default=str)),
                "status": "open",
                "anomalyFlagId": anomaly_flag_id,
                "notes": alert_data["notes"],
                "createdAt": alert_data["created_at"],
                "updatedAt": alert_data["updated_at"],
            }
        )

        alerts_generated += 1
        anomaly_types.append(anomaly.flag_type)

    # --- Check liquidity thresholds ---
    if latest_snapshot and body.transaction_type == "cash_out":
        total = snapshot_info["total"]
        # Simulate the balance drop from this transaction
        provider_key = body.provider
        provider_balance = snapshot_info.get(provider_key, snapshot_info.get("physical_cash", 0))
        new_balance = max(0, provider_balance - body.amount)

        low_threshold = settings.low_liquidity_threshold_pct
        critical_threshold = settings.critical_liquidity_threshold_pct

        pct_of_total = (new_balance / total * 100) if total > 0 else 0

        if pct_of_total < critical_threshold:
            # Check if critical alert already exists
            existing_critical = await db.alert.find_first(
                where={
                    "agentId": body.agent_id,
                    "alertType": "liquidity_critical",
                    "status": {"in": ["open", "acknowledged"]},
                }
            )
            if not existing_critical:
                liq_alert = create_liquidity_alert(
                    agent_id=body.agent_id,
                    agent_name=agent.name,
                    user_language=user_language,
                    is_critical=True,
                    lowest_provider=provider_key,
                    lowest_balance=new_balance,
                    total_liquidity=total,
                    snapshot_info=snapshot_info,
                )
                await db.alert.create(
                    data={
                        "id": liq_alert["id"],
                        "agentId": body.agent_id,
                        "alertType": liq_alert["alert_type"],
                        "severity": liq_alert["severity"],
                        "confidence": liq_alert["confidence"],
                        "evidence": Json(json.dumps(liq_alert["evidence"], default=str)),
                        "status": "open",
                        "notes": liq_alert["notes"],
                        "createdAt": liq_alert["created_at"],
                        "updatedAt": liq_alert["updated_at"],
                    }
                )
                alerts_generated += 1
                anomaly_types.append("liquidity_critical")

        elif pct_of_total < low_threshold:
            existing_low = await db.alert.find_first(
                where={
                    "agentId": body.agent_id,
                    "alertType": {"in": ["liquidity_low", "liquidity_critical"]},
                    "status": {"in": ["open", "acknowledged"]},
                }
            )
            if not existing_low:
                liq_alert = create_liquidity_alert(
                    agent_id=body.agent_id,
                    agent_name=agent.name,
                    user_language=user_language,
                    is_critical=False,
                    lowest_provider=provider_key,
                    lowest_balance=new_balance,
                    total_liquidity=total,
                    snapshot_info=snapshot_info,
                )
                await db.alert.create(
                    data={
                        "id": liq_alert["id"],
                        "agentId": body.agent_id,
                        "alertType": liq_alert["alert_type"],
                        "severity": liq_alert["severity"],
                        "confidence": liq_alert["confidence"],
                        "evidence": Json(json.dumps(liq_alert["evidence"], default=str)),
                        "status": "open",
                        "notes": liq_alert["notes"],
                        "createdAt": liq_alert["created_at"],
                        "updatedAt": liq_alert["updated_at"],
                    }
                )
                alerts_generated += 1
                anomaly_types.append("liquidity_low")

    return TransactionResponse(
        id=tx_id,
        agent_id=body.agent_id,
        provider=body.provider,
        transaction_type=body.transaction_type,
        amount=body.amount,
        timestamp=now.isoformat(),
        account_ref=body.account_ref,
        alerts_generated=alerts_generated,
        anomalies_detected=anomaly_types,
    )
