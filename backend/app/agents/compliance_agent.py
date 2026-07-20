"""
Compliance Agent — LangGraph node.
TODO(M3): LLM-driven reasoning to explain gaps and suggest remediation
priority based on framework coverage.
"""
from app.agents.state import AgentState
from app.agents.tools import compliance_tools


def compliance_agent_node(state: AgentState) -> AgentState:
    # TODO(M3): infer framework name from user_query via LLM classification;
    # defaulting to ISO 27001 for the MVP stub.
    gaps = compliance_tools.list_control_gaps(framework_name="ISO 27001")

    state.setdefault("retrieved_context", {})["compliance_gaps"] = gaps
    state.setdefault("agent_trace", []).append("compliance_agent")
    return state
