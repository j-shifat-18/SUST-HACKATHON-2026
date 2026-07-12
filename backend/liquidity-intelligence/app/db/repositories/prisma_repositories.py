"""
Prisma-based async repository implementations.
Each class implements the matching interface from domain/repositories.py.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from prisma import Prisma
from prisma.models import (
    Agent as AgentModel,
    AgentTraceLog as AgentTraceLogModel,
    Alert as AlertModel,
    AlertStateTransition as AlertStateTransitionModel,
    AnomalyFlag as AnomalyFlagModel,
    Case as CaseModel,
    DataFeedStatus as DataFeedStatusModel,
    ForecastHorizon as ForecastHorizonModel,
    LiquiditySnapshot as LiquiditySnapshotModel,
    Transaction as TransactionModel,
    User as UserModel,
)

from app.domain.entities import (
    AgentEntity,
    AgentTraceLog,
    Alert,
    AlertStateTransition,
    AnomalyFlag,
    Case,
    DataFeedStatus,
    ForecastHorizon,
    LiquiditySnapshot,
    Transaction,
    User,
)
from app.domain.repositories import (
    IAgentRepository,
    IAgentTraceLogRepository,
    IAlertRepository,
    IAnomalyFlagRepository,
    ICaseRepository,
    IDataFeedRepository,
    IForecastRepository,
    ILiquiditySnapshotRepository,
    ITransactionRepository,
    IUserRepository,
)
from app.domain.value_objects import (
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


# ---------------------------------------------------------------------------
# Mapper helpers  (Prisma model → domain entity)
# ---------------------------------------------------------------------------

def _agent(m: AgentModel) -> AgentEntity:
    return AgentEntity(
        id=m.id, name=m.name, phone=m.phone,
        area=m.area, region=m.region,
        is_active=m.isActive, created_at=m.createdAt,
    )


def _tx(m: TransactionModel) -> Transaction:
    return Transaction(
        id=m.id, agent_id=m.agentId,
        provider=Provider(m.provider),
        transaction_type=TransactionType(m.transactionType),
        amount=Money(Decimal(str(m.amount))),
        timestamp=m.timestamp, area=m.area, account_ref=m.accountRef,
        anomaly_flag_id=m.anomalyFlagId,
        metadata=m.metadata if isinstance(m.metadata, dict) else {},
    )


def _snapshot(m: LiquiditySnapshotModel) -> LiquiditySnapshot:
    return LiquiditySnapshot(
        id=m.id, agent_id=m.agentId,
        physical_cash=Money(Decimal(str(m.physicalCash))),
        bkash_balance=Money(Decimal(str(m.bkashBalance))),
        nagad_balance=Money(Decimal(str(m.nagadBalance))),
        rocket_balance=Money(Decimal(str(m.rocketBalance))),
        overall_confidence=ConfidenceScore(m.overallConfidence),
        captured_at=m.capturedAt,
    )


def _forecast(m: ForecastHorizonModel) -> ForecastHorizon:
    return ForecastHorizon(
        id=m.id, agent_id=m.agentId,
        provider=Provider(m.provider),
        forecast_hours=m.forecastHours,
        predicted_balance=Money(Decimal(str(m.predictedBalance))),
        depletion_time_hours=m.depletionTimeHours,
        confidence=ConfidenceScore(m.confidence),
        model_version=m.modelVersion,
        generated_at=m.generatedAt,
    )


def _anomaly(m: AnomalyFlagModel) -> AnomalyFlag:
    return AnomalyFlag(
        id=m.id, transaction_id=m.transactionId,
        transaction_group_ids=m.transactionGroupIds if isinstance(m.transactionGroupIds, list) else [],
        flag_type=AnomalyType(m.flagType),
        severity_score=m.severityScore,
        confidence=ConfidenceScore(m.confidence),
        evidence=m.evidence if isinstance(m.evidence, dict) else {},
        explanation_en=m.explanationEn,
        explanation_bn=m.explanationBn,
        explanation_banglish=m.explanationBanglish,
        review_language=ReviewLanguage(m.reviewLanguage),
        is_reviewed=m.isReviewed,
        created_at=m.createdAt,
    )


def _alert(m: AlertModel) -> Alert:
    return Alert(
        id=m.id, agent_id=m.agentId,
        alert_type=AlertType(m.alertType),
        severity=AlertSeverity(m.severity),
        confidence=ConfidenceScore(m.confidence),
        evidence=m.evidence if isinstance(m.evidence, dict) else {},
        status=AlertStatus(m.status),
        assigned_to_user_id=m.assignedToUserId,
        anomaly_flag_id=m.anomalyFlagId,
        forecast_horizon_id=m.forecastHorizonId,
        notes=m.notes,
        created_at=m.createdAt,
        updated_at=m.updatedAt,
    )


def _transition(m: AlertStateTransitionModel) -> AlertStateTransition:
    return AlertStateTransition(
        id=m.id, alert_id=m.alertId,
        from_status=AlertStatus(m.fromStatus),
        to_status=AlertStatus(m.toStatus),
        actor_user_id=m.actorUserId,
        note=m.note,
        transitioned_at=m.transitionedAt,
    )


def _case(m: CaseModel) -> Case:
    return Case(
        id=m.id, agent_id=m.agentId, title=m.title,
        alert_ids=m.alertIds if isinstance(m.alertIds, list) else [],
        status=m.status,
        resolution_note=m.resolutionNote,
        created_at=m.createdAt, updated_at=m.updatedAt,
    )


def _feed(m: DataFeedStatusModel) -> DataFeedStatus:
    return DataFeedStatus(
        id=m.id, provider=Provider(m.provider),
        last_received_at=m.lastReceivedAt,
        is_healthy=m.isHealthy,
        staleness_threshold_seconds=m.stalenessThresholdSeconds,
    )


def _user(m: UserModel) -> User:
    return User(
        id=m.id, firebase_uid=m.firebaseUid, phone=m.phone,
        name=m.name, role=UserRole(m.role),
        region=m.region, area=m.area,
        is_active=m.isActive, created_at=m.createdAt,
    )


def _trace(m: AgentTraceLogModel) -> AgentTraceLog:
    return AgentTraceLog(
        id=m.id, request_id=m.requestId,
        agent_name=m.agentName,
        input_summary=m.inputSummary,
        output_summary=m.outputSummary,
        tool_calls=m.toolCalls if isinstance(m.toolCalls, list) else [],
        duration_ms=m.durationMs,
        created_at=m.createdAt,
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class PrismaAgentRepository(IAgentRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def get_by_id(self, agent_id: str) -> Optional[AgentEntity]:
        m = await self._db.agent.find_unique(where={"id": agent_id})
        return _agent(m) if m else None

    async def list_all(
        self, area: Optional[str] = None, region: Optional[str] = None
    ) -> list[AgentEntity]:
        where: dict = {"isActive": True}
        if area:
            where["area"] = area
        if region:
            where["region"] = region
        rows = await self._db.agent.find_many(where=where)
        return [_agent(r) for r in rows]

    async def save(self, agent: AgentEntity) -> AgentEntity:
        await self._db.agent.upsert(
            where={"id": agent.id},
            data={
                "create": {
                    "id": agent.id, "name": agent.name, "phone": agent.phone,
                    "area": agent.area, "region": agent.region,
                    "isActive": agent.is_active, "createdAt": agent.created_at,
                },
                "update": {
                    "name": agent.name, "phone": agent.phone,
                    "area": agent.area, "region": agent.region,
                    "isActive": agent.is_active,
                },
            },
        )
        return agent


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class PrismaTransactionRepository(ITransactionRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def get_by_id(self, tx_id: str) -> Optional[Transaction]:
        m = await self._db.transaction.find_unique(where={"id": tx_id})
        return _tx(m) if m else None

    async def list_for_agent(
        self,
        agent_id: str,
        provider: Optional[Provider] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[Transaction]:
        where: dict = {"agentId": agent_id}
        if provider:
            where["provider"] = provider.value
        ts_filter: dict = {}
        if since:
            ts_filter["gte"] = since
        if until:
            ts_filter["lte"] = until
        if ts_filter:
            where["timestamp"] = ts_filter
        rows = await self._db.transaction.find_many(
            where=where,
            order={"timestamp": "desc"},
            take=limit,
        )
        return [_tx(r) for r in rows]

    async def save(self, tx: Transaction) -> Transaction:
        data = {
            "id": tx.id, "agentId": tx.agent_id,
            "provider": tx.provider.value,
            "transactionType": tx.transaction_type.value,
            "amount": float(tx.amount.amount),
            "timestamp": tx.timestamp, "area": tx.area,
            "accountRef": tx.account_ref,
            "anomalyFlagId": tx.anomaly_flag_id,
            "metadata": tx.metadata,
        }
        await self._db.transaction.upsert(
            where={"id": tx.id},
            data={"create": data, "update": {k: v for k, v in data.items() if k != "id"}},
        )
        return tx

    async def bulk_save(self, txs: list[Transaction]) -> int:
        for tx in txs:
            await self.save(tx)
        return len(txs)


# ---------------------------------------------------------------------------
# LiquiditySnapshot
# ---------------------------------------------------------------------------

class PrismaLiquiditySnapshotRepository(ILiquiditySnapshotRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def get_latest(self, agent_id: str) -> Optional[LiquiditySnapshot]:
        row = await self._db.liquiditysnapshot.find_first(
            where={"agentId": agent_id},
            order={"capturedAt": "desc"},
        )
        return _snapshot(row) if row else None

    async def list_for_agent(
        self, agent_id: str, since: Optional[datetime] = None, limit: int = 100
    ) -> list[LiquiditySnapshot]:
        where: dict = {"agentId": agent_id}
        if since:
            where["capturedAt"] = {"gte": since}
        rows = await self._db.liquiditysnapshot.find_many(
            where=where, order={"capturedAt": "desc"}, take=limit
        )
        return [_snapshot(r) for r in rows]

    async def save(self, snapshot: LiquiditySnapshot) -> LiquiditySnapshot:
        data = {
            "id": snapshot.id, "agentId": snapshot.agent_id,
            "physicalCash": float(snapshot.physical_cash.amount),
            "bkashBalance": float(snapshot.bkash_balance.amount),
            "nagadBalance": float(snapshot.nagad_balance.amount),
            "rocketBalance": float(snapshot.rocket_balance.amount),
            "overallConfidence": snapshot.overall_confidence.value,
            "capturedAt": snapshot.captured_at,
        }
        await self._db.liquiditysnapshot.upsert(
            where={"id": snapshot.id},
            data={"create": data, "update": {k: v for k, v in data.items() if k != "id"}},
        )
        return snapshot


# ---------------------------------------------------------------------------
# ForecastHorizon
# ---------------------------------------------------------------------------

class PrismaForecastRepository(IForecastRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def get_latest(self, agent_id: str, provider: Provider) -> Optional[ForecastHorizon]:
        row = await self._db.forecasthorizon.find_first(
            where={"agentId": agent_id, "provider": provider.value},
            order={"generatedAt": "desc"},
        )
        return _forecast(row) if row else None

    async def save(self, forecast: ForecastHorizon) -> ForecastHorizon:
        data = {
            "id": forecast.id, "agentId": forecast.agent_id,
            "provider": forecast.provider.value,
            "forecastHours": forecast.forecast_hours,
            "predictedBalance": float(forecast.predicted_balance.amount),
            "depletionTimeHours": forecast.depletion_time_hours,
            "confidence": forecast.confidence.value,
            "modelVersion": forecast.model_version,
            "generatedAt": forecast.generated_at,
        }
        await self._db.forecasthorizon.upsert(
            where={"id": forecast.id},
            data={"create": data, "update": {k: v for k, v in data.items() if k != "id"}},
        )
        return forecast


# ---------------------------------------------------------------------------
# AnomalyFlag
# ---------------------------------------------------------------------------

class PrismaAnomalyFlagRepository(IAnomalyFlagRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def get_by_id(self, flag_id: str) -> Optional[AnomalyFlag]:
        m = await self._db.anomalyflag.find_unique(where={"id": flag_id})
        return _anomaly(m) if m else None

    async def list_for_agent(
        self, agent_id: str, unreviewed_only: bool = False
    ) -> list[AnomalyFlag]:
        where: dict = {"transactions": {"some": {"agentId": agent_id}}}
        if unreviewed_only:
            where["isReviewed"] = False
        rows = await self._db.anomalyflag.find_many(where=where)
        return [_anomaly(r) for r in rows]

    async def save(self, flag: AnomalyFlag) -> AnomalyFlag:
        data = {
            "id": flag.id, "transactionId": flag.transaction_id,
            "transactionGroupIds": flag.transaction_group_ids,
            "flagType": flag.flag_type.value,
            "severityScore": flag.severity_score,
            "confidence": flag.confidence.value,
            "evidence": flag.evidence,
            "explanationEn": flag.explanation_en,
            "explanationBn": flag.explanation_bn,
            "explanationBanglish": flag.explanation_banglish,
            "reviewLanguage": flag.review_language.value,
            "isReviewed": flag.is_reviewed,
            "createdAt": flag.created_at,
        }
        await self._db.anomalyflag.upsert(
            where={"id": flag.id},
            data={"create": data, "update": {k: v for k, v in data.items() if k != "id"}},
        )
        return flag


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

class PrismaAlertRepository(IAlertRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def get_by_id(self, alert_id: str) -> Optional[Alert]:
        m = await self._db.alert.find_unique(where={"id": alert_id})
        return _alert(m) if m else None

    async def list_for_agent(
        self,
        agent_id: str,
        status: Optional[AlertStatus] = None,
        limit: int = 100,
    ) -> list[Alert]:
        where: dict = {"agentId": agent_id}
        if status:
            where["status"] = status.value
        rows = await self._db.alert.find_many(
            where=where, order={"createdAt": "desc"}, take=limit
        )
        return [_alert(r) for r in rows]

    async def list_open(
        self, region: Optional[str] = None, area: Optional[str] = None
    ) -> list[Alert]:
        agent_filter: dict = {}
        if region:
            agent_filter["region"] = region
        if area:
            agent_filter["area"] = area

        where: dict = {"status": AlertStatus.OPEN.value}
        if agent_filter:
            where["agent"] = {"is": agent_filter}

        rows = await self._db.alert.find_many(
            where=where, order={"createdAt": "desc"}
        )
        return [_alert(r) for r in rows]

    async def save(self, alert: Alert) -> Alert:
        from prisma import Json as PrismaJson
        evidence_val = PrismaJson(alert.evidence) if isinstance(alert.evidence, dict) else alert.evidence
        
        # For update, we just need the changed fields
        update_data = {
            "alertType": alert.alert_type.value,
            "severity": alert.severity.value,
            "confidence": alert.confidence.value,
            "evidence": evidence_val,
            "status": alert.status.value,
            "assignedToUserId": alert.assigned_to_user_id,
            "anomalyFlagId": alert.anomaly_flag_id,
            "forecastHorizonId": alert.forecast_horizon_id,
            "notes": alert.notes,
            "updatedAt": alert.updated_at,
        }
        
        # For create, use relation connect
        create_data = {
            "id": alert.id,
            "agent": {"connect": {"id": alert.agent_id}},
            "alertType": alert.alert_type.value,
            "severity": alert.severity.value,
            "confidence": alert.confidence.value,
            "evidence": evidence_val,
            "status": alert.status.value,
            "assignedToUserId": alert.assigned_to_user_id,
            "anomalyFlagId": alert.anomaly_flag_id,
            "forecastHorizonId": alert.forecast_horizon_id,
            "notes": alert.notes,
            "createdAt": alert.created_at,
            "updatedAt": alert.updated_at,
        }
        
        await self._db.alert.upsert(
            where={"id": alert.id},
            data={"create": create_data, "update": update_data},
        )
        return alert

    async def save_transition(
        self, transition: AlertStateTransition
    ) -> AlertStateTransition:
        await self._db.alertstatetransition.create(
            data={
                "id": transition.id, "alertId": transition.alert_id,
                "fromStatus": transition.from_status.value,
                "toStatus": transition.to_status.value,
                "actorUserId": transition.actor_user_id,
                "note": transition.note,
                "transitionedAt": transition.transitioned_at,
            }
        )
        return transition


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------

class PrismaCaseRepository(ICaseRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def get_by_id(self, case_id: str) -> Optional[Case]:
        m = await self._db.case.find_unique(where={"id": case_id})
        return _case(m) if m else None

    async def list_for_agent(self, agent_id: str) -> list[Case]:
        rows = await self._db.case.find_many(
            where={"agentId": agent_id}, order={"createdAt": "desc"}
        )
        return [_case(r) for r in rows]

    async def save(self, case: Case) -> Case:
        data = {
            "id": case.id, "agentId": case.agent_id, "title": case.title,
            "alertIds": case.alert_ids, "status": case.status,
            "resolutionNote": case.resolution_note,
            "createdAt": case.created_at, "updatedAt": case.updated_at,
        }
        await self._db.case.upsert(
            where={"id": case.id},
            data={"create": data, "update": {k: v for k, v in data.items() if k != "id"}},
        )
        return case


# ---------------------------------------------------------------------------
# DataFeedStatus
# ---------------------------------------------------------------------------

class PrismaDataFeedRepository(IDataFeedRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def get_status(self, provider: Provider) -> Optional[DataFeedStatus]:
        m = await self._db.datafeedstatus.find_unique(
            where={"provider": provider.value}
        )
        return _feed(m) if m else None

    async def list_all(self) -> list[DataFeedStatus]:
        rows = await self._db.datafeedstatus.find_many()
        return [_feed(r) for r in rows]

    async def save(self, status: DataFeedStatus) -> DataFeedStatus:
        data = {
            "id": status.id, "provider": status.provider.value,
            "lastReceivedAt": status.last_received_at,
            "isHealthy": status.is_healthy,
            "stalenessThresholdSeconds": status.staleness_threshold_seconds,
        }
        await self._db.datafeedstatus.upsert(
            where={"provider": status.provider.value},
            data={"create": data, "update": {k: v for k, v in data.items() if k not in ("id", "provider")}},
        )
        return status


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class PrismaUserRepository(IUserRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        m = await self._db.user.find_unique(where={"id": user_id})
        return _user(m) if m else None

    async def get_by_firebase_uid(self, uid: str) -> Optional[User]:
        m = await self._db.user.find_unique(where={"firebaseUid": uid})
        return _user(m) if m else None

    async def save(self, user: User) -> User:
        data = {
            "id": user.id, "firebaseUid": user.firebase_uid,
            "phone": user.phone, "name": user.name,
            "role": user.role.value, "region": user.region,
            "area": user.area, "isActive": user.is_active,
            "createdAt": user.created_at,
        }
        await self._db.user.upsert(
            where={"id": user.id},
            data={"create": data, "update": {k: v for k, v in data.items() if k != "id"}},
        )
        return user


# ---------------------------------------------------------------------------
# AgentTraceLog
# ---------------------------------------------------------------------------

class PrismaAgentTraceLogRepository(IAgentTraceLogRepository):
    def __init__(self, db: Prisma) -> None:
        self._db = db

    async def save(self, trace: AgentTraceLog) -> AgentTraceLog:
        await self._db.agenttracelog.create(
            data={
                "id": trace.id, "requestId": trace.request_id,
                "agentName": trace.agent_name,
                "inputSummary": trace.input_summary,
                "outputSummary": trace.output_summary,
                "toolCalls": trace.tool_calls,
                "durationMs": trace.duration_ms,
                "createdAt": trace.created_at,
            }
        )
        return trace

    async def list_by_request(self, request_id: str) -> list[AgentTraceLog]:
        rows = await self._db.agenttracelog.find_many(
            where={"requestId": request_id}
        )
        return [_trace(r) for r in rows]
