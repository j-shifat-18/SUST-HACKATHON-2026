"""
AnomalyEngine — detects suspicious transaction patterns.
Deterministic, pure logic — no AI, no I/O.

Patterns detected:
1. Velocity Spike — Z-score on hourly tx count/volume
2. Transaction Splitting — near-identical amounts from same account in short window
3. Circular Flow — cash-out followed by cash-in from same account ref
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class AnomalyResult:
    flag_type: str  # velocity_spike | transaction_splitting | circular_flow
    severity_score: int  # 0-100
    confidence: float  # 0.0 - 1.0
    evidence: dict
    transaction_ids: list[str] = field(default_factory=list)


@dataclass
class TransactionRecord:
    id: str
    agent_id: str
    provider: str
    transaction_type: str
    amount: float
    timestamp: datetime
    account_ref: str


def detect_velocity_spike(
    transactions: list[TransactionRecord],
    window_hours: int = 1,
    rolling_hours: int = 24,
    zscore_threshold: float = 2.5,
) -> Optional[AnomalyResult]:
    """
    Detect if the most recent hour has an unusual spike in transaction
    count or volume relative to the rolling window.
    """
    if len(transactions) < 6:
        return None

    now = max(t.timestamp for t in transactions)
    window_start = now - timedelta(hours=window_hours)
    rolling_start = now - timedelta(hours=rolling_hours)

    # Current window transactions
    current_txs = [t for t in transactions if t.timestamp >= window_start]
    # Rolling historical (excluding current window)
    historical_txs = [t for t in transactions if rolling_start <= t.timestamp < window_start]

    if not historical_txs:
        return None

    current_count = len(current_txs)
    current_volume = sum(t.amount for t in current_txs)

    # Compute hourly buckets for historical
    hours_in_history = max(1, (window_start - rolling_start).total_seconds() / 3600)
    hourly_counts = []
    hourly_volumes = []

    for h in range(int(hours_in_history)):
        h_start = rolling_start + timedelta(hours=h)
        h_end = h_start + timedelta(hours=1)
        h_txs = [t for t in historical_txs if h_start <= t.timestamp < h_end]
        hourly_counts.append(len(h_txs))
        hourly_volumes.append(sum(t.amount for t in h_txs))

    if not hourly_counts or len(hourly_counts) < 3:
        return None

    # Z-score for count
    mean_count = sum(hourly_counts) / len(hourly_counts)
    std_count = math.sqrt(sum((x - mean_count) ** 2 for x in hourly_counts) / len(hourly_counts))

    if std_count == 0:
        z_count = 0
    else:
        z_count = (current_count - mean_count) / std_count

    # Z-score for volume
    mean_volume = sum(hourly_volumes) / len(hourly_volumes)
    std_volume = math.sqrt(sum((x - mean_volume) ** 2 for x in hourly_volumes) / len(hourly_volumes))

    if std_volume == 0:
        z_volume = 0
    else:
        z_volume = (current_volume - mean_volume) / std_volume

    max_z = max(z_count, z_volume)

    if max_z >= zscore_threshold:
        severity = min(100, int(30 + max_z * 15))
        confidence = min(0.95, 0.5 + (max_z - zscore_threshold) * 0.15)

        return AnomalyResult(
            flag_type="velocity_spike",
            severity_score=severity,
            confidence=round(confidence, 2),
            evidence={
                "hourly_count": current_count,
                "normal_hourly_count": round(mean_count, 1),
                "z_score_count": round(z_count, 2),
                "z_score_volume": round(z_volume, 2),
                "current_volume_bdt": round(current_volume, 0),
                "normal_hourly_volume_bdt": round(mean_volume, 0),
            },
            transaction_ids=[t.id for t in current_txs[:10]],
        )

    return None


def detect_transaction_splitting(
    transactions: list[TransactionRecord],
    time_window_minutes: int = 60,
    amount_tolerance_pct: float = 5.0,
    min_count: int = 3,
) -> Optional[AnomalyResult]:
    """
    Detect near-identical amounts from the same account_ref in a short window.
    """
    if len(transactions) < min_count:
        return None

    now = max(t.timestamp for t in transactions)
    window_start = now - timedelta(minutes=time_window_minutes)
    recent = [t for t in transactions if t.timestamp >= window_start and t.transaction_type == "cash_out"]

    # Group by account_ref
    by_account: dict[str, list[TransactionRecord]] = defaultdict(list)
    for t in recent:
        by_account[t.account_ref].append(t)

    for account_ref, txs in by_account.items():
        if len(txs) < min_count:
            continue

        # Check if amounts are near-identical
        amounts = [t.amount for t in txs]
        mean_amount = sum(amounts) / len(amounts)
        if mean_amount == 0:
            continue

        within_tolerance = all(
            abs(a - mean_amount) / mean_amount * 100 <= amount_tolerance_pct
            for a in amounts
        )

        if within_tolerance:
            severity = min(100, 30 + len(txs) * 10)
            confidence = min(0.9, 0.5 + len(txs) * 0.1)

            return AnomalyResult(
                flag_type="transaction_splitting",
                severity_score=severity,
                confidence=round(confidence, 2),
                evidence={
                    "account_ref": account_ref,
                    "transaction_count": len(txs),
                    "mean_amount_bdt": round(mean_amount, 0),
                    "total_amount_bdt": round(sum(amounts), 0),
                    "time_window_minutes": time_window_minutes,
                },
                transaction_ids=[t.id for t in txs],
            )

    return None


def detect_circular_flow(
    transactions: list[TransactionRecord],
    time_window_hours: int = 6,
    amount_tolerance_pct: float = 10.0,
) -> Optional[AnomalyResult]:
    """
    Detect cash-out followed by cash-in from the same account_ref
    with similar amounts (within tolerance).
    """
    if len(transactions) < 2:
        return None

    now = max(t.timestamp for t in transactions)
    window_start = now - timedelta(hours=time_window_hours)
    recent = [t for t in transactions if t.timestamp >= window_start]

    cash_outs = [t for t in recent if t.transaction_type == "cash_out"]
    cash_ins = [t for t in recent if t.transaction_type == "cash_in"]

    for co in cash_outs:
        for ci in cash_ins:
            if ci.account_ref != co.account_ref:
                continue
            if ci.timestamp <= co.timestamp:
                continue

            # Check amount similarity
            if co.amount == 0:
                continue
            diff_pct = abs(ci.amount - co.amount) / co.amount * 100
            if diff_pct <= amount_tolerance_pct:
                severity = min(100, 50 + int(diff_pct))
                confidence = max(0.5, 0.85 - diff_pct * 0.03)

                return AnomalyResult(
                    flag_type="circular_flow",
                    severity_score=severity,
                    confidence=round(confidence, 2),
                    evidence={
                        "account_ref": co.account_ref,
                        "cash_out_amount_bdt": round(co.amount, 0),
                        "cash_in_amount_bdt": round(ci.amount, 0),
                        "amount_difference_pct": round(diff_pct, 1),
                        "time_gap_minutes": round((ci.timestamp - co.timestamp).total_seconds() / 60, 0),
                    },
                    transaction_ids=[co.id, ci.id],
                )

    return None


def run_all_detections(transactions: list[TransactionRecord]) -> list[AnomalyResult]:
    """Run all anomaly detection algorithms and return all findings."""
    results = []

    spike = detect_velocity_spike(transactions)
    if spike:
        results.append(spike)

    splitting = detect_transaction_splitting(transactions)
    if splitting:
        results.append(splitting)

    circular = detect_circular_flow(transactions)
    if circular:
        results.append(circular)

    return results
