"""
ContextEngine — cross-references event calendar with transaction volume.
Classifies spikes as demand-driven vs. potentially suspicious.
Loads context_calendar.csv from the data directory.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class CalendarEvent:
    event_date: date
    event_name: str
    expected_volume_multiplier: float  # e.g. 2.5x normal volume on Eid
    description: str


@dataclass
class ContextAssessment:
    is_known_event: bool
    event_name: Optional[str]
    expected_multiplier: float
    confidence_adjustment: float   # positive = boost, negative = downgrade anomaly confidence
    notes: str


_CALENDAR_CACHE: list[CalendarEvent] = []


def load_calendar(csv_path: str) -> None:
    """Load context_calendar.csv into memory. Call once at startup."""
    global _CALENDAR_CACHE
    if not os.path.exists(csv_path):
        return
    events = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                events.append(CalendarEvent(
                    event_date=date.fromisoformat(row["date"]),
                    event_name=row["event_name"],
                    expected_volume_multiplier=float(row.get("volume_multiplier", 1.0)),
                    description=row.get("description", ""),
                ))
            except (KeyError, ValueError):
                continue
    _CALENDAR_CACHE = events


def get_events_on(target_date: date) -> list[CalendarEvent]:
    return [e for e in _CALENDAR_CACHE if e.event_date == target_date]


def assess_context(spike_timestamp: datetime, observed_multiplier: float) -> ContextAssessment:
    """
    Given a spike timestamp and how much above normal it was,
    determine if a known calendar event explains it.

    observed_multiplier: e.g. 3.0 means 3x the normal volume.

    Returns a ContextAssessment with a confidence_adjustment:
    - If a known event explains the spike → downgrade anomaly confidence (negative adjustment)
    - If no event explains it → no adjustment (0.0) or slight upgrade
    """
    events = get_events_on(spike_timestamp.date())

    if not events:
        return ContextAssessment(
            is_known_event=False,
            event_name=None,
            expected_multiplier=1.0,
            confidence_adjustment=0.0,
            notes="No calendar event on this date.",
        )

    # Find the best-matching event
    best = max(events, key=lambda e: e.expected_volume_multiplier)

    # If the observed spike is within 20% of the expected multiplier → explained
    if observed_multiplier <= best.expected_volume_multiplier * 1.2:
        adjustment = -0.3  # downgrade anomaly confidence — likely legitimate demand
        notes = (
            f"Spike likely explained by '{best.event_name}' "
            f"(expected {best.expected_volume_multiplier}x, observed {observed_multiplier:.1f}x)."
        )
    elif observed_multiplier > best.expected_volume_multiplier * 1.5:
        adjustment = 0.1  # spike exceeds what the event explains — slightly more suspicious
        notes = (
            f"'{best.event_name}' event present but spike ({observed_multiplier:.1f}x) "
            f"significantly exceeds expected ({best.expected_volume_multiplier}x). Requires review."
        )
    else:
        adjustment = -0.1
        notes = (
            f"Partially explained by '{best.event_name}' event. "
            f"Observed {observed_multiplier:.1f}x, expected {best.expected_volume_multiplier}x."
        )

    return ContextAssessment(
        is_known_event=True,
        event_name=best.event_name,
        expected_multiplier=best.expected_volume_multiplier,
        confidence_adjustment=adjustment,
        notes=notes,
    )


def adjust_anomaly_confidence(raw_confidence: float, assessment: ContextAssessment) -> float:
    """
    Apply calendar context to raw anomaly confidence score.
    Result is clamped to [0.05, 1.0].
    """
    adjusted = raw_confidence + assessment.confidence_adjustment
    return round(max(0.05, min(1.0, adjusted)), 2)
