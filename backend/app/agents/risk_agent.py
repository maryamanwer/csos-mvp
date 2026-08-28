"""Risk Assessment Agent — retrieves ranked risks and attack paths."""
from app.agents.state import AgentState
from app.agents.tools import risk_tools


def risk_agent_node(state: AgentState) -> AgentState:
    top_risks = risk_tools.list_top_risks(limit=5)
    attack_paths = risk_tools.list_attack_paths(limit=5)

    state.setdefault("retrieved_context", {})["risks"] = top_risks
    state.setdefault("retrieved_context", {})["attack_paths"] = attack_paths
    state.setdefault("agent_trace", []).append("risk_assessment_agent")
    return state
