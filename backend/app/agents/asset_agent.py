"""Asset Intelligence Agent — retrieves graph facts for grounded generation."""
from app.agents.state import AgentState
from app.agents.tools import asset_tools


def asset_agent_node(state: AgentState) -> AgentState:
    query = state.get("user_query", "")
    generic = {"asset", "assets", "server", "device", "host", "topology"}
    search = "" if any(word in query.lower().split() for word in generic) else query
    results = asset_tools.search_assets(name_contains=search, limit=5)

    state.setdefault("retrieved_context", {})["assets"] = results
    state.setdefault("agent_trace", []).append("asset_intelligence_agent")
    return state
