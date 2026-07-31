"""
Orchestrator Agent — builds and compiles the LangGraph state graph
that routes a user query through the right specialist agent(s) and
produces a final chat reply.

TODO(P3):
  - Replace `_classify_intent` with an LLM call (Ollama) that returns
    one or more of {"asset", "risk", "compliance"} based on user_query.
  - Add conditional edges so only the relevant agent(s) run per query
    instead of always running all three (cheaper + more precise).
  - Add memory/conversation history to AgentState for multi-turn chat.
"""
from langgraph.graph import END, StateGraph

from app.agents.asset_agent import asset_agent_node
from app.agents.chat_assistant import chat_assistant_node
from app.agents.compliance_agent import compliance_agent_node
from app.agents.risk_agent import risk_agent_node
from app.agents.state import AgentState


def _classify_intent(state: AgentState) -> AgentState:
    # TODO(P3): model-based classification. The current scaffold runs all agents.
    state["route"] = "all"
    return state


def build_orchestrator_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("asset_agent", asset_agent_node)
    graph.add_node("risk_agent", risk_agent_node)
    graph.add_node("compliance_agent", compliance_agent_node)
    graph.add_node("chat_assistant", chat_assistant_node)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "asset_agent")
    graph.add_edge("asset_agent", "risk_agent")
    graph.add_edge("risk_agent", "compliance_agent")
    graph.add_edge("compliance_agent", "chat_assistant")
    graph.add_edge("chat_assistant", END)

    return graph.compile()


_compiled_graph = None


def run_orchestrator(user_query: str, user_role: str = "Analyst") -> AgentState:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_orchestrator_graph()

    initial_state: AgentState = {"user_query": user_query, "user_role": user_role}
    return _compiled_graph.invoke(initial_state)
