"""Shared state passed between grounded LangGraph nodes."""
from typing import TypedDict


class AgentState(TypedDict, total=False):
    user_query: str
    user_role: str
    route: str  # which specialist agent(s) the orchestrator selected
    retrieved_context: dict
    agent_trace: list[str]
    final_reply: str
    conversation_history: list[dict[str, str]]
    citations: list[dict[str, str]]
