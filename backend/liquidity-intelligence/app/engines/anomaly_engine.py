"""
AnomalyEngine — deterministic rule-based + statistical detection.
Detects: velocity spikes, transaction splitting, circular flows.
Output always includes: type, severity (0-100), confidence, evidence, explanation.
Language is always careful — "unusual pattern", "requires review", never "fraud".
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import numpy as np

from app.domain.entities import AnomalyFlag, Transaction
from app.domain.value_objects import AnomalyType, ConfidenceScore, ReviewLanguage


# Tuning constants
VELOCITY_ZSCORE_THRESHOLD = 2.5
SPLITTING_MIN_TRANSACTIONS = 3
SPLITTING_AMOUNT_TOLERANCE_PCT = 0.05   # within 5% of each other
SPLITTING_WINDOW_MINUTES = 60
CIRCULAR_WINDOW_HOURS = 6
CIRCULAR_MIN_AMOUNT = Decimal("500")    # BDT minimum to flag


@dataclass
class AnomalyResult:
    flag_type: AnomalyType
    severity_score: int           # 0-100
    confidence: float             # 0-1
    evidence: dict
    transaction_id: Optional[str] = None
    transaction_group_ids: list[str] = field(default_factory=list)

    # Language-safe explanations
    explanation_en: str = ""
    explanation_bn: str = ""
    explanation_banglish: str = ""


def detect_anomalies(
    transactions: list[Transaction],
    zscore_threshold: float = VELOCITY_ZSCORE_THRESHOLD,
    rolling_window_hours: int = 24,
) -> list[AnomalyResult]:
    """
    Run all three detection algorithms on a list of transactions.
    Returns a combined list of AnomalyResults.
    """
    results: list[AnomalyResult] = []
    results.extend(_detect_velocity_spikes(transactions, zscore_threshold, rolling_window_hours))
    results.extend(_detect_splitting(transactions))
    results.extend(_detect_circular_flows(transactions))
    return results


def anomaly_result_to_entity(result: AnomalyResult) -> AnomalyFlag:
    return AnomalyFlag(
        id=str(uuid.uuid4()),
        transaction_id=result.transaction_id,
        transaction_group_ids=result.transaction_group_ids,
        flag_type=result.flag_type,
        severity_score=result.severity_score,
        confidence=ConfidenceScore(round(result.confidence, 2)),
        evidence=result.evidence,
        explanation_en=result.explanation_en,
        explanation_bn=result.explanation_bn,
        explanation_banglish=result.explanation_banglish,
        review_language=ReviewLanguage.EN,
        is_reviewed=False,
        created_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# 1. Velocity Spike Detection
# ---------------------------------------------------------------------------

def _detect_velocity_spikes(
    transactions: list[Transaction],
    zscore_threshold: float,
    rolling_window_hours: int,
) -> list[AnomalyResult]:
    """
    Detect hours where transaction volume deviates more than z-score threshold
    from the rolling mean.
    """
    if len(transactions) < 10:
        return []

    # Bin by hour
    hourly_counts: dict[datetime, int] = defaultdict(int)
    hourly_amounts: dict[datetime, float] = defaultdict(float)

    for tx in transactions:
        bucket = tx.timestamp.replace(minute=0, second=0, microsecond=0)
        hourly_counts[bucket] += 1
        hourly_amounts[bucket] += float(tx.amount.amount)

    hours = sorted(hourly_counts.keys())
    counts = [hourly_counts[h] for h in hours]
    amounts = [hourly_amounts[h] for h in hours]

    if len(counts) < 3:
        return []

    mean_count = np.mean(counts)
    std_count = np.std(counts) + 1e-6
    mean_amount = np.mean(amounts)
    std_amount = np.std(amounts) + 1e-6

    results = []
    for i, hour in enumerate(hours):
        z_count = (counts[i] - mean_count) / std_count
        z_amount = (amounts[i] - mean_amount) / std_amount
        z_max = max(z_count, z_amount)

        if z_max >= zscore_threshold:
            severity = min(100, int(z_max / zscore_threshold * 50))
            confidence = min(0.95, (z_max - zscore_threshold) / 5 + 0.5)

            txs_in_hour = [
                t.id for t in transactions
                if t.timestamp.replace(minute=0, second=0, microsecond=0) == hour
            ]

            results.append(AnomalyResult(
                flag_type=AnomalyType.VELOCITY_SPIKE,
                severity_score=severity,
                confidence=round(confidence, 2),
                evidence={
                    "hour": hour.isoformat(),
                    "transaction_count": counts[i],
                    "total_amount_bdt": round(amounts[i], 2),
                    "z_score_count": round(float(z_count), 2),
                    "z_score_amount": round(float(z_amount), 2),
                    "mean_hourly_count": round(float(mean_count), 2),
                    "transaction_ids": txs_in_hour[:10],  # cap for storage
                },
                transaction_group_ids=txs_in_hour,
                explanation_en=(
                    f"Unusual transaction volume detected at {hour.strftime('%Y-%m-%d %H:00')}. "
                    f"{counts[i]} transactions totalling ৳{amounts[i]:,.0f} — "
                    f"approximately {z_max:.1f} standard deviations above the hourly average. "
                    "This requires manual review."
                ),
                explanation_bn=(
                    f"{hour.strftime('%Y-%m-%d %H:00')} সময়ে অস্বাভাবিক লেনদেনের পরিমাণ লক্ষ্য করা গেছে। "
                    f"মোট {counts[i]}টি লেনদেনে ৳{amounts[i]:,.0f} — গড়ের চেয়ে {z_max:.1f} স্ট্যান্ডার্ড ডেভিয়েশন বেশি। "
                    "ম্যানুয়াল পর্যালোচনা প্রয়োজন।"
                ),
                explanation_banglish=(
                    f"{hour.strftime('%H:00')} te unusual transaction volume. "
                    f"{counts[i]}ta transaction, total ৳{amounts[i]:,.0f}. "
                    "Review korte hobe."
                ),
            ))

    return results


# ---------------------------------------------------------------------------
# 2. Transaction Splitting Detection
# ---------------------------------------------------------------------------

def _detect_splitting(transactions: list[Transaction]) -> list[AnomalyResult]:
    """
    Detect near-identical repeated amounts within a short time window from
    the same account_ref — a pattern associated with structured transactions.
    """
    results = []
    # Group by account_ref
    by_ref: dict[str, list[Transaction]] = defaultdict(list)
    for tx in transactions:
        by_ref[tx.account_ref].append(tx)

    for ref, txs in by_ref.items():
        if len(txs) < SPLITTING_MIN_TRANSACTIONS:
            continue

        # Sort by time
        txs_sorted = sorted(txs, key=lambda t: t.timestamp)

        # Sliding window
        for i in range(len(txs_sorted) - SPLITTING_MIN_TRANSACTIONS + 1):
            window = txs_sorted[i : i + SPLITTING_MIN_TRANSACTIONS]
            window_start = window[0].timestamp
            window_end = window[-1].timestamp

            if (window_end - window_start) > timedelta(minutes=SPLITTING_WINDOW_MINUTES):
                continue

            amounts = [float(t.amount.amount) for t in window]
            mean_amount = np.mean(amounts)
            if mean_amount == 0:
                continue

            # Check if all amounts are within tolerance of the mean
            deviations = [abs(a - mean_amount) / mean_amount for a in amounts]
            if max(deviations) <= SPLITTING_AMOUNT_TOLERANCE_PCT:
                total = sum(amounts)
                severity = min(100, int(len(window) * 15))
                confidence = 1.0 - max(deviations)

                results.append(AnomalyResult(
                    flag_type=AnomalyType.TRANSACTION_SPLITTING,
                    severity_score=severity,
                    confidence=round(confidence, 2),
                    evidence={
                        "account_ref": ref,
                        "window_start": window_start.isoformat(),
                        "window_end": window_end.isoformat(),
                        "transaction_count": len(window),
                        "amounts_bdt": [round(a, 2) for a in amounts],
                        "total_bdt": round(total, 2),
                        "mean_amount_bdt": round(mean_amount, 2),
                    },
                    transaction_group_ids=[t.id for t in window],
                    explanation_en=(
                        f"{len(window)} transactions of near-identical amounts "
                        f"(mean ৳{mean_amount:,.0f}) detected within "
                        f"{int((window_end - window_start).total_seconds() // 60)} minutes. "
                        "This pattern requires review."
                    ),
                    explanation_bn=(
                        f"অনুরূপ পরিমাণের {len(window)}টি লেনদেন "
                        f"(গড় ৳{mean_amount:,.0f}) মাত্র "
                        f"{int((window_end - window_start).total_seconds() // 60)} মিনিটের মধ্যে। "
                        "এই প্যাটার্নটি পর্যালোচনা প্রয়োজন।"
                    ),
                    explanation_banglish=(
                        f"{len(window)}ta similar amount er transaction "
                        f"{int((window_end - window_start).total_seconds() // 60)} minute e. "
                        "Review dorkar."
                    ),
                ))

    return results


# ---------------------------------------------------------------------------
# 3. Circular Flow Detection
# ---------------------------------------------------------------------------

def _detect_circular_flows(transactions: list[Transaction]) -> list[AnomalyResult]:
    """
    Detect transactions where cash-out to a ref is followed closely by
    cash-in from the same ref — a potential circular movement pattern.
    """
    results = []
    window = timedelta(hours=CIRCULAR_WINDOW_HOURS)

    # Build index: ref → list of (timestamp, type, amount, id)
    ref_index: dict[str, list[tuple]] = defaultdict(list)
    for tx in transactions:
        if tx.amount.amount >= CIRCULAR_MIN_AMOUNT:
            ref_index[tx.account_ref].append(
                (tx.timestamp, tx.transaction_type.value, float(tx.amount.amount), tx.id)
            )

    for ref, events in ref_index.items():
        events_sorted = sorted(events, key=lambda e: e[0])
        out_events = [(ts, amt, tid) for ts, ttype, amt, tid in events_sorted if ttype == "cash_out"]
        in_events = [(ts, amt, tid) for ts, ttype, amt, tid in events_sorted if ttype == "cash_in"]

        for out_ts, out_amt, out_id in out_events:
            for in_ts, in_amt, in_id in in_events:
                if out_ts < in_ts <= out_ts + window:
                    amount_match = abs(in_amt - out_amt) / max(out_amt, 1e-6) <= 0.1
                    if amount_match:
                        severity = min(100, int(out_amt / 1000))
                        results.append(AnomalyResult(
                            flag_type=AnomalyType.CIRCULAR_FLOW,
                            severity_score=max(40, severity),
                            confidence=0.65,
                            evidence={
                                "account_ref": ref,
                                "cash_out_id": out_id,
                                "cash_out_amount_bdt": round(out_amt, 2),
                                "cash_out_time": out_ts.isoformat(),
                                "cash_in_id": in_id,
                                "cash_in_amount_bdt": round(in_amt, 2),
                                "cash_in_time": in_ts.isoformat(),
                                "turnaround_minutes": round(
                                    (in_ts - out_ts).total_seconds() / 60, 1
                                ),
                            },
                            transaction_group_ids=[out_id, in_id],
                            explanation_en=(
                                f"A cash-out of ৳{out_amt:,.0f} followed by a cash-in of "
                                f"৳{in_amt:,.0f} from the same account within "
                                f"{round((in_ts - out_ts).total_seconds() / 60)} minutes. "
                                "This unusual round-trip pattern requires review."
                            ),
                            explanation_bn=(
                                f"একই অ্যাকাউন্ট থেকে ৳{out_amt:,.0f} ক্যাশ-আউটের পর "
                                f"{round((in_ts - out_ts).total_seconds() / 60)} মিনিটের মধ্যে "
                                f"৳{in_amt:,.0f} ক্যাশ-ইন। এই অস্বাভাবিক প্যাটার্নটি পর্যালোচনা প্রয়োজন।"
                            ),
                            explanation_banglish=(
                                f"Same account theke ৳{out_amt:,.0f} cash-out er por "
                                f"{round((in_ts - out_ts).total_seconds() / 60)} minute e "
                                f"৳{in_amt:,.0f} cash-in. Unusual pattern — review dorkar."
                            ),
                        ))

    return results
