"""Grounded LangGraph routing for CSOS specialist agents."""
from langgraph.graph import END, StateGraph

from app.agents.asset_agent import asset_agent_node
from app.agents.chat_assistant import chat_assistant_node
from app.agents.compliance_agent import compliance_agent_node
from app.agents.risk_agent import risk_agent_node
from app.agents.state import AgentState


def _classify_intent(state: AgentState) -> AgentState:
    query = state.get("user_query", "").lower()
    compliance_words = {"compliance", "control", "framework", "iso", "nist", "policy"}
    risk_words = {"risk", "vulnerability", "cve", "critical", "remediation", "finding"}
    asset_words = {"asset", "server", "device", "host", "owner", "endpoint", "topology"}
    matches = {
        "compliance": any(word in query for word in compliance_words),
        "risk": any(word in query for word in risk_words),
        "asset": any(word in query for word in asset_words),
    }
    selected = [name for name, matched in matches.items() if matched]
    state["route"] = selected[0] if len(selected) == 1 else "all"
    state.setdefault("agent_trace", []).append(f"orchestrator:{state['route']}")
    return state


def _all_agents(state: AgentState) -> AgentState:
    for node in (asset_agent_node, risk_agent_node, compliance_agent_node):
        state = node(state)
    return state


def build_orchestrator_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("asset_agent", asset_agent_node)
    graph.add_node("risk_agent", risk_agent_node)
    graph.add_node("compliance_agent", compliance_agent_node)
    graph.add_node("all_agents", _all_agents)
    graph.add_node("chat_assistant", chat_assistant_node)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        lambda state: state.get("route", "all"),
        {
            "asset": "asset_agent",
            "risk": "risk_agent",
            "compliance": "compliance_agent",
            "all": "all_agents",
        },
    )
    graph.add_edge("asset_agent", "chat_assistant")
    graph.add_edge("risk_agent", "chat_assistant")
    graph.add_edge("compliance_agent", "chat_assistant")
    graph.add_edge("all_agents", "chat_assistant")
    graph.add_edge("chat_assistant", END)

    return graph.compile()


_compiled_graph = None


def run_orchestrator(
    user_query: str,
    user_role: str = "Analyst",
    conversation_history: list[dict[str, str]] | None = None,
) -> AgentState:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_orchestrator_graph()

    initial_state: AgentState = {
        "user_query": user_query,
        "user_role": user_role,
        "conversation_history": conversation_history or [],
    }
    return _compiled_graph.invoke(initial_state)
