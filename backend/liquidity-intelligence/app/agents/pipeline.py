"""
Agent pipeline orchestrator.
Runs engines deterministically, then feeds results into the agent layer.
This is the integration point between Application Layer and AI Layer.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from agents import Runner

from app.core.config import get_settings
from app.domain.entities import AgentTraceLog, DataFeedStatus, LiquiditySnapshot, Transaction
from app.engines.anomaly_engine import AnomalyResult, detect_anomalies
from app.engines.context_engine import ContextAssessment, assess_context
from app.engines.forecast_engine import ForecastResult, forecast_provider
from app.engines.liquidity_engine import LiquidityMatrix, compute_liquidity_matrix

from .agent_definitions import (
    build_coordinator_agent,
    build_executive_assistant_agent,
    build_explainability_agent,
    build_operations_analyst_agent,
    build_recommendation_agent,
)
from .tools import (
    make_anomaly_tool,
    make_context_tool,
    make_forecast_tool,
    make_liquidity_tool,
)

_settings = get_settings()


@dataclass
class PipelineResult:
    agent_id: str
    request_id: str
    liquidity_matrix: LiquidityMatrix
    forecasts: list[ForecastResult]
    anomalies: list[AnomalyResult]
    agent_response: dict          # structured JSON from CoordinatorAgent
    trace_log: AgentTraceLog
    generated_at: datetime


async def run_full_pipeline(
    agent_id: str,
    snapshot: LiquiditySnapshot,
    transactions: list[Transaction],
    feed_statuses: list[DataFeedStatus],
    request_id: Optional[str] = None,
    horizon_hours: int = 12,
) -> PipelineResult:
    """
    1. Run all deterministic engines.
    2. Build agent tools from engine outputs.
    3. Run CoordinatorAgent.
    4. Return structured result + trace log.
    """
    request_id = request_id or str(uuid.uuid4())
    start_ms = int(time.time() * 1000)

    # --- Step 1: Deterministic engines ---
    matrix = compute_liquidity_matrix(
        snapshot,
        feed_statuses,
        low_threshold_pct=_settings.low_liquidity_threshold_pct,
        critical_threshold_pct=_settings.critical_liquidity_threshold_pct,
    )

    from app.domain.value_objects import Provider
    forecasts = [
        forecast_provider(agent_id, p, snapshot.balance_for(p), transactions, horizon_hours)
        for p in [Provider.BKASH, Provider.NAGAD, Provider.ROCKET, Provider.PHYSICAL]
    ]

    anomalies = detect_anomalies(
        transactions,
        zscore_threshold=_settings.anomaly_zscore_threshold,
        rolling_window_hours=_settings.anomaly_rolling_window_hours,
    )

    # Context assessments keyed by date string
    context_assessments: dict[str, ContextAssessment] = {}
    for anomaly in anomalies:
        if "hour" in anomaly.evidence:
            date_str = anomaly.evidence["hour"][:10]
            if date_str not in context_assessments:
                mean_count = anomaly.evidence.get("mean_hourly_count", 1.0)
                observed = anomaly.evidence.get("transaction_count", 1.0)
                multiplier = observed / max(mean_count, 1e-6)
                context_assessments[date_str] = assess_context(
                    datetime.fromisoformat(anomaly.evidence["hour"]),
                    multiplier,
                )

    # --- Step 2: Build agent tools ---
    shared_tools = [
        make_liquidity_tool(matrix),
        make_forecast_tool(forecasts),
        make_anomaly_tool(anomalies),
        make_context_tool(context_assessments),
    ]

    # --- Step 3: Build agents ---
    analyst = build_operations_analyst_agent(shared_tools)
    explainability = build_explainability_agent(shared_tools)
    recommendation = build_recommendation_agent(shared_tools)
    executive = build_executive_assistant_agent(shared_tools)
    coordinator = build_coordinator_agent(analyst, explainability, recommendation, executive, shared_tools)

    # --- Step 4: Run coordinator ---
    query = (
        f"Provide a full liquidity intelligence report for agent {agent_id}. "
        f"Include operational status, any anomaly explanations, and recommendations."
    )

    result = await Runner.run(coordinator, query)
    raw_output = result.final_output or ""

    # Parse JSON from agent output (agents are instructed to return JSON)
    try:
        agent_response = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError):
        agent_response = {"raw": raw_output, "parse_error": True}

    # --- Step 5: Build trace log ---
    duration_ms = int(time.time() * 1000) - start_ms
    tool_calls = [
        {"agent": item.agent.name, "tool": getattr(item, "tool_name", "unknown")}
        for item in (result.raw_responses or [])
        if hasattr(item, "agent")
    ]

    trace = AgentTraceLog(
        id=str(uuid.uuid4()),
        request_id=request_id,
        agent_name="CoordinatorAgent",
        input_summary=query[:500],
        output_summary=raw_output[:500],
        tool_calls=tool_calls,
        duration_ms=duration_ms,
        created_at=datetime.utcnow(),
    )

    return PipelineResult(
        agent_id=agent_id,
        request_id=request_id,
        liquidity_matrix=matrix,
        forecasts=forecasts,
        anomalies=anomalies,
        agent_response=agent_response,
        trace_log=trace,
        generated_at=datetime.utcnow(),
    )
