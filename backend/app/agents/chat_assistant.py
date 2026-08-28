"""Final grounded response node with a deterministic local fallback."""
import json

from app.ai.providers import get_model_provider
from app.agents.state import AgentState


def chat_assistant_node(state: AgentState) -> AgentState:
    context = state.get("retrieved_context", {})
    parts: list[str] = []

    if "assets" in context:
        names = [
            str(item.get("a", item).get("name", item.get("a", item).get("id", "asset")))
            for item in context["assets"][:5]
        ]
        parts.append(f"Assets ({len(context['assets'])}): {', '.join(names) or 'none'}.")
    if "risks" in context:
        risk_names = [
            str(item.get("title") or item.get("risk", {}).get("title") or item.get("id") or "risk")
            for item in context["risks"][:5]
        ]
        parts.append(f"Top risks ({len(context['risks'])}): {', '.join(risk_names) or 'none'}.")
    if "attack_paths" in context:
        parts.append(f"Ranked attack paths identified: {len(context['attack_paths'])}.")
    if "compliance_gaps" in context:
        framework = context.get("compliance_framework", "the selected framework")
        parts.append(f"{framework} compliance gaps identified: {len(context['compliance_gaps'])}.")

    if not parts:
        parts.append("No matching CSOS records were found for this question.")

    fallback = " ".join(parts)
    citations: list[dict[str, str]] = []
    for category, items in context.items():
        if not isinstance(items, list):
            continue
        for item in items[:10]:
            if not hasattr(item, "get"):
                continue
            entity = item
            for key in ("asset", "risk", "a", "r", "c", "v"):
                candidate = item.get(key)
                if hasattr(candidate, "get"):
                    entity = candidate
                    break
            entity_id = entity.get("id") if hasattr(entity, "get") else None
            if entity_id:
                citations.append({
                    "entity_type": category,
                    "entity_id": str(entity_id),
                    "label": str(entity.get("name") or entity.get("title") or entity_id),
                })
    state["citations"] = citations
    history = state.get("conversation_history", [])[-10:]
    prompt = (
        "You are the CSOS security assistant. Answer only from the JSON context below. "
        "Do not invent facts. Cite asset, risk, vulnerability or control IDs when present. "
        f"Use concise language appropriate for a {state.get('user_role', 'Analyst')}.\n"
        f"Question: {state.get('user_query', '')}\n"
        f"Recent conversation: {json.dumps(history, default=str)}\n"
        f"Context: {json.dumps(context, default=str)[:24000]}"
    )
    try:
        generated = get_model_provider().generate(prompt)
        state["final_reply"] = generated.strip() or fallback
        state.setdefault("agent_trace", []).append("ollama:grounded_generation")
    except Exception as exc:  # local runtime/model may not yet be installed
        state["final_reply"] = fallback
        state.setdefault("agent_trace", []).append(
            f"local_model_fallback:{type(exc).__name__}"
        )
    state.setdefault("agent_trace", []).append("chat_assistant")
    return state
