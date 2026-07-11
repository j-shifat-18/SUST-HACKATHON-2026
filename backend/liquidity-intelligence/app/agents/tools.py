"""
Agent tools — thin wrappers that bridge the OpenAI Agents SDK to domain engines.
Agents call these; tools call engines; engines return structured data.
Tools are the ONLY place agents touch deterministic business logic.
"""
from __future__ import annotations

import json
from typing import Any

from agents import function_tool

from app.engines.liquidity_engine import LiquidityMatrix
from app.engines.forecast_engine import ForecastResult
from app.engines.anomaly_engine import AnomalyResult
from app.engines.context_engine import ContextAssessment


# ---------------------------------------------------------------------------
# Serialisation helpers (engines return dataclasses, agents need dicts/strings)
# ---------------------------------------------------------------------------

def _matrix_to_dict(m: LiquidityMatrix) -> dict:
    return {
        "agent_id": m.agent_id,
        "physical_cash_bdt": float(m.physical_cash.amount),
        "bkash_balance_bdt": float(m.bkash_balance.amount),
        "nagad_balance_bdt": float(m.nagad_balance.amount),
        "rocket_balance_bdt": float(m.rocket_balance.amount),
        "total_liquidity_bdt": float(m.total_liquidity.amount),
        "utilization_pct": round(m.utilization_pct, 1),
        "lowest_provider": m.lowest_provider.value,
        "is_low": m.is_low,
        "is_critical": m.is_critical,
        "overall_confidence": m.overall_confidence.value,
        "degraded_providers": m.degraded_providers,
    }


def _forecast_to_dict(f: ForecastResult) -> dict:
    return {
        "provider": f.provider.value,
        "current_balance_bdt": float(f.current_balance.amount),
        "predicted_balance_bdt": float(f.predicted_balance_at_horizon.amount),
        "depletion_time_hours": f.depletion_time_hours,
        "hourly_net_flow_bdt": round(f.hourly_net_flow, 2),
        "confidence": f.confidence.value,
    }


def _anomaly_to_dict(a: AnomalyResult) -> dict:
    return {
        "flag_type": a.flag_type.value,
        "severity_score": a.severity_score,
        "confidence": a.confidence,
        "explanation_en": a.explanation_en,
        "explanation_bn": a.explanation_bn,
        "explanation_banglish": a.explanation_banglish,
        "evidence": a.evidence,
        "transaction_count": len(a.transaction_group_ids),
    }


# ---------------------------------------------------------------------------
# Tool: get_liquidity_matrix
# ---------------------------------------------------------------------------

# These tools receive pre-computed results injected by the use case orchestrator.
# The orchestrator runs the engines, serialises the results, and passes them
# as context strings into the agent run. The tools below are registered so
# the agent CAN call them — but in practice the orchestrator pre-populates
# the context to avoid redundant computation.

def make_liquidity_tool(matrix: LiquidityMatrix):
    """Factory: returns a tool bound to a specific pre-computed matrix."""

    @function_tool
    def get_liquidity_matrix() -> str:
        """
        Returns the current unified liquidity matrix for this agent,
        including all provider balances, total liquidity, utilisation,
        and any data-feed degradation indicators.
        """
        return json.dumps(_matrix_to_dict(matrix), ensure_ascii=False, indent=2)

    return get_liquidity_matrix


def make_forecast_tool(forecasts: list[ForecastResult]):
    """Factory: returns a tool bound to a list of pre-computed forecasts."""

    @function_tool
    def get_forecasts() -> str:
        """
        Returns balance forecasts for all providers over the next N hours,
        including predicted depletion times and confidence scores.
        """
        return json.dumps(
            [_forecast_to_dict(f) for f in forecasts],
            ensure_ascii=False,
            indent=2,
        )

    return get_forecasts


def make_anomaly_tool(anomalies: list[AnomalyResult]):
    """Factory: returns a tool bound to a list of pre-computed anomaly results."""

    @function_tool
    def get_anomaly_flags() -> str:
        """
        Returns all anomaly flags detected for this agent's recent transactions,
        with severity scores, confidence, and evidence.
        Language is advisory — never accusatory.
        """
        if not anomalies:
            return json.dumps({"anomalies": [], "count": 0})
        return json.dumps(
            {"anomalies": [_anomaly_to_dict(a) for a in anomalies], "count": len(anomalies)},
            ensure_ascii=False,
            indent=2,
        )

    return get_anomaly_flags


def make_context_tool(assessments: dict[str, ContextAssessment]):
    """Factory: returns a tool that looks up calendar context for a given date."""

    @function_tool
    def get_calendar_context(date_str: str) -> str:
        """
        Given a date string (YYYY-MM-DD), returns whether a known calendar event
        (Eid, salary day, payday) explains elevated transaction volume on that date.
        """
        assessment = assessments.get(date_str)
        if not assessment:
            return json.dumps({
                "is_known_event": False,
                "notes": "No calendar event data for this date.",
            })
        return json.dumps({
            "is_known_event": assessment.is_known_event,
            "event_name": assessment.event_name,
            "expected_multiplier": assessment.expected_multiplier,
            "confidence_adjustment": assessment.confidence_adjustment,
            "notes": assessment.notes,
        }, ensure_ascii=False)

    return get_calendar_context
