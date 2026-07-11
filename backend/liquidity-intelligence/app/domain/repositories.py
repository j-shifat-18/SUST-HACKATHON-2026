"""
Repository interfaces (abstract base classes) — domain layer.
Concrete implementations live in infrastructure/repositories/.
Zero framework imports.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from .entities import (
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
from .value_objects import AlertStatus, Provider


class IAgentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, agent_id: str) -> Optional[AgentEntity]: ...

    @abstractmethod
    async def list_all(self, area: Optional[str] = None, region: Optional[str] = None) -> list[AgentEntity]: ...

    @abstractmethod
    async def save(self, agent: AgentEntity) -> AgentEntity: ...


class ITransactionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tx_id: str) -> Optional[Transaction]: ...

    @abstractmethod
    async def list_for_agent(
        self,
        agent_id: str,
        provider: Optional[Provider] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[Transaction]: ...

    @abstractmethod
    async def save(self, tx: Transaction) -> Transaction: ...

    @abstractmethod
    async def bulk_save(self, txs: list[Transaction]) -> int: ...


class ILiquiditySnapshotRepository(ABC):
    @abstractmethod
    async def get_latest(self, agent_id: str) -> Optional[LiquiditySnapshot]: ...

    @abstractmethod
    async def list_for_agent(
        self, agent_id: str, since: Optional[datetime] = None, limit: int = 100
    ) -> list[LiquiditySnapshot]: ...

    @abstractmethod
    async def save(self, snapshot: LiquiditySnapshot) -> LiquiditySnapshot: ...


class IForecastRepository(ABC):
    @abstractmethod
    async def get_latest(self, agent_id: str, provider: Provider) -> Optional[ForecastHorizon]: ...

    @abstractmethod
    async def save(self, forecast: ForecastHorizon) -> ForecastHorizon: ...


class IAnomalyFlagRepository(ABC):
    @abstractmethod
    async def get_by_id(self, flag_id: str) -> Optional[AnomalyFlag]: ...

    @abstractmethod
    async def list_for_agent(self, agent_id: str, unreviewed_only: bool = False) -> list[AnomalyFlag]: ...

    @abstractmethod
    async def save(self, flag: AnomalyFlag) -> AnomalyFlag: ...


class IAlertRepository(ABC):
    @abstractmethod
    async def get_by_id(self, alert_id: str) -> Optional[Alert]: ...

    @abstractmethod
    async def list_for_agent(
        self,
        agent_id: str,
        status: Optional[AlertStatus] = None,
        limit: int = 100,
    ) -> list[Alert]: ...

    @abstractmethod
    async def list_open(self, region: Optional[str] = None, area: Optional[str] = None) -> list[Alert]: ...

    @abstractmethod
    async def save(self, alert: Alert) -> Alert: ...

    @abstractmethod
    async def save_transition(self, transition: AlertStateTransition) -> AlertStateTransition: ...


class ICaseRepository(ABC):
    @abstractmethod
    async def get_by_id(self, case_id: str) -> Optional[Case]: ...

    @abstractmethod
    async def list_for_agent(self, agent_id: str) -> list[Case]: ...

    @abstractmethod
    async def save(self, case: Case) -> Case: ...


class IDataFeedRepository(ABC):
    @abstractmethod
    async def get_status(self, provider: Provider) -> Optional[DataFeedStatus]: ...

    @abstractmethod
    async def list_all(self) -> list[DataFeedStatus]: ...

    @abstractmethod
    async def save(self, status: DataFeedStatus) -> DataFeedStatus: ...


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    async def get_by_firebase_uid(self, uid: str) -> Optional[User]: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...


class IAgentTraceLogRepository(ABC):
    @abstractmethod
    async def save(self, trace: AgentTraceLog) -> AgentTraceLog: ...

    @abstractmethod
    async def list_by_request(self, request_id: str) -> list[AgentTraceLog]: ...
