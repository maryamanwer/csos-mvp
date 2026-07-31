"""
Shared state passed between nodes in the LangGraph orchestrator graph.
TODO(P3): extend with retrieved_context typing per agent and message history.
"""
from typing import TypedDict


class AgentState(TypedDict, total=False):
    user_query: str
    user_role: str
    route: str  # which specialist agent(s) the orchestrator selected
    retrieved_context: dict
    agent_trace: list[str]
    final_reply: str
