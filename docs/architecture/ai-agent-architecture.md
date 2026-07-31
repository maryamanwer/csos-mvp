# CSOS – Provider-Independent AI Multi-Agent Architecture

## 1. Framework

- **Orchestration:** LangGraph state graph with agent nodes and conditional routing.
- **Agent/tool framework:** LangChain-compatible tools over authorized platform APIs and graph queries.
- **Provider boundary:** Agents call the `ModelProvider` interface rather than importing a vendor/model directly.
- **Default local runtime:** Ollama.
- **Model selection:** Environment-configured allow-list and default model.
- **Compatible model families:** Llama, DeepSeek, Qwen, Mistral, ALLAM, HUMAIN-compatible open/sovereign models, and future Ollama-compatible models.

This design allows a deployment to add or switch a compatible model without
changing agent routing, prompts, tools, or the wider platform architecture.

## 2. Agent Roster

| Agent | Responsibility | Tools it can call |
|---|---|---|
| Orchestrator Agent | Classifies intent, applies role context, routes and merges results | intent classifier, agent router |
| Asset Intelligence Agent | Answers questions about assets, ownership, classification, and relationships | `get_asset`, `search_assets`, `get_asset_relationships` |
| Risk Assessment Agent | Computes/explains scores and prioritizes remediation | `get_risk_score`, `list_top_risks`, `get_vulnerabilities_for_asset` |
| Compliance Agent | Maps controls to frameworks and explains gaps | `get_framework_coverage`, `list_control_gaps`, `get_policy` |
| AI Chat Assistant | Produces the user-facing response and supporting citations | delegates through the Orchestrator |

Architecture Review, Incident Response, Threat Intelligence, and Threat
Generation agents can be added in later implementation phases through the same
state and provider interfaces.

## 3. Execution Graph

```text
User query + requesting role
   │
   ▼
Orchestrator Agent (intent classification and authorization context)
   │
   ├──► Asset Intelligence Agent ──┐
   ├──► Risk Assessment Agent ─────┼──► grounded context
   └──► Compliance Agent ──────────┘
   │
   ▼
Configured ModelProvider + selected compatible model
   │
   ▼
AI Chat Assistant (answer + citations + agent trace)
```

The shared state includes `user_query`, `user_role`, `route`,
`retrieved_context`, `agent_trace`, and `final_reply`.

## 4. Provider and Model Resolution

`backend/app/ai/providers.py` supplies the application boundary:

1. `get_model_provider()` resolves the configured provider.
2. `resolve_model()` validates a requested model against the configured allow-list.
3. `OllamaModelProvider` invokes the selected compatible local model.
4. A future runtime registers another `ModelProvider` factory without agent changes.

Model names are operational configuration, not architectural dependencies. A
specific sovereign model is enabled only when its weights/license and an
Ollama-compatible package are available to the deployment.

## 5. Prompting, Grounding, and Controls

- Retrieve authorized Neo4j/PostgreSQL facts before generation.
- Instruct models to use only supplied facts and identify supporting asset/control IDs.
- Preserve the requesting role so executive and analyst responses differ appropriately.
- Return an agent trace for explainability.
- Reject model selections that are not explicitly enabled.
- Keep external providers optional; air-gapped operation must remain functional with Ollama.

## 6. File Layout

```text
backend/app/
 ├── ai/
 │    └── providers.py       # ModelProvider interface, registry, Ollama adapter
 └── agents/
      ├── orchestrator.py    # LangGraph definition
      ├── asset_agent.py
      ├── risk_agent.py
      ├── compliance_agent.py
      ├── chat_assistant.py
      ├── tools/
      │    ├── asset_tools.py
      │    ├── risk_tools.py
      │    └── compliance_tools.py
      └── state.py
```

## 7. Environment Configuration

```dotenv
AI_PROVIDER=ollama
AI_DEFAULT_MODEL=llama3.1
AI_AVAILABLE_MODELS=llama3.1,deepseek-r1,qwen2.5,mistral,allam
OLLAMA_BASE_URL=http://ollama:11434

# Optional provider configuration for a future registered adapter
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_API_KEY=
```
