"""
AI Chat Assistant — final LangGraph node.
Formats the natural-language reply from whatever context the
specialist agents retrieved.

TODO(M3): replace the string-templating below with a real Ollama call:

    from langchain_community.llms import Ollama
    llm = Ollama(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
    reply = llm.invoke(build_prompt(state))

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
