from typing import TypedDict
class AgentState(TypedDict, total=False):
    user_query: str
    user_role: str
    routes: list[str]
    completed: list[str]
    retrieved_context: dict
    agent_trace: list[str]
    final_reply: str
    history: list[dict]
    model: str | None
    citations: list[dict]
