"""
LiquidityEngine — deterministic module.
Aggregates physical cash + per-provider balances.
Detects threshold breaches and computes liquidity ratios.
No AI. No framework imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities import DataFeedStatus, LiquiditySnapshot
from app.domain.value_objects import ConfidenceScore, Money, Provider


@dataclass
class LiquidityMatrix:
    """Unified view of an agent's liquidity across all providers."""
    agent_id: str
    physical_cash: Money
    bkash_balance: Money
    nagad_balance: Money
    rocket_balance: Money
    overall_confidence: ConfidenceScore

    # Computed
    total_liquidity: Money
    utilization_pct: float          # how much of float is deployed
    lowest_provider: Provider       # provider with least liquidity
    is_low: bool                    # breaches low threshold
    is_critical: bool               # breaches critical threshold
    degraded_providers: list[str]   # stale feed providers


@dataclass
class ProviderLiquidityMetric:
    provider: Provider
    balance: Money
    share_pct: float            # % of total liquidity
    is_stale: bool
    confidence: ConfidenceScore


STALENESS_CONFIDENCE_PENALTY = 0.5  # multiply confidence by this when feed is stale


def compute_liquidity_matrix(
    snapshot: LiquiditySnapshot,
    feed_statuses: list[DataFeedStatus],
    low_threshold_pct: float = 20.0,
    critical_threshold_pct: float = 10.0,
) -> LiquidityMatrix:
    """
    Given a LiquiditySnapshot and current feed health,
    produce a unified LiquidityMatrix.
    """
    stale_providers = {
        fs.provider for fs in feed_statuses if fs.is_stale
    }

    balances: dict[Provider, Money] = {
        Provider.PHYSICAL: snapshot.physical_cash,
        Provider.BKASH: snapshot.bkash_balance,
        Provider.NAGAD: snapshot.nagad_balance,
        Provider.ROCKET: snapshot.rocket_balance,
    }

    total = Money(
        snapshot.physical_cash.amount
        + snapshot.bkash_balance.amount
        + snapshot.nagad_balance.amount
        + snapshot.rocket_balance.amount
    )

    # Degrade overall confidence for each stale provider
    base_confidence = snapshot.overall_confidence
    for _ in stale_providers:
        base_confidence = base_confidence.degrade(STALENESS_CONFIDENCE_PENALTY)

    # Thresholds (absolute BDT from % of total)
    if total.amount > 0:
        low_threshold = Money(total.amount * Decimal(str(low_threshold_pct / 100)))
        critical_threshold = Money(total.amount * Decimal(str(critical_threshold_pct / 100)))
    else:
        low_threshold = Money(Decimal("0"))
        critical_threshold = Money(Decimal("0"))

    # Find provider with lowest balance
    provider_balances = [
        (p, b) for p, b in balances.items() if p != Provider.PHYSICAL
    ]
    lowest_provider, _ = min(provider_balances, key=lambda x: x[1].amount)

    # Utilization = how much cash is out vs. total float
    # For hackathon: utilization is ratio of provider float deployed
    utilization_pct = 0.0
    if total.amount > 0:
        provider_total = (
            snapshot.bkash_balance.amount
            + snapshot.nagad_balance.amount
            + snapshot.rocket_balance.amount
        )
        utilization_pct = float(provider_total / total.amount * 100)

    # Threshold breach checks on lowest individual provider
    lowest_balance = balances[lowest_provider]
    is_low = lowest_balance <= low_threshold
    is_critical = lowest_balance <= critical_threshold

    degraded_providers = [p.value for p in stale_providers]

    return LiquidityMatrix(
        agent_id=snapshot.agent_id,
        physical_cash=snapshot.physical_cash,
        bkash_balance=snapshot.bkash_balance,
        nagad_balance=snapshot.nagad_balance,
        rocket_balance=snapshot.rocket_balance,
        overall_confidence=base_confidence,
        total_liquidity=total,
        utilization_pct=utilization_pct,
        lowest_provider=lowest_provider,
        is_low=is_low,
        is_critical=is_critical,
        degraded_providers=degraded_providers,
    )


def provider_metrics(matrix: LiquidityMatrix) -> list[ProviderLiquidityMetric]:
    """Break down per-provider metrics from a LiquidityMatrix."""
    providers = [
        (Provider.PHYSICAL, matrix.physical_cash),
        (Provider.BKASH, matrix.bkash_balance),
        (Provider.NAGAD, matrix.nagad_balance),
        (Provider.ROCKET, matrix.rocket_balance),
    ]
    total = matrix.total_liquidity.amount or Decimal("1")
    return [
        ProviderLiquidityMetric(
            provider=p,
            balance=b,
            share_pct=float(b.amount / total * 100),
            is_stale=(p.value in matrix.degraded_providers),
            confidence=(
                ConfidenceScore(matrix.overall_confidence.value)
                if p.value not in matrix.degraded_providers
                else ConfidenceScore(matrix.overall_confidence.value * STALENESS_CONFIDENCE_PENALTY)
            ),
        )
        for p, b in providers
    ]
