"""
AI Chat Assistant — final LangGraph node.
Formats the natural-language reply from whatever context the
specialist agents retrieved.

TODO(P3): replace the string-templating below with a ModelProvider call:

    from app.ai import get_model_provider
    provider = get_model_provider()
    reply = provider.generate(build_prompt(state))

The prompt should instruct the model to: only use retrieved_context
facts (no hallucination), cite asset/control IDs, and phrase the
answer appropriately for state["user_role"].
"""
from app.agents.state import AgentState


def chat_assistant_node(state: AgentState) -> AgentState:
    context = state.get("retrieved_context", {})
    parts = []

    if "assets" in context:
        parts.append(f"Found {len(context['assets'])} matching asset(s).")
    if "risks" in context:
        parts.append(f"Top {len(context['risks'])} risk(s) retrieved from the Knowledge Graph.")
    if "compliance_gaps" in context:
        parts.append(f"{len(context['compliance_gaps'])} control gap(s) identified.")

    if not parts:
        parts.append("No specialist agent produced context for this query yet (stub response).")

    state["final_reply"] = " ".join(parts)
    state.setdefault("agent_trace", []).append("chat_assistant")
    return state
