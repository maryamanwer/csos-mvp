# CSOS – AI Multi-Agent Architecture (Milestone 1)

## 1. Framework
- **Orchestration:** LangGraph (state graph of agent nodes + conditional edges)
- **Agent/tool framework:** LangChain
- **LLM runtime:** Ollama (local), models: Llama 3.x, Mistral, Qwen — OpenAI-compatible endpoint optional for teams that want a hosted model.

## 2. Agent Roster (MVP)

| Agent | Responsibility | Tools it can call |
|---|---|---|
| Orchestrator Agent | Classifies user intent, routes to the right specialist agent(s), merges results | intent classifier (LLM), agent router |
| Asset Intelligence Agent | Answers questions about assets, ownership, classification, relationships | `get_asset`, `search_assets`, `get_asset_relationships` (Neo4j) |
| Risk Assessment Agent | Computes/explains risk scores, prioritizes remediation | `get_risk_score`, `list_top_risks`, `get_vulnerabilities_for_asset` |
| Compliance Agent | Maps controls to frameworks, reports gaps | `get_framework_coverage`, `list_control_gaps`, `get_policy` |
| AI Chat Assistant | User-facing conversational layer; formats the final answer | delegates to the three agents above via Orchestrator |

Reserved for future phases (not implemented in MVP, but the graph interface accommodates them): Architecture Review Agent, Incident Response Agent, Threat Intelligence Agent, Threat Generator Agent.

## 3. Example Execution Graph

```
User query
   │
   ▼
Orchestrator Agent (intent classification)
   │
   ├──► Asset Intelligence Agent ──┐
   ├──► Risk Assessment Agent ─────┼──► merge context
   └──► Compliance Agent ──────────┘
   │
   ▼
AI Chat Assistant (final natural-language response)
```

LangGraph implementation notes:
- Each agent is a **node**; the Orchestrator's routing function is a **conditional edge**.
- Shared **state** object carries: `user_query`, `user_role` (for RBAC-aware answers), `retrieved_context`, `agent_trace`.
- `agent_trace` is returned to the UI so analysts can see which agents/tools were used (explainability).

## 4. Prompting & Grounding
- Agents are **grounded** by first calling Neo4j/PostgreSQL tools, then passing retrieved facts into the LLM prompt (retrieval-before-generation) to reduce hallucination.
- System prompts enforce: cite the asset/control IDs used, refuse to answer outside available data, respect the requesting user's role (e.g., Analyst vs Executive phrasing).

## 5. File Layout

```
backend/app/agents/
 ├── orchestrator.py        # LangGraph graph definition
 ├── asset_agent.py
 ├── risk_agent.py
 ├── compliance_agent.py
 ├── chat_assistant.py
 ├── tools/
 │    ├── asset_tools.py     # Neo4j-backed tools
 │    ├── risk_tools.py
 │    └── compliance_tools.py
 └── state.py                # Shared LangGraph state schema
```

## 6. Model Configuration (env-driven)
```
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1
# optional OpenAI-compatible fallback
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_API_KEY=
```
