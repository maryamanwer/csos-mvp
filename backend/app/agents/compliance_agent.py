"""Compliance Agent — retrieves framework-specific control gaps."""
from app.agents.state import AgentState
from app.agents.tools import compliance_tools


def compliance_agent_node(state: AgentState) -> AgentState:
    query = state.get("user_query", "").lower()
    framework = "NIST CSF" if "nist" in query else "ISO 27001"
    gaps = compliance_tools.list_control_gaps(framework_name=framework)

    state.setdefault("retrieved_context", {})["compliance_gaps"] = gaps
    state.setdefault("retrieved_context", {})["compliance_framework"] = framework
    state.setdefault("agent_trace", []).append("compliance_agent")
    return state
