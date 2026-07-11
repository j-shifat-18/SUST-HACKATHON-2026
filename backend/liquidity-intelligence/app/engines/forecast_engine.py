"""
ForecastEngine — deterministic time-series module.
Uses exponential smoothing (statsmodels) to predict balance depletion.
No AI. Pure computation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

import numpy as np
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

from app.domain.entities import ForecastHorizon, Transaction
from app.domain.value_objects import ConfidenceScore, Money, Provider

MODEL_VERSION = "ses_v1"
MIN_OBSERVATIONS = 6  # need at least this many data points for a valid forecast


@dataclass
class ForecastResult:
    provider: Provider
    current_balance: Money
    predicted_balance_at_horizon: Money
    depletion_time_hours: Optional[float]
    confidence: ConfidenceScore
    hourly_net_flow: float  # negative = draining, positive = growing


def forecast_provider(
    agent_id: str,
    provider: Provider,
    current_balance: Money,
    transactions: list[Transaction],
    horizon_hours: int = 12,
) -> ForecastResult:
    """
    Forecast provider balance at `horizon_hours` in the future.

    Strategy:
    1. Bin transactions into hourly net-flow buckets.
    2. Fit SimpleExpSmoothing on the last N hourly buckets.
    3. Extrapolate forward.
    4. Estimate depletion time by linear regression on trend.

    Returns a ForecastResult. Degrades gracefully with few observations.
    """
    # Filter to this provider only
    provider_txs = [t for t in transactions if t.provider == provider]

    if len(provider_txs) < MIN_OBSERVATIONS:
        # Not enough data — return current balance with low confidence
        return ForecastResult(
            provider=provider,
            current_balance=current_balance,
            predicted_balance_at_horizon=current_balance,
            depletion_time_hours=None,
            confidence=ConfidenceScore(0.3),
            hourly_net_flow=0.0,
        )

    # Build hourly net-flow series
    hourly_flows = _build_hourly_flows(provider_txs)

    # Exponential smoothing on flows
    try:
        model = SimpleExpSmoothing(hourly_flows, initialization_method="estimated")
        fit = model.fit(optimized=True)
        predicted_flows = fit.forecast(horizon_hours)
        mean_flow = float(np.mean(predicted_flows))
    except Exception:
        mean_flow = float(np.mean(hourly_flows)) if hourly_flows else 0.0

    # Predicted balance at horizon
    cumulative_change = mean_flow * horizon_hours
    predicted_amount = max(
        Decimal("0"),
        current_balance.amount + Decimal(str(round(cumulative_change, 2))),
    )
    predicted_balance = Money(predicted_amount)

    # Depletion time estimate
    depletion_hours: Optional[float] = None
    if mean_flow < 0 and current_balance.amount > 0:
        # Divide current balance by rate of drain (hours until zero)
        drain_rate = abs(mean_flow)
        if drain_rate > 0:
            depletion_hours = float(current_balance.amount) / drain_rate

    # Confidence degrades with fewer observations and high variance
    obs_factor = min(1.0, len(provider_txs) / 100)
    variance_factor = max(0.3, 1.0 - (np.std(hourly_flows) / (abs(np.mean(hourly_flows)) + 1e-6)) * 0.1)
    confidence_val = round(obs_factor * float(variance_factor), 2)
    confidence = ConfidenceScore(min(1.0, max(0.1, confidence_val)))

    return ForecastResult(
        provider=provider,
        current_balance=current_balance,
        predicted_balance_at_horizon=predicted_balance,
        depletion_time_hours=depletion_hours,
        confidence=confidence,
        hourly_net_flow=mean_flow,
    )


def forecast_result_to_entity(
    agent_id: str,
    result: ForecastResult,
    horizon_hours: int,
) -> ForecastHorizon:
    return ForecastHorizon(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        provider=result.provider,
        forecast_hours=horizon_hours,
        predicted_balance=result.predicted_balance_at_horizon,
        depletion_time_hours=result.depletion_time_hours,
        confidence=result.confidence,
        model_version=MODEL_VERSION,
        generated_at=datetime.utcnow(),
    )


def _build_hourly_flows(transactions: list[Transaction]) -> list[float]:
    """
    Convert raw transactions into a list of hourly net flows
    (cash_in positive, cash_out negative).
    Sorted ascending by time, binned to 1-hour buckets.
    """
    if not transactions:
        return []

    # Sort ascending
    sorted_txs = sorted(transactions, key=lambda t: t.timestamp)
    start_hour = sorted_txs[0].timestamp.replace(minute=0, second=0, microsecond=0)
    end_hour = sorted_txs[-1].timestamp.replace(minute=0, second=0, microsecond=0)

    # Build hour-indexed dict
    from collections import defaultdict
    hourly: dict[int, float] = defaultdict(float)

    for tx in sorted_txs:
        bucket = int((tx.timestamp - start_hour).total_seconds() // 3600)
        sign = 1.0 if tx.transaction_type.value in ("cash_in", "recharge") else -1.0
        hourly[bucket] += sign * float(tx.amount.amount)

    # Fill gaps with 0
    total_hours = int((end_hour - start_hour).total_seconds() // 3600) + 1
    return [hourly.get(i, 0.0) for i in range(total_hours)]
