"""
OpenAI Agents SDK agent definitions.
Each agent is a pure reasoning engine — it calls tools, never computes directly.
"""
from __future__ import annotations

from agents import Agent

from .prompts import (
    COORDINATOR_SYSTEM_PROMPT,
    EXECUTIVE_ASSISTANT_SYSTEM_PROMPT,
    EXPLAINABILITY_SYSTEM_PROMPT,
    OPERATIONS_ANALYST_SYSTEM_PROMPT,
    RECOMMENDATION_SYSTEM_PROMPT,
)


def build_operations_analyst_agent(tools: list) -> Agent:
    return Agent(
        name="OperationsAnalystAgent",
        instructions=OPERATIONS_ANALYST_SYSTEM_PROMPT,
        tools=tools,
        model="gpt-4o-mini",
    )


def build_explainability_agent(tools: list) -> Agent:
    return Agent(
        name="ExplainabilityAgent",
        instructions=EXPLAINABILITY_SYSTEM_PROMPT,
        tools=tools,
        model="gpt-4o-mini",
    )


def build_recommendation_agent(tools: list) -> Agent:
    return Agent(
        name="RecommendationAgent",
        instructions=RECOMMENDATION_SYSTEM_PROMPT,
        tools=tools,
        model="gpt-4o-mini",
    )


def build_executive_assistant_agent(tools: list) -> Agent:
    return Agent(
        name="ExecutiveAssistantAgent",
        instructions=EXECUTIVE_ASSISTANT_SYSTEM_PROMPT,
        tools=tools,
        model="gpt-4o-mini",
    )


def build_coordinator_agent(
    analyst: Agent,
    explainability: Agent,
    recommendation: Agent,
    executive: Agent,
    tools: list,
) -> Agent:
    return Agent(
        name="CoordinatorAgent",
        instructions=COORDINATOR_SYSTEM_PROMPT,
        tools=tools,
        handoffs=[analyst, explainability, recommendation, executive],
        model="gpt-4o",
    )
