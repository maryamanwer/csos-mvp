"""
Risk Assessment Agent — LangGraph node.
TODO(M3): LLM-driven reasoning over retrieved risk/vulnerability data,
producing a ranked, explained remediation recommendation.
"""
from app.agents.state import AgentState
from app.agents.tools import risk_tools


def risk_agent_node(state: AgentState) -> AgentState:
    top_risks = risk_tools.list_top_risks(limit=5)

    state.setdefault("retrieved_context", {})["risks"] = top_risks
    state.setdefault("agent_trace", []).append("risk_assessment_agent")
    return state
