"""
ContextEngine — cross-references anomaly timestamps against a known
event calendar (Eid, salary days, etc.) to adjust anomaly confidence.

If a spike coincides with a known event and stays within the expected
multiplier range, the anomaly confidence is degraded (it's probably
legitimate demand). If the spike far exceeds the event expectation,
confidence is boosted.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Module-level calendar store
_calendar: list["CalendarEvent"] = []


@dataclass
class CalendarEvent:
    event_date: date
    event_name: str
    expected_multiplier: float
    region: Optional[str] = None  # None = nationwide


@dataclass
class ContextAssessment:
    event_name: str
    event_date: date
    expected_multiplier: float
    confidence_adjustment: float  # negative = degrade, positive = boost
    explanation: str


def load_calendar(path: str) -> None:
    """Load context calendar from CSV. Called once at startup."""
    global _calendar
    _calendar = []

    if not os.path.exists(path):
        logger.warning("context_calendar_not_found", path=path)
        return

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Support both column naming conventions
                multiplier_key = (
                    "expected_multiplier"
                    if "expected_multiplier" in row
                    else "volume_multiplier"
                )
                evt = CalendarEvent(
                    event_date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
                    event_name=row["event_name"],
                    expected_multiplier=float(row[multiplier_key]),
                    region=row.get("region") or None,
                )
                _calendar.append(evt)
            except (KeyError, ValueError) as e:
                logger.warning("calendar_parse_error", row=row, error=str(e))

    logger.info("context_calendar_loaded", event_count=len(_calendar))


def get_context_for_date(
    target_date: date,
    region: Optional[str] = None,
) -> list[ContextAssessment]:
    """
    Check if the target_date falls on a known event.
    Returns assessments for matching events.
    """
    assessments = []
    for evt in _calendar:
        if evt.event_date != target_date:
            continue
        if evt.region and evt.region != region:
            continue
        # Event matches — produce a default assessment
        assessments.append(
            ContextAssessment(
                event_name=evt.event_name,
                event_date=evt.event_date,
                expected_multiplier=evt.expected_multiplier,
                confidence_adjustment=-0.3,  # default degrade
                explanation=(
                    f"Spike coincides with {evt.event_name} "
                    f"(expected {evt.expected_multiplier}x volume). "
                    f"Likely legitimate demand."
                ),
            )
        )
    return assessments


def adjust_anomaly_confidence(
    base_confidence: float,
    actual_multiplier: float,
    target_date: date,
    region: Optional[str] = None,
) -> tuple[float, list[ContextAssessment]]:
    """
    Adjust anomaly confidence based on calendar context.

    Returns:
        (adjusted_confidence, list of context assessments applied)
    """
    assessments = get_context_for_date(target_date, region)
    if not assessments:
        return base_confidence, []

    adjusted = base_confidence
    for assessment in assessments:
        if actual_multiplier <= assessment.expected_multiplier * 1.2:
            # Within expected range — degrade confidence (legitimate)
            assessment.confidence_adjustment = -0.3
            assessment.explanation = (
                f"Spike coincides with {assessment.event_name} "
                f"(expected {assessment.expected_multiplier}x, actual {actual_multiplier:.1f}x). "
                f"Likely legitimate demand."
            )
        elif actual_multiplier > assessment.expected_multiplier * 1.5:
            # Far exceeds expectation — boost confidence (still suspicious)
            assessment.confidence_adjustment = 0.1
            assessment.explanation = (
                f"Spike on {assessment.event_name} exceeds expected "
                f"{assessment.expected_multiplier}x by significant margin "
                f"(actual {actual_multiplier:.1f}x). Remains suspicious."
            )
        else:
            # Moderately above expected — small degrade
            assessment.confidence_adjustment = -0.15
            assessment.explanation = (
                f"Spike on {assessment.event_name} is slightly above expected "
                f"{assessment.expected_multiplier}x (actual {actual_multiplier:.1f}x)."
            )
        adjusted += assessment.confidence_adjustment

    # Clamp to [0, 1]
    adjusted = max(0.0, min(1.0, adjusted))
    return adjusted, assessments
