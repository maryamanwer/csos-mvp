"""
Asset Intelligence Agent — LangGraph node.
TODO(P3): replace the naive keyword lookup with a ModelProvider call
that decides which asset_tools function(s) to invoke, then summarizes
the retrieved facts in natural language.
"""
from app.agents.state import AgentState
from app.agents.tools import asset_tools


def asset_agent_node(state: AgentState) -> AgentState:
    query = state.get("user_query", "")
    results = asset_tools.search_assets(name_contains=query, limit=5)

    state.setdefault("retrieved_context", {})["assets"] = results
    state.setdefault("agent_trace", []).append("asset_intelligence_agent")
    return state
